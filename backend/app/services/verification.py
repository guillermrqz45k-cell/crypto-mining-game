"""Verificacion on-chain de depositos USDT (BSC BEP-20 / TRON TRC-20).

SIN claves de API (BSCSCAN_API_KEY / TRONGRID_API_KEY) el deposito queda en
'pending_verification' y NUNCA se acredita. Con claves, se verifica on-chain:
- BSC: Etherscan API V2 (chainid 56), token transfers del contrato USDT; debe
  existir el tx_hash, to == DEPOSIT_BSC_ADDRESS y value == amount (18 decimales).
  BscScan ya no genera API keys propias: la clave es la de Etherscan V2
  (misma clave para BSC y 60+ cadenas) y se configura en BSCSCAN_API_KEY.
- TRON: TronGrid TRC-20 transfers; to == DEPOSIT_TRON_ADDRESS, value == amount
  (6 decimales), contrato USDT TRC-20.

Las funciones *_raw son el punto de mock en tests (monkeypatch).
"""
from decimal import Decimal

import httpx

from app.core import config

# Etherscan API V2 (una clave para 60+ cadenas; BSC = chainid 56).
ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"
BSC_CHAIN_ID = "56"
TRONGRID_URL = "https://api.trongrid.io"


def _bsc_token_txs(deposit_address: str):
    params = {
        "chainid": BSC_CHAIN_ID,
        "module": "account", "action": "tokentx",
        "contractaddress": config.USDT_BSC_CONTRACT,
        "address": deposit_address, "page": 1, "offset": 100,
        "sort": "desc", "apikey": config.BSCSCAN_API_KEY,
    }
    r = httpx.get(ETHERSCAN_V2_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("result", [])


def _tron_trc20_txs(deposit_address: str):
    headers = {"TRON-PRO-API-KEY": config.TRONGRID_API_KEY} if config.TRONGRID_API_KEY else {}
    url = f"{TRONGRID_URL}/v1/accounts/{deposit_address}/transactions/trc20"
    r = httpx.get(url, params={"limit": 100, "only_to": "true"}, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def verify_bsc_deposit(tx_hash: str, amount_usdt: Decimal, deposit_address: str) -> dict:
    """Devuelve {'status': 'verified'|'rejected'|'pending', 'reason': str|None}."""
    if not config.BSCSCAN_API_KEY:
        return {"status": "pending", "reason": "sin BSCSCAN_API_KEY"}
    if not deposit_address:
        return {"status": "rejected", "reason": "sin direccion de deposito BSC configurada"}
    try:
        txs = _bsc_token_txs(deposit_address)
    except Exception as e:  # noqa: BLE001 - error de red/API -> pendiente, no acreditar
        return {"status": "pending", "reason": f"error BscScan: {e}"}
    for tx in txs:
        if str(tx.get("hash", "")).lower() == tx_hash.lower():
            to = str(tx.get("to", "")).lower()
            value = Decimal(str(tx.get("value", "0"))) / Decimal(10) ** 18
            if to != deposit_address.lower():
                return {"status": "rejected", "reason": "destinatario distinto a la direccion de deposito"}
            if value != Decimal(amount_usdt):
                return {"status": "rejected", "reason": f"monto on-chain {value} != declarado {amount_usdt}"}
            return {"status": "verified", "reason": None}
    return {"status": "rejected", "reason": "tx_hash no encontrado en transferencias USDT a la direccion"}


def verify_tron_deposit(tx_hash: str, amount_usdt: Decimal, deposit_address: str) -> dict:
    if not config.TRONGRID_API_KEY:
        return {"status": "pending", "reason": "sin TRONGRID_API_KEY"}
    if not deposit_address:
        return {"status": "rejected", "reason": "sin direccion de deposito TRON configurada"}
    try:
        txs = _tron_trc20_txs(deposit_address)
    except Exception as e:  # noqa: BLE001
        return {"status": "pending", "reason": f"error TronGrid: {e}"}
    for tx in txs:
        if str(tx.get("transaction_id", "")).lower() == tx_hash.lower():
            to = str(tx.get("to", ""))
            value = Decimal(str(tx.get("value", "0"))) / Decimal(10) ** 6
            contract = str(tx.get("token_info", {}).get("address", ""))
            if contract and contract != config.USDT_TRON_CONTRACT:
                return {"status": "rejected", "reason": "contrato distinto a USDT TRC-20"}
            if to != deposit_address:
                return {"status": "rejected", "reason": "destinatario distinto a la direccion de deposito"}
            if value != Decimal(amount_usdt):
                return {"status": "rejected", "reason": f"monto on-chain {value} != declarado {amount_usdt}"}
            return {"status": "verified", "reason": None}
    return {"status": "rejected", "reason": "tx_hash no encontrado en transferencias USDT a la direccion"}


def verify_deposit(network: str, tx_hash: str, amount_usdt: Decimal, deposit_address: str) -> dict:
    if network == "BSC":
        return verify_bsc_deposit(tx_hash, amount_usdt, deposit_address)
    return verify_tron_deposit(tx_hash, amount_usdt, deposit_address)
