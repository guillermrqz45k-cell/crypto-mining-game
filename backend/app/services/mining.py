"""Produccion minera: calculo en servidor por tiempo transcurrido.
HCK/hora = hashrate_total * produccion_por_hash (10 por defecto).
Capacidad (nido) = produccion/hora * horas_almacenamiento (8 por defecto).
Sin mineria activa no hay produccion. El pendiente nunca supera la capacidad.
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.models import User
from app.services.economy import get_config, user_hashrate


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def capacity_hck(db: Session, user: User) -> Decimal:
    cfg = get_config(db)
    return user_hashrate(db, user.id) * cfg.production_per_hash * cfg.storage_hours


def pending_hck(db: Session, user: User) -> Decimal:
    """HCK producido y no recolectado (acumulado de sesiones paradas + sesion activa)."""
    cfg = get_config(db)
    cap = capacity_hck(db, user)
    pending = Decimal(user.mining_pending_hck or 0)
    if user.mining_active and user.mining_started_at:
        elapsed_h = Decimal(str((now_utc() - user.mining_started_at).total_seconds())) / Decimal("3600")
        produced = user_hashrate(db, user.id) * cfg.production_per_hash * elapsed_h
        pending += produced
    return min(pending, cap)


def accrue_to_pending(db: Session, user: User) -> Decimal:
    """Mueve la produccion de la sesion activa al pendiente almacenado y para el reloj."""
    pending = pending_hck(db, user)
    user.mining_pending_hck = pending
    user.mining_started_at = None
    return pending
