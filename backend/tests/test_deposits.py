"""Depositos: idempotencia, sin claves -> pendiente sin acreditar,
verificacion mockeada (BscScan/TronGrid): exito acredita, monto distinto no."""
from decimal import Decimal

import pytest

from tests.conftest import auth_headers, make_user
from app.models.models import Deposit, User


def _deposit(client, token, tx="0xabc123456789", network="BSC", amount=50):
    return client.post("/api/wallet/deposits",
                       json={"tx_hash": tx, "network": network, "amount_usdt": amount},
                       headers=auth_headers(token))


def test_deposit_without_keys_stays_pending_never_credited(client, db):
    _, token = make_user(client, db, "dep1")
    r = _deposit(client, token)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending_verification"
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 0  # NUNCA se acredita sin verificacion


def test_deposit_idempotent_409(client, db):
    _, token = make_user(client, db, "dep2")
    assert _deposit(client, token).status_code == 201
    r = _deposit(client, token)
    assert r.status_code == 409
    assert db.query(Deposit).filter(Deposit.tx_hash == "0xabc123456789").count() == 1


def test_deposit_verified_mock_credits_once(client, db, monkeypatch):
    _, token = make_user(client, db, "dep3")

    def fake_verify(network, tx_hash, amount, address):
        return {"status": "verified", "reason": None}

    monkeypatch.setattr("app.services.verification.verify_deposit", fake_verify)
    r = _deposit(client, token)
    assert r.json()["status"] == "verified"
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 50


def test_deposit_wrong_amount_rejected_no_credit(client, db, monkeypatch):
    _, token = make_user(client, db, "dep4")

    def fake_verify(network, tx_hash, amount, address):
        return {"status": "rejected", "reason": "monto on-chain 10 != declarado 50"}

    monkeypatch.setattr("app.services.verification.verify_deposit", fake_verify)
    r = _deposit(client, token)
    assert r.json()["status"] == "rejected"
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 0


def test_deposit_tron_verified_mock(client, db, monkeypatch):
    _, token = make_user(client, db, "dep5")

    def fake_verify(network, tx_hash, amount, address):
        assert network == "TRON"
        return {"status": "verified", "reason": None}

    monkeypatch.setattr("app.services.verification.verify_deposit", fake_verify)
    r = _deposit(client, token, tx="a1b2c3d4e5f6a7b8c9d0", network="TRON", amount=25)
    assert r.json()["status"] == "verified"
    assert client.get("/api/me", headers=auth_headers(token)).json()["usdt_balance"] == 25


def test_wallet_shows_deposit_addresses_config(client, db):
    _, token = make_user(client, db, "dep6")
    r = client.get("/api/wallet", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["hck_to_usdt_rate"] == 10000
    # Sin direcciones configuradas en tests: configured False, nunca inventadas
    assert r.json()["deposit_addresses"]["configured"] is False
    assert r.json()["deposit_addresses"]["bsc"] is None
