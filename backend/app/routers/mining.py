"""Mineria: start / stop / collect / status. Produccion calculada en servidor."""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User
from app.services import mining as mining_svc
from app.services.economy import (
    add_transaction, audit, check_level_up, user_hashrate,
)
from app.services.missions import add_progress

router = APIRouter(prefix="/api/mining", tags=["mining"])


def _status(db: Session, user: User) -> dict:
    hashrate = user_hashrate(db, user.id)
    pending = mining_svc.pending_hck(db, user)
    capacity = mining_svc.capacity_hck(db, user)
    return {
        "mining_active": user.mining_active,
        "hashrate": float(hashrate),
        "pending_hck": float(pending),
        "capacity_hck": float(capacity),
        "started_at": user.mining_started_at.isoformat() if user.mining_started_at else None,
        "storage_full": pending >= capacity and capacity > 0,
    }


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _status(db, user)


@router.post("/start")
def start(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.mining_active:
        raise HTTPException(status_code=422, detail="La mineria ya esta activa")
    if user_hashrate(db, user.id) <= 0:
        raise HTTPException(status_code=422, detail="Necesitas al menos una maquina para minar")
    user.mining_active = True
    user.mining_started_at = mining_svc.now_utc()
    audit(db, "mining_start", user.id, "inicio de sesion de mineria")
    db.commit()
    return _status(db, user)


@router.post("/stop")
def stop(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.mining_active:
        raise HTTPException(status_code=422, detail="La mineria no esta activa")
    started = user.mining_started_at
    minutes = 0.0
    if started:
        minutes = (mining_svc.now_utc() - started).total_seconds() / 60
    mining_svc.accrue_to_pending(db, user)
    user.mining_active = False
    if minutes > 0:
        add_progress(db, user.id, "mine_1h", Decimal(str(minutes)))
    audit(db, "mining_stop", user.id, f"mineria detenida, pendiente {user.mining_pending_hck} HCK")
    db.commit()
    return _status(db, user)


@router.post("/collect")
def collect(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # El saldo NUNCA viene del cliente: se calcula en servidor por tiempo transcurrido.
    pending = mining_svc.pending_hck(db, user)
    if pending <= 0:
        return {"collected_hck": 0.0, "xp_gained": 0, "level_up": False,
                "hck_balance": float(user.hck_balance), "level": user.level}
    # Minutos minados en esta sesion activa -> mision mine_1h
    if user.mining_active and user.mining_started_at:
        minutes = (mining_svc.now_utc() - user.mining_started_at).total_seconds() / 60
        add_progress(db, user.id, "mine_1h", Decimal(str(minutes)))
        user.mining_started_at = mining_svc.now_utc()  # el reloj sigue corriendo tras recolectar
    user.mining_pending_hck = Decimal("0")
    user.hck_balance = Decimal(user.hck_balance) + pending
    user.total_hck_earned = Decimal(user.total_hck_earned) + pending
    xp_gained = int(pending // Decimal("100"))
    user.xp += xp_gained
    add_progress(db, user.id, "collect_1000", pending)
    add_transaction(db, user.id, "collect", amount_hck=pending, description="Recoleccion de HCK minado")
    level_up = check_level_up(db, user)
    audit(db, "collect", user.id, f"recolectados {pending} HCK (+{xp_gained} XP)")
    db.commit()
    return {"collected_hck": float(pending), "xp_gained": xp_gained, "level_up": level_up,
            "hck_balance": float(user.hck_balance), "level": user.level}
