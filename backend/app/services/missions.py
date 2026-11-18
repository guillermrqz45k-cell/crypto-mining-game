"""Misiones diarias. Se resetean cada dia (clave por fecha YYYY-MM-DD)."""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.models import User, UserMission

MISSIONS = [
    {"id": "mine_1h", "name": "Mina 1 hora", "description": "Ten la mineria activa 1 hora acumulada hoy", "target": Decimal("60"), "reward_hck": Decimal("300"), "unit": "minutos"},
    {"id": "collect_1000", "name": "Recolecta 1000 HCK", "description": "Recolecta 1000 HCK hoy", "target": Decimal("1000"), "reward_hck": Decimal("200"), "unit": "HCK"},
    {"id": "buy_first", "name": "Compra tu primera máquina", "description": "Compra tu primera maquina (una sola vez)", "target": Decimal("1"), "reward_hck": Decimal("500"), "unit": "maquina"},
    {"id": "invite_1", "name": "Invita 1 amigo", "description": "Que un amigo se registre con tu codigo", "target": Decimal("1"), "reward_hck": Decimal("500"), "unit": "amigo"},
    {"id": "claim_daily", "name": "Reclama el bono diario", "description": "Reclama tu bono diario", "target": Decimal("1"), "reward_hck": Decimal("100"), "unit": "bono"},
]


def today_str() -> str:
    return date.today().isoformat()


def get_or_create(db: Session, user_id: int, mission_id: str, day: str) -> UserMission:
    row = db.query(UserMission).filter_by(user_id=user_id, mission_id=mission_id, date=day).first()
    if row is None:
        row = UserMission(user_id=user_id, mission_id=mission_id, date=day, progress=Decimal("0"))
        db.add(row)
        db.flush()
    return row


def add_progress(db: Session, user_id: int, mission_id: str, amount, day: str = None) -> None:
    day = day or today_str()
    row = get_or_create(db, user_id, mission_id, day)
    row.progress = Decimal(row.progress) + Decimal(str(amount))


def missions_status(db: Session, user: User) -> list:
    day = today_str()
    referred = db.query(User).filter(User.referred_by_id == user.id).count()
    out = []
    for m in MISSIONS:
        row = get_or_create(db, user.id, m["id"], day)
        # Progreso derivado para misiones que dependen del estado actual
        progress = Decimal(row.progress)
        if m["id"] == "invite_1":
            progress = max(progress, Decimal(min(referred, 1)))
        if m["id"] == "buy_first":
            # Solo cuentan las maquinas de PAGO: el Minero Inicial (nivel 0,
            # gratis) lo tienen todos desde el registro y no completa la mision.
            from app.models.models import OwnedMachine
            from app.services.economy import STARTER_MACHINE_ID
            owned = db.query(OwnedMachine).filter(
                OwnedMachine.user_id == user.id,
                OwnedMachine.machine_id != STARTER_MACHINE_ID).count()
            progress = max(progress, Decimal(1 if owned else 0))
        completed = progress >= m["target"]
        out.append({
            "id": m["id"], "name": m["name"], "description": m["description"],
            "target": float(m["target"]), "progress": float(progress),
            "reward_hck": float(m["reward_hck"]), "completed": completed,
            "claimed": row.claimed, "unit": m["unit"],
        })
    db.commit()
    return out


def claim_mission(db: Session, user: User, mission_id: str):
    """Devuelve (ok, payload_o_error)."""
    mission = next((m for m in MISSIONS if m["id"] == mission_id), None)
    if mission is None:
        return False, (404, "Mision no encontrada")
    day = today_str()
    if mission_id == "buy_first":
        # Una sola vez en la vida: si ya se reclamo en cualquier dia, no repetir
        ever = db.query(UserMission).filter_by(user_id=user.id, mission_id="buy_first", claimed=True).first()
        if ever:
            return False, (422, "Mision ya reclamada (una sola vez)")
    row = get_or_create(db, user.id, mission_id, day)
    if row.claimed:
        return False, (422, "Mision ya reclamada hoy")
    progress = Decimal(row.progress)
    if mission_id == "invite_1":
        referred = db.query(User).filter(User.referred_by_id == user.id).count()
        progress = max(progress, Decimal(min(referred, 1)))
    if mission_id == "buy_first":
        # Solo cuentan las maquinas de PAGO (ver comentario en missions_status).
        from app.models.models import OwnedMachine
        from app.services.economy import STARTER_MACHINE_ID
        owned = db.query(OwnedMachine).filter(
            OwnedMachine.user_id == user.id,
            OwnedMachine.machine_id != STARTER_MACHINE_ID).count()
        progress = max(progress, Decimal(1 if owned else 0))
    if progress < mission["target"]:
        return False, (422, "Mision no completada todavia")
    row.claimed = True
    reward = mission["reward_hck"]
    user.hck_balance = Decimal(user.hck_balance) + reward
    user.total_hck_earned = Decimal(user.total_hck_earned) + reward
    return True, {"mission_id": mission_id, "reward_hck": float(reward),
                  "hck_balance": float(user.hck_balance)}
