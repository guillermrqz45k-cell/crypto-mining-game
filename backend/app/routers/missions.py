"""Misiones diarias y bono diario con racha de 7 dias."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User
from app.services.economy import DAILY_BONUS, add_transaction, audit, check_level_up
from app.services.missions import add_progress, claim_mission, missions_status, today_str

router = APIRouter(tags=["missions"])


class ClaimIn(BaseModel):
    mission_id: str


@router.get("/api/missions")
def list_missions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return missions_status(db, user)


@router.post("/api/missions/claim")
def claim(data: ClaimIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ok, result = claim_mission(db, user, data.mission_id)
    if not ok:
        code, msg = result
        raise HTTPException(status_code=code, detail=msg)
    check_level_up(db, user)
    add_transaction(db, user.id, "reward", amount_hck=Decimal(str(result["reward_hck"])),
                    description=f"Mision completada: {data.mission_id}")
    audit(db, "mission_claim", user.id, f"mision {data.mission_id} +{result['reward_hck']} HCK")
    db.commit()
    return result


@router.post("/api/daily-bonus/claim")
def daily_bonus(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    last = user.last_daily_bonus_date.date() if user.last_daily_bonus_date else None
    if last == today:
        raise HTTPException(status_code=422, detail="El bono diario ya fue reclamado hoy")
    if last == today - timedelta(days=1):
        streak = user.daily_bonus_streak + 1
    else:
        streak = 1
    if streak > 7:
        streak = 1
    reward = DAILY_BONUS[streak - 1]
    user.daily_bonus_streak = streak
    user.last_daily_bonus_date = datetime.now()
    user.hck_balance = Decimal(user.hck_balance) + reward
    user.total_hck_earned = Decimal(user.total_hck_earned) + reward
    add_progress(db, user.id, "claim_daily", Decimal("1"))
    add_transaction(db, user.id, "bonus", amount_hck=reward,
                    description=f"Bono diario dia {streak} de racha")
    check_level_up(db, user)
    audit(db, "daily_bonus", user.id, f"bono diario dia {streak}: +{reward} HCK")
    db.commit()
    return {"streak": streak, "reward_hck": float(reward),
            "hck_balance": float(user.hck_balance)}
