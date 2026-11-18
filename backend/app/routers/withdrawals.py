"""Retiros: HCK -> USDT. Minimo 10 USDT, comision 2%. NUNCA paga on-chain
automaticamente: el retiro queda 'pending' y lo paga el admin a mano."""
import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, Withdrawal
from app.services.economy import add_transaction, audit, get_config

router = APIRouter(prefix="/api/withdrawals", tags=["withdrawals"])

BSC_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
TRON_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")


class WithdrawalIn(BaseModel):
    amount_usdt: Decimal = Field(gt=0)
    address: str
    network: str  # BSC | TRON


def _validate_address(network: str, address: str):
    if network == "BSC":
        if not BSC_RE.match(address):
            raise HTTPException(status_code=422, detail="Direccion BSC invalida (0x + 40 hex)")
    elif network == "TRON":
        if not TRON_RE.match(address):
            raise HTTPException(status_code=422, detail="Direccion TRON invalida (empieza por T, 34 caracteres)")
    else:
        raise HTTPException(status_code=422, detail="network debe ser BSC o TRON")


@router.post("", status_code=201)
def create_withdrawal(data: WithdrawalIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _validate_address(data.network, data.address)
    cfg = get_config(db)
    amount = Decimal(data.amount_usdt)
    if amount < Decimal(cfg.min_withdrawal_usdt):
        raise HTTPException(status_code=422, detail=f"Retiro minimo: {cfg.min_withdrawal_usdt} USDT")
    fee = (amount * Decimal(cfg.withdrawal_fee_percent) / Decimal("100")).quantize(Decimal("0.000001"))
    net = amount - fee
    hck_needed = (amount * Decimal(cfg.hck_to_usdt_rate)).quantize(Decimal("0.0001"))
    if Decimal(user.hck_balance) < hck_needed:
        raise HTTPException(status_code=402, detail="Saldo HCK insuficiente para el retiro")
    user.hck_balance = Decimal(user.hck_balance) - hck_needed
    wd = Withdrawal(user_id=user.id, amount_usdt=amount, fee_usdt=fee, net_usdt=net,
                    hck_spent=hck_needed, address=data.address, network=data.network)
    db.add(wd)
    add_transaction(db, user.id, "withdrawal", amount_hck=-hck_needed, amount_usdt=-amount,
                    description=f"Retiro solicitado {amount} USDT ({data.network})")
    audit(db, "withdrawal_request", user.id, f"retiro {amount} USDT -> {data.network} {data.address}")
    db.commit()
    db.refresh(wd)
    return {"id": wd.id, "amount_usdt": float(wd.amount_usdt), "fee_usdt": float(wd.fee_usdt),
            "net_usdt": float(wd.net_usdt), "hck_spent": float(wd.hck_spent),
            "address": wd.address, "network": wd.network, "status": wd.status,
            "created_at": wd.created_at.isoformat()}


@router.get("")
def list_withdrawals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    wds = db.query(Withdrawal).filter(Withdrawal.user_id == user.id).order_by(Withdrawal.created_at.desc()).all()
    return [{"id": w.id, "amount_usdt": float(w.amount_usdt), "fee_usdt": float(w.fee_usdt),
             "net_usdt": float(w.net_usdt), "hck_spent": float(w.hck_spent),
             "address": w.address, "network": w.network, "status": w.status,
             "reason": w.reason, "tx_hash": w.tx_hash,
             "created_at": w.created_at.isoformat()} for w in wds]
