"""Wallet: saldo, direccion de deposito BSC, registro de depositos y movimientos.
Recarga automatica: el usuario guarda su direccion BSC y el escaneo
en segundo plano acredita los pagos USDT entrantes a la direccion del proyecto.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import config
from app.core.database import get_db
from app.core.deps import get_admin, get_current_user
from app.models.models import Deposit, Transaction, User
from app.services import scanner, verification
from app.services.economy import MIN_DEPOSIT_USDT, add_transaction, audit, get_config
from app.services.mining import now_utc
from app.routers.withdrawals import BSC_RE

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


class DepositIn(BaseModel):
    tx_hash: str = Field(min_length=10, max_length=128)
    network: str  # BSC | TRON
    amount_usdt: Decimal = Field(gt=0)


class AddressesIn(BaseModel):
    bsc_address: str | None = None


@router.get("")
def wallet(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cfg = get_config(db)
    return {
        "usdt_balance": float(user.usdt_balance),
        "hck_balance": float(user.hck_balance),
        "deposit_addresses": {
            "bsc": config.DEPOSIT_BSC_ADDRESS,
            "tron": config.DEPOSIT_TRON_ADDRESS,
            "configured": bool(config.DEPOSIT_BSC_ADDRESS or config.DEPOSIT_TRON_ADDRESS),
        },
        "hck_to_usdt_rate": float(cfg.hck_to_usdt_rate),
    }


@router.get("/deposit-info")
def deposit_info(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Datos para la seccion 'Recargar USDT': UNA SOLA direccion de deposito
    (BSC/BEP-20), monto minimo, si la acreditacion automatica esta activa y la
    direccion BSC guardada del usuario (para que el escaneo identifique sus pagos)."""
    cfg = get_config(db)
    configured = scanner.scan_configured()
    return {
        "address": config.DEPOSIT_BSC_ADDRESS,
        "network": "BSC",
        "configured": bool(config.DEPOSIT_BSC_ADDRESS),
        "min_deposit_usdt": float(MIN_DEPOSIT_USDT),
        "auto_credit": configured,
        "hck_to_usdt_rate": float(cfg.hck_to_usdt_rate),
        "my_address": user.bsc_address,
    }


@router.put("/addresses")
def save_addresses(data: AddressesIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Guarda la direccion de billetera BSC del usuario (remitente de sus pagos).
    Solo la direccion: nunca se piden ni se guardan claves privadas."""
    if data.bsc_address is not None:
        addr = data.bsc_address.strip()
        if addr and not BSC_RE.match(addr):
            raise HTTPException(status_code=422, detail="Direccion BSC invalida (0x + 40 hex)")
        user.bsc_address = addr or None
    audit(db, "wallet_addresses_saved", user.id,
          f"direccion BSC guardada: {'si' if user.bsc_address else 'no'}")
    db.commit()
    return {"bsc_address": user.bsc_address}


@router.post("/deposits/scan")
def manual_scan(db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    """Dispara un escaneo manual de depositos entrantes (solo admin).
    Sin direcciones ni API keys configuradas, devuelve inactivo sin romper nada."""
    result = scanner.scan_all(db)
    audit(db, "deposit_scan_manual", admin.id, f"escaneo manual: {result}")
    return result


@router.post("/deposits", status_code=201)
def create_deposit(data: DepositIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.network not in ("BSC", "TRON"):
        raise HTTPException(status_code=422, detail="network debe ser BSC o TRON")
    existing = db.query(Deposit).filter(Deposit.tx_hash == data.tx_hash).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ese tx_hash ya fue registrado")
    deposit_address = config.DEPOSIT_BSC_ADDRESS if data.network == "BSC" else config.DEPOSIT_TRON_ADDRESS
    result = verification.verify_deposit(data.network, data.tx_hash, data.amount_usdt, deposit_address)
    status = {"verified": "verified", "rejected": "rejected", "pending": "pending_verification"}[result["status"]]
    dep = Deposit(user_id=user.id, tx_hash=data.tx_hash, network=data.network,
                  amount_usdt=Decimal(data.amount_usdt), status=status, reason=result.get("reason"))
    db.add(dep)
    if status == "verified":
        dep.verified_at = now_utc()
        user.usdt_balance = Decimal(user.usdt_balance) + Decimal(data.amount_usdt)
        add_transaction(db, user.id, "deposit", amount_usdt=Decimal(data.amount_usdt),
                        description=f"Deposito verificado {data.network} {data.tx_hash}")
        audit(db, "deposit_verified", user.id, f"+{data.amount_usdt} USDT ({data.network})")
    else:
        audit(db, "deposit_registered", user.id,
              f"deposito {data.network} {data.tx_hash} -> {status}: {result.get('reason')}")
    db.commit()
    db.refresh(dep)
    return {"id": dep.id, "tx_hash": dep.tx_hash, "network": dep.network,
            "amount_usdt": float(dep.amount_usdt), "status": dep.status,
            "reason": dep.reason, "created_at": dep.created_at.isoformat()}


@router.get("/deposits")
def list_deposits(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deps = db.query(Deposit).filter(Deposit.user_id == user.id).order_by(Deposit.created_at.desc()).all()
    return [{"id": d.id, "tx_hash": d.tx_hash, "network": d.network,
             "amount_usdt": float(d.amount_usdt), "status": d.status, "reason": d.reason,
             "created_at": d.created_at.isoformat()} for d in deps]


@router.get("/transactions")
def list_transactions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.created_at.desc()).limit(200).all()
    return [{"id": t.id, "type": t.type, "amount_hck": float(t.amount_hck),
             "amount_usdt": float(t.amount_usdt), "description": t.description,
             "created_at": t.created_at.isoformat()} for t in txs]
