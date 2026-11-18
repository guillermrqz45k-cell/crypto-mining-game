"""Escaneo automatico de depositos: acredita por remitente (mockeado, sin keys
reales), idempotencia por tx_hash, inactivo sin configurar, endpoints."""
from decimal import Decimal

import pytest

from tests.conftest import auth_headers, make_admin, make_user
from app.core import config
from app.models.models import Deposit, User
from app.services import scanner

DEPOSIT_BSC = "0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d"
SENDER_BSC = "0x1111111111111111111111111111111111111111"


def _bsc_txs(amount_usdt=25, sender=SENDER_BSC, tx_hash="0xscan0000000000000000000000000000000000000000000000000000000001"):
    return [{"hash": tx_hash, "from": sender, "to": DEPOSIT_BSC,
             "value": str(int(Decimal(str(amount_usdt)) * Decimal(10) ** 18))}]


def _set_bsc_address(client, db, username, address):
    u = db.query(User).filter(User.username == username).first()
    u.bsc_address = address
    db.commit()


def test_scan_inactive_without_config(client, db):
    # Sin direccion ni key: inactivo, sin romper nada
    assert scanner.scan_configured() == {"bsc": False, "active": False}
    result = scanner.scan_all(db)
    assert result["active"] is False
    assert result["bsc"] is None


def test_scan_bsc_credits_by_sender(client, db, monkeypatch):
    _, token = make_user(client, db, "scan1")
    _set_bsc_address(client, db, "scan1", SENDER_BSC)
    monkeypatch.setattr(config, "DEPOSIT_BSC_ADDRESS", DEPOSIT_BSC)
    monkeypatch.setattr(config, "BSCSCAN_API_KEY", "fake-key")
    monkeypatch.setattr("app.services.verification._bsc_token_txs",
                        lambda addr: _bsc_txs())
    result = scanner.scan_all(db)
    assert result["bsc"]["credited"] == 1
    assert result["bsc"]["checked"] == 1
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 25
    dep = db.query(Deposit).filter(Deposit.tx_hash == _bsc_txs()[0]["hash"]).first()
    assert dep is not None and dep.status == "verified"


def test_scan_bsc_idempotent_no_double_credit(client, db, monkeypatch):
    _, token = make_user(client, db, "scan2")
    _set_bsc_address(client, db, "scan2", SENDER_BSC)
    monkeypatch.setattr(config, "DEPOSIT_BSC_ADDRESS", DEPOSIT_BSC)
    monkeypatch.setattr(config, "BSCSCAN_API_KEY", "fake-key")
    monkeypatch.setattr("app.services.verification._bsc_token_txs",
                        lambda addr: _bsc_txs())
    scanner.scan_all(db)
    result = scanner.scan_all(db)
    assert result["bsc"]["credited"] == 0
    assert result["bsc"]["duplicate"] == 1
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 25  # una sola vez
    assert db.query(Deposit).count() == 1


def test_scan_bsc_unknown_sender_not_credited(client, db, monkeypatch):
    _, token = make_user(client, db, "scan3")
    # El usuario NO guardo su direccion: el remitente no coincide con nadie
    monkeypatch.setattr(config, "DEPOSIT_BSC_ADDRESS", DEPOSIT_BSC)
    monkeypatch.setattr(config, "BSCSCAN_API_KEY", "fake-key")
    monkeypatch.setattr("app.services.verification._bsc_token_txs",
                        lambda addr: _bsc_txs())
    result = scanner.scan_all(db)
    assert result["bsc"]["unknown_sender"] == 1
    assert result["bsc"]["credited"] == 0
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 0
    assert db.query(Deposit).count() == 0


def test_scan_bsc_below_min_not_credited(client, db, monkeypatch):
    _, token = make_user(client, db, "scan4")
    _set_bsc_address(client, db, "scan4", SENDER_BSC)
    monkeypatch.setattr(config, "DEPOSIT_BSC_ADDRESS", DEPOSIT_BSC)
    monkeypatch.setattr(config, "BSCSCAN_API_KEY", "fake-key")
    monkeypatch.setattr("app.services.verification._bsc_token_txs",
                        lambda addr: _bsc_txs(amount_usdt=Decimal("0.5")))
    result = scanner.scan_all(db)
    assert result["bsc"]["below_min"] == 1
    assert client.get("/api/me", headers=auth_headers(token)).json()["usdt_balance"] == 0


def test_scan_api_error_does_not_crash(client, db, monkeypatch):
    monkeypatch.setattr(config, "DEPOSIT_BSC_ADDRESS", DEPOSIT_BSC)
    monkeypatch.setattr(config, "BSCSCAN_API_KEY", "fake-key")

    def boom(addr):
        raise RuntimeError("BscScan caido")

    monkeypatch.setattr("app.services.verification._bsc_token_txs", boom)
    result = scanner.scan_all(db)
    assert result["bsc"]["error"] is not None
    assert result["bsc"]["credited"] == 0


def test_manual_scan_endpoint_admin_only(client, db, monkeypatch):
    _, token = make_user(client, db, "scan6")
    r = client.post("/api/wallet/deposits/scan", headers=auth_headers(token))
    assert r.status_code == 403
    _, admin_token = make_admin(client, db)
    r = client.post("/api/wallet/deposits/scan", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["active"] is False  # sin configurar, inactivo


def test_save_wallet_addresses_validation(client, db):
    _, token = make_user(client, db, "scan7")
    r = client.put("/api/wallet/addresses", json={"bsc_address": "no-es-una-direccion"},
                   headers=auth_headers(token))
    assert r.status_code == 422
    r = client.put("/api/wallet/addresses", json={"bsc_address": SENDER_BSC},
                   headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["bsc_address"] == SENDER_BSC
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["bsc_address"] == SENDER_BSC


def test_deposit_info_endpoint(client, db):
    _, token = make_user(client, db, "scan8")
    r = client.get("/api/wallet/deposit-info", headers=auth_headers(token))
    assert r.status_code == 200
    # UNA SOLA direccion (BSC): sin TRON en la respuesta
    assert r.json()["network"] == "BSC"
    assert "tron" not in r.json()
    assert r.json()["min_deposit_usdt"] == 1
    assert r.json()["auto_credit"] == {"bsc": False, "active": False}
    assert r.json()["configured"] is False
    assert r.json()["my_address"] is None


def test_admin_approve_deposit_credits_balance(client, db):
    # Deposito en pending (sin keys) -> el admin lo aprueba tras revisar BscScan
    _, token = make_user(client, db, "scan9")
    r = client.post("/api/wallet/deposits",
                    json={"tx_hash": "0xapprove0000000000000000000000000000000000000000000000000001",
                          "network": "BSC", "amount_usdt": 40},
                    headers=auth_headers(token))
    assert r.status_code == 201
    assert r.json()["status"] == "pending_verification"
    dep_id = r.json()["id"]
    assert client.get("/api/me", headers=auth_headers(token)).json()["usdt_balance"] == 0
    # No admin -> 403
    assert client.post(f"/api/admin/deposits/{dep_id}/approve",
                       headers=auth_headers(token)).status_code == 403
    _, admin_token = make_admin(client, db)
    r = client.post(f"/api/admin/deposits/{dep_id}/approve", headers=auth_headers(admin_token))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"
    assert client.get("/api/me", headers=auth_headers(token)).json()["usdt_balance"] == 40
    # Segunda aprobacion -> 422 (no se acredita dos veces)
    r = client.post(f"/api/admin/deposits/{dep_id}/approve", headers=auth_headers(admin_token))
    assert r.status_code == 422
    assert client.get("/api/me", headers=auth_headers(token)).json()["usdt_balance"] == 40
    assert db.query(Deposit).filter(Deposit.id == dep_id).count() == 1


def test_admin_approve_deposit_not_found_404(client, db):
    _, admin_token = make_admin(client, db)
    r = client.post("/api/admin/deposits/999999/approve", headers=auth_headers(admin_token))
    assert r.status_code == 404
