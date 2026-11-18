"""Referidos, leaderboard y estadisticas globales."""
from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Deposit, Transaction, User
from app.services.economy import get_pool, user_hashrate

router = APIRouter(tags=["public"])


@router.get("/api/me")
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.economy import user_public
    return user_public(user, db)


@router.get("/api/referrals")
def referrals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    referred = db.query(User).filter(User.referred_by_id == user.id).order_by(User.created_at).all()
    earned = db.query(func.coalesce(func.sum(Transaction.amount_hck), 0)).filter(
        Transaction.user_id == user.id, Transaction.type == "referral").scalar()
    return {
        "referral_code": user.referral_code,
        "referral_link": f"/register?ref={user.referral_code}",
        "referred_count": len(referred),
        "earned_hck": float(earned),
        "referred_users": [{"username": u.username,
                            "created_at": u.created_at.isoformat() if u.created_at else None}
                           for u in referred],
    }


@router.get("/api/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_banned == False).all()  # noqa: E712
    by_hck = sorted(users, key=lambda u: float(u.total_hck_earned), reverse=True)[:20]
    by_hash = sorted(users, key=lambda u: float(user_hashrate(db, u.id)), reverse=True)[:20]
    return {
        "by_hck": [{"username": u.username, "total_hck_earned": float(u.total_hck_earned),
                    "level": u.level} for u in by_hck],
        "by_hashrate": [{"username": u.username, "hashrate": float(user_hashrate(db, u.id)),
                         "level": u.level} for u in by_hash],
    }


@router.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    from datetime import date, timedelta
    users = db.query(User).all()
    total_hashrate = sum(float(user_hashrate(db, u.id)) for u in users)
    total_hck = db.query(func.coalesce(func.sum(User.total_hck_earned), 0)).scalar()
    total_usdt = db.query(func.coalesce(func.sum(Deposit.amount_usdt), 0)).filter(
        Deposit.status == "verified").scalar()
    pool = get_pool(db)
    # Historial de produccion: HCK recolectados por dia, ultimos 14 dias
    history = []
    for i in range(13, -1, -1):
        day = date.today() - timedelta(days=i)
        day_total = db.query(func.coalesce(func.sum(Transaction.amount_hck), 0)).filter(
            Transaction.type == "collect",
            func.date(Transaction.created_at) == day.isoformat()).scalar()
        history.append({"date": day.isoformat(), "hck": float(day_total)})
    return {
        "total_users": len(users),
        "total_hashrate": total_hashrate,
        "total_hck_mined": float(total_hck),
        "total_usdt_deposited": float(total_usdt),
        "reward_pool_balance": float(pool.balance_usdt),
        "production_history": history,
    }
