"""Maquinas: catalogo, mis maquinas, compra (USDT) y overclock."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import OwnedMachine, User
from app.services.economy import (
    MACHINES, MAX_OVERCLOCK, STARTER_MACHINE_ID, add_transaction, audit,
    check_level_up, get_config, grant_starter_machine, machine_hashrate,
    upgrade_cost, user_hashrate,
)
from app.services.missions import add_progress

router = APIRouter(prefix="/api/machines", tags=["machines"])


class BuyIn(BaseModel):
    machine_id: str


class UpgradeIn(BaseModel):
    owned_machine_id: int


@router.get("")
def catalog():
    return [{"id": m["id"], "name": m["name"], "price_usdt": float(m["price_usdt"]),
             "hashrate": float(m["hashrate"]),
             "level": int(m["id"].split("_")[1]),
             "is_starter": m["id"] == STARTER_MACHINE_ID} for m in MACHINES.values()]


@router.get("/mine")
def mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = []
    for om in db.query(OwnedMachine).filter(OwnedMachine.user_id == user.id).all():
        base = MACHINES[om.machine_id]
        out.append({
            "id": om.id, "machine_id": om.machine_id, "name": base["name"],
            "base_hashrate": float(base["hashrate"]),
            "hashrate": float(machine_hashrate(om.machine_id, om.overclock_level)),
            "overclock_level": om.overclock_level,
            "purchased_at": om.purchased_at.isoformat() if om.purchased_at else None,
        })
    return out


@router.post("/buy")
def buy(data: BuyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    machine = MACHINES.get(data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Maquina no encontrada")
    # Nivel 0: gratis, no se compra. Se otorga al registrarse; si un usuario
    # antiguo no lo tiene, puede reclamarlo aqui sin pagar.
    if data.machine_id == STARTER_MACHINE_ID:
        granted = grant_starter_machine(db, user)
        if granted is None:
            raise HTTPException(status_code=422, detail="El Minero Inicial ya esta activo")
        audit(db, "starter_claim", user.id, "minero inicial (nivel 0) activado gratis")
        db.commit()
        return {"owned_machine_id": granted.id, "machine_id": STARTER_MACHINE_ID,
                "hashrate": float(user_hashrate(db, user.id)),
                "usdt_balance": float(user.usdt_balance)}
    price = machine["price_usdt"]
    if Decimal(user.usdt_balance) < price:
        raise HTTPException(status_code=402, detail="Saldo USDT insuficiente")
    # Primera compra de pago: solo cuentan las maquinas de pago, no el
    # Minero Inicial gratuito (todos lo tienen desde el registro).
    first_purchase = db.query(OwnedMachine).filter(
        OwnedMachine.user_id == user.id,
        OwnedMachine.machine_id != STARTER_MACHINE_ID).count() == 0
    user.usdt_balance = Decimal(user.usdt_balance) - price
    om = OwnedMachine(user_id=user.id, machine_id=data.machine_id)
    db.add(om)
    add_transaction(db, user.id, "purchase", amount_usdt=-price,
                    description=f"Compra de {machine['name']}")
    audit(db, "machine_buy", user.id, f"compro {data.machine_id} por {price} USDT")
    if first_purchase:
        add_progress(db, user.id, "buy_first", Decimal("1"))
        # Bono de referido SOLO si el comprador llego por un referido:
        # referido y referente ganan 500 HCK (configurable) en la primera compra.
        if user.referred_by_id:
            cfg = get_config(db)
            bonus = Decimal(cfg.referral_bonus_hck)
            user.hck_balance = Decimal(user.hck_balance) + bonus
            user.total_hck_earned = Decimal(user.total_hck_earned) + bonus
            add_transaction(db, user.id, "referral", amount_hck=bonus,
                            description="Bono de referido (primera compra)")
            check_level_up(db, user)
            referrer = db.query(User).filter(User.id == user.referred_by_id).first()
            if referrer:
                referrer.hck_balance = Decimal(referrer.hck_balance) + bonus
                referrer.total_hck_earned = Decimal(referrer.total_hck_earned) + bonus
                add_transaction(db, referrer.id, "referral", amount_hck=bonus,
                                description=f"Bono de referido por {user.username}")
                check_level_up(db, referrer)
    db.commit()
    return {"owned_machine_id": om.id, "machine_id": om.machine_id,
            "hashrate": float(user_hashrate(db, user.id)),
            "usdt_balance": float(user.usdt_balance)}


@router.post("/upgrade")
def upgrade(data: UpgradeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    om = db.query(OwnedMachine).filter(OwnedMachine.id == data.owned_machine_id,
                                        OwnedMachine.user_id == user.id).first()
    if not om:
        raise HTTPException(status_code=404, detail="Maquina no encontrada")
    if om.machine_id == STARTER_MACHINE_ID:
        raise HTTPException(status_code=422, detail="El Minero Inicial no admite overclock")
    if om.overclock_level >= MAX_OVERCLOCK:
        raise HTTPException(status_code=422, detail="Overclock maximo alcanzado (nivel 5)")
    next_level = om.overclock_level + 1
    cost = upgrade_cost(om.machine_id, next_level)
    if Decimal(user.usdt_balance) < cost:
        raise HTTPException(status_code=402, detail="Saldo USDT insuficiente para el overclock")
    user.usdt_balance = Decimal(user.usdt_balance) - cost
    om.overclock_level = next_level
    add_transaction(db, user.id, "purchase", amount_usdt=-cost,
                    description=f"Overclock nivel {next_level} de {MACHINES[om.machine_id]['name']}")
    audit(db, "machine_upgrade", user.id, f"overclock {om.machine_id} -> nivel {next_level}")
    db.commit()
    return {"owned_machine_id": om.id, "overclock_level": om.overclock_level,
            "hashrate": float(machine_hashrate(om.machine_id, om.overclock_level)),
            "usdt_balance": float(user.usdt_balance)}
