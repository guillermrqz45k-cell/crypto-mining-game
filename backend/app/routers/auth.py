"""Auth: registro y login. Username unico, password >= 6, JWT 7 dias."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.services.economy import audit, generate_referral_code, grant_starter_machine, user_public

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6)
    referral_code: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


def _token_response(db: Session, user: User):
    return {"access_token": create_access_token(str(user.id)), "user": user_public(user, db)}


@router.post("/register", status_code=201)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    referrer = None
    if data.referral_code:
        referrer = db.query(User).filter(User.referral_code == data.referral_code).first()
        if not referrer:
            raise HTTPException(status_code=400, detail="Codigo de referido invalido")
    code = generate_referral_code()
    while db.query(User).filter(User.referral_code == code).first():
        code = generate_referral_code()
    ip = request.client.host if request.client else None
    user = User(username=data.username, password_hash=hash_password(data.password),
                referral_code=code, referred_by_id=referrer.id if referrer else None,
                registration_ip=ip)
    db.add(user)
    db.commit()
    db.refresh(user)
    # Todo usuario nuevo empieza con el Minero Inicial (nivel 0, gratis, 2 H/s).
    grant_starter_machine(db, user)
    audit(db, "register", user.id, f"registro de {user.username}", ip)
    db.commit()
    return _token_response(db, user)


@router.post("/login")
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Usuario baneado")
    ip = request.client.host if request.client else None
    user.last_login_ip = ip
    audit(db, "login", user.id, f"login de {user.username}", ip)
    db.commit()
    return _token_response(db, user)
