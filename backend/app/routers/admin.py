"""Admin: requiere is_admin=true. Gestion de usuarios, depositos, retiros,
reward pool, configuracion, auditoria y alertas de fraude."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_admin
from app.models.models import AuditLog, Deposit, User, Withdrawal
from app.services.economy import (
    add_transaction, audit, get_config, get_pool, user_hashrate, user_public,
)
from app.services.mining import now_utc

router = APIRouter(prefix="/api/admin", tags=["admin"])


class RejectIn(BaseModel):
    reason: str = ""


class MarkPaidIn(BaseModel):
    tx_hash: str


class FundIn(BaseModel):
    amount_usdt: Decimal = Field(gt=0)


class ConfigIn(BaseModel):
    hck_to_usdt_rate: Decimal | None = None
    withdrawal_fee_percent: Decimal | None = None
    min_withdrawal_usdt: Decimal | None = None
    referral_bonus_hck: Decimal | None = None
    production_per_hash: Decimal | None = None
    storage_hours: Decimal | None = None


def _wd_out(w: Withdrawal, db: Session):
    u = db.query(User).filter(User.id == w.user_id).first()
    return {"id": w.id, "username": u.username if u else None, "amount_usdt": float(w.amount_usdt),
            "fee_usdt": float(w.fee_usdt), "net_usdt": float(w.net_usdt),
            "hck_spent": float(w.hck_spent), "address": w.address, "network": w.network,
            "status": w.status, "reason": w.reason, "tx_hash": w.tx_hash,
            "created_at": w.created_at.isoformat()}


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    users = db.query(User).count()
    pending_wd = db.query(Withdrawal).filter(Withdrawal.status == "pending").count()
    pending_dep = db.query(Deposit).filter(Deposit.status == "pending_verification").count()
    pool = get_pool(db)
    return {"total_users": users, "pending_withdrawals": pending_wd,
            "pending_deposits": pending_dep, "reward_pool_balance": float(pool.balance_usdt),
            "total_funded": float(pool.total_funded), "total_paid": float(pool.total_paid)}


@router.get("/users")
def list_users(search: str = Query(""), db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    q = db.query(User)
    if search:
        q = q.filter(User.username.ilike(f"%{search}%"))
    return [user_public(u, db) for u in q.order_by(User.created_at.desc()).limit(200).all()]


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user_public(u, db)


@router.post("/users/{user_id}/ban")
def ban(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.is_banned = True
    audit(db, "user_ban", admin.id, f"baneado usuario {u.username} (id {u.id})")
    db.commit()
    return {"id": u.id, "is_banned": True}


@router.post("/users/{user_id}/unban")
def unban(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.is_banned = False
    audit(db, "user_unban", admin.id, f"desbaneado usuario {u.username} (id {u.id})")
    db.commit()
    return {"id": u.id, "is_banned": False}


@router.get("/deposits")
def all_deposits(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    deps = db.query(Deposit).order_by(Deposit.created_at.desc()).limit(200).all()
    return [{"id": d.id, "user_id": d.user_id, "tx_hash": d.tx_hash, "network": d.network,
             "amount_usdt": float(d.amount_usdt), "status": d.status, "reason": d.reason,
             "created_at": d.created_at.isoformat()} for d in deps]


@router.get("/withdrawals")
def all_withdrawals(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    return [_wd_out(w, db) for w in db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).limit(200).all()]


@router.post("/withdrawals/{wd_id}/approve")
def approve(wd_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    w = db.query(Withdrawal).filter(Withdrawal.id == wd_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Retiro no encontrado")
    if w.status not in ("pending", "waiting_funds"):
        raise HTTPException(status_code=422, detail=f"Retiro en estado {w.status}, no se puede aprobar")
    pool = get_pool(db)
    if Decimal(pool.balance_usdt) < Decimal(w.amount_usdt):
        w.status = "waiting_funds"
        audit(db, "withdrawal_waiting_funds", admin.id,
              f"retiro {w.id} sin fondos en pool (necesita {w.amount_usdt}, pool {pool.balance_usdt})")
        db.commit()
        return {"id": w.id, "status": "waiting_funds",
                "detail": "Sin saldo suficiente en el reward pool; no se inventa dinero"}
    pool.balance_usdt = Decimal(pool.balance_usdt) - Decimal(w.amount_usdt)
    w.status = "approved"
    audit(db, "withdrawal_approve", admin.id, f"retiro {w.id} aprobado por {w.amount_usdt} USDT (reservado del pool)")
    db.commit()
    return {"id": w.id, "status": "approved"}


@router.post("/withdrawals/{wd_id}/reject")
def reject(wd_id: int, data: RejectIn, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    w = db.query(Withdrawal).filter(Withdrawal.id == wd_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Retiro no encontrado")
    if w.status not in ("pending", "waiting_funds"):
        raise HTTPException(status_code=422, detail=f"Retiro en estado {w.status}")
    w.status = "rejected"
    w.reason = data.reason
    user = db.query(User).filter(User.id == w.user_id).first()
    if user:
        user.hck_balance = Decimal(user.hck_balance) + Decimal(w.hck_spent)
        add_transaction(db, user.id, "withdrawal", amount_hck=Decimal(w.hck_spent),
                        description=f"Reembolso de retiro rechazado #{w.id}")
    audit(db, "withdrawal_reject", admin.id, f"retiro {w.id} rechazado: {data.reason}")
    db.commit()
    return {"id": w.id, "status": "rejected"}


@router.post("/withdrawals/{wd_id}/mark-paid")
def mark_paid(wd_id: int, data: MarkPaidIn, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    w = db.query(Withdrawal).filter(Withdrawal.id == wd_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Retiro no encontrado")
    if w.status != "approved":
        raise HTTPException(status_code=422, detail="Solo un retiro aprobado puede marcarse pagado")
    w.status = "paid"
    w.tx_hash = data.tx_hash
    pool = get_pool(db)
    pool.total_paid = Decimal(pool.total_paid) + Decimal(w.amount_usdt)
    audit(db, "withdrawal_paid", admin.id, f"retiro {w.id} pagado on-chain, tx {data.tx_hash}")
    db.commit()
    return {"id": w.id, "status": "paid", "tx_hash": w.tx_hash}


@router.get("/reward-pool")
def pool_info(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    pool = get_pool(db)
    return {"balance_usdt": float(pool.balance_usdt), "total_funded": float(pool.total_funded),
            "total_paid": float(pool.total_paid)}


@router.post("/reward-pool/fund")
def fund_pool(data: FundIn, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    pool = get_pool(db)
    pool.balance_usdt = Decimal(pool.balance_usdt) + Decimal(data.amount_usdt)
    pool.total_funded = Decimal(pool.total_funded) + Decimal(data.amount_usdt)
    audit(db, "pool_fund", admin.id, f"fondeo del pool +{data.amount_usdt} USDT (transferencia real por fuera)")
    db.commit()
    return {"balance_usdt": float(pool.balance_usdt), "total_funded": float(pool.total_funded)}


@router.get("/config")
def get_cfg(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    cfg = get_config(db)
    return {"hck_to_usdt_rate": float(cfg.hck_to_usdt_rate),
            "withdrawal_fee_percent": float(cfg.withdrawal_fee_percent),
            "min_withdrawal_usdt": float(cfg.min_withdrawal_usdt),
            "referral_bonus_hck": float(cfg.referral_bonus_hck),
            "production_per_hash": float(cfg.production_per_hash),
            "storage_hours": float(cfg.storage_hours)}


@router.put("/config")
def put_cfg(data: ConfigIn, db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    cfg = get_config(db)
    for field in ("hck_to_usdt_rate", "withdrawal_fee_percent", "min_withdrawal_usdt",
                  "referral_bonus_hck", "production_per_hash", "storage_hours"):
        val = getattr(data, field)
        if val is not None:
            setattr(cfg, field, Decimal(val))
    audit(db, "config_update", admin.id, f"config actualizada: {data.model_dump(exclude_none=True)}")
    db.commit()
    return {"hck_to_usdt_rate": float(cfg.hck_to_usdt_rate),
            "withdrawal_fee_percent": float(cfg.withdrawal_fee_percent),
            "min_withdrawal_usdt": float(cfg.min_withdrawal_usdt),
            "referral_bonus_hck": float(cfg.referral_bonus_hck),
            "production_per_hash": float(cfg.production_per_hash),
            "storage_hours": float(cfg.storage_hours)}


@router.get("/audit")
def audit_list(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [{"id": l.id, "user_id": l.user_id, "action": l.action, "details": l.details,
             "ip": l.ip, "created_at": l.created_at.isoformat()} for l in logs]


@router.get("/fraud-alerts")
def fraud_alerts(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    alerts = []
    # >3 cuentas con el mismo IP de registro
    rows = db.query(User.registration_ip, func.count(User.id)).filter(
        User.registration_ip.isnot(None)).group_by(User.registration_ip).having(func.count(User.id) > 3).all()
    for ip, count in rows:
        alerts.append({"type": "same_ip_registrations", "ip": ip, "count": count,
                       "detail": f"{count} cuentas registradas desde la misma IP"})
    # Retiros > 500 USDT
    big = db.query(Withdrawal).filter(Withdrawal.amount_usdt > 500).all()
    for w in big:
        alerts.append({"type": "large_withdrawal", "withdrawal_id": w.id, "user_id": w.user_id,
                       "amount_usdt": float(w.amount_usdt), "detail": f"Retiro de {w.amount_usdt} USDT"})
    # Recolecciones con velocidad anormal: pendiente mayor que el maximo posible
    for u in db.query(User).all():
        from app.services.mining import capacity_hck, pending_hck
        cap = capacity_hck(db, u)
        if cap > 0 and Decimal(u.mining_pending_hck or 0) > cap:
            alerts.append({"type": "abnormal_collection", "user_id": u.id, "username": u.username,
                           "pending_hck": float(u.mining_pending_hck), "capacity_hck": float(cap),
                           "detail": "Pendiente mayor que la capacidad maxima posible"})
    # Muchos referidos en poco tiempo (>5 en 24 h)
    since = now_utc().replace(tzinfo=None)
    from datetime import timedelta
    since = since - timedelta(hours=24)
    rows = db.query(User.referred_by_id, func.count(User.id)).filter(
        User.referred_by_id.isnot(None), User.created_at >= since).group_by(
        User.referred_by_id).having(func.count(User.id) > 5).all()
    for ref_id, count in rows:
        alerts.append({"type": "many_referrals", "user_id": ref_id, "count": count,
                       "detail": f"{count} referidos en 24 h"})
    return alerts
