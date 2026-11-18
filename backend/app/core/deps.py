"""Dependencias: sesion DB, usuario actual (JWT Bearer), admin."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario baneado")
    return user


def get_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere admin")
    return user


def client_ip(request) -> str:
    return request.client.host if request.client else "unknown"
