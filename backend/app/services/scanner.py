"""Escaneo automatico de depositos USDT entrantes (BSC BEP-20).

UNA SOLA direccion de deposito (AMO, 2026-11-17): 0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d
(BSC). No hay direccion TRON: el escaner vigila SOLO BSC.

Como funciona: el usuario guarda su direccion de billetera BSC (bsc_address)
en su perfil y envia USDT a la direccion de deposito del proyecto. El escaner
consulta BscScan (transferencias USDT BEP-20 entrantes) a DEPOSIT_BSC_ADDRESS;
por cada transferencia busca al usuario cuya direccion guardada coincida con
el remitente y acredita el deposito de forma idempotente por tx_hash
(un tx_hash repetido nunca se acredita dos veces).

El escaner solo esta activo cuando DEPOSIT_BSC_ADDRESS y BSCSCAN_API_KEY
estan configuradas. Sin la API key, el escaner queda inactivo y no rompe
nada: los depositos se acreditan por aprobacion manual del admin (ver
POST /api/admin/deposits/{id}/approve). NUNCA se guardan claves privadas.
La funcion _bsc_token_txs de verification es el punto de mock en tests.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import config
from app.models.models import Deposit, User
from app.services import verification
from app.services.economy import MIN_DEPOSIT_USDT, add_transaction, audit
from app.services.mining import now_utc

log = logging.getLogger("crypto-mining-game.scanner")


def scan_configured() -> dict:
    """Si el escaneo automatico BSC esta activo (direccion + API key)."""
    bsc = bool(config.DEPOSIT_BSC_ADDRESS and config.BSCSCAN_API_KEY)
    return {"bsc": bsc, "active": bsc}


def _credit_transfer(db: Session, tx_hash: str, sender: str, amount_usdt: Decimal) -> dict:
    """Acredita una transferencia entrante al usuario remitente.
    Devuelve {'result': 'credited'|'duplicate'|'unknown_sender'|'below_min',
    'user_id': int|None}."""
    if amount_usdt < MIN_DEPOSIT_USDT:
        return {"result": "below_min", "user_id": None}
    existing = db.query(Deposit).filter(Deposit.tx_hash == tx_hash).first()
    if existing:
        return {"result": "duplicate", "user_id": existing.user_id}
    sender_norm = sender.lower()
    user = None
    for u in db.query(User).filter(User.bsc_address.isnot(None)).all():
        if (u.bsc_address or "").lower() == sender_norm:
            user = u
            break
    if not user:
        return {"result": "unknown_sender", "user_id": None}
    dep = Deposit(user_id=user.id, tx_hash=tx_hash, network="BSC",
                  amount_usdt=amount_usdt, status="verified",
                  reason="acreditado automaticamente por escaneo (remitente verificado)")
    dep.verified_at = now_utc()
    db.add(dep)
    user.usdt_balance = Decimal(user.usdt_balance) + amount_usdt
    add_transaction(db, user.id, "deposit", amount_usdt=amount_usdt,
                    description=f"Deposito automatico BSC {tx_hash}")
    audit(db, "deposit_auto_credited", user.id,
          f"+{amount_usdt} USDT (BSC) tx {tx_hash} de {sender}")
    db.commit()
    log.info("Deposito automatico acreditado: usuario %s +%s USDT (BSC) tx %s",
             user.id, amount_usdt, tx_hash)
    return {"result": "credited", "user_id": user.id}


def scan_bsc(db: Session) -> dict:
    """Escanea transferencias USDT BEP-20 entrantes a DEPOSIT_BSC_ADDRESS."""
    summary = {"network": "BSC", "checked": 0, "credited": 0, "duplicate": 0,
               "unknown_sender": 0, "below_min": 0, "error": None}
    if not config.DEPOSIT_BSC_ADDRESS or not config.BSCSCAN_API_KEY:
        summary["error"] = "escaneo BSC inactivo: falta DEPOSIT_BSC_ADDRESS o BSCSCAN_API_KEY"
        return summary
    try:
        txs = verification._bsc_token_txs(config.DEPOSIT_BSC_ADDRESS)
    except Exception as e:  # noqa: BLE001 - error de red/API -> se registra, no se rompe
        summary["error"] = f"error BscScan: {e}"
        return summary
    deposit_address = config.DEPOSIT_BSC_ADDRESS.lower()
    for tx in txs:
        to = str(tx.get("to", "")).lower()
        if to != deposit_address:
            continue
        summary["checked"] += 1
        tx_hash = str(tx.get("hash", ""))
        sender = str(tx.get("from", ""))
        try:
            amount = Decimal(str(tx.get("value", "0"))) / Decimal(10) ** 18
        except Exception:  # noqa: BLE001 - valor no numerico -> se ignora
            continue
        result = _credit_transfer(db, tx_hash, sender, amount)
        summary[result["result"]] = summary.get(result["result"], 0) + 1
    return summary


def scan_all(db: Session) -> dict:
    """Un escaneo completo (solo BSC). Nunca lanza excepciones."""
    configured = scan_configured()
    out = {"active": configured["active"], "bsc": None}
    if configured["bsc"]:
        out["bsc"] = scan_bsc(db)
    return out
