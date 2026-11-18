"""Retiros: minimo, comision 2%, aprobacion con/sin fondos del pool, mark-paid."""
from tests.conftest import auth_headers, make_admin, make_user

BSC_ADDR = "0x" + "a" * 40
TRON_ADDR = "T" + "A" * 33


def _withdraw(client, token, amount=10, address=BSC_ADDR, network="BSC"):
    return client.post("/api/withdrawals",
                       json={"amount_usdt": amount, "address": address, "network": network},
                       headers=auth_headers(token))


def test_withdrawal_minimum_422(client, db):
    _, token = make_user(client, db, "wd1", hck=200000)
    assert _withdraw(client, token, amount=5).status_code == 422


def test_withdrawal_bad_address_422(client, db):
    _, token = make_user(client, db, "wd2", hck=200000)
    assert _withdraw(client, token, address="no-es-una-direccion").status_code == 422
    assert _withdraw(client, token, network="TRON", address="X" + "A" * 33).status_code == 422


def test_withdrawal_insufficient_hck_402(client, db):
    _, token = make_user(client, db, "wd3", hck=1000)
    assert _withdraw(client, token, amount=10).status_code == 402


def test_withdrawal_fee_2_percent(client, db):
    _, token = make_user(client, db, "wd4", hck=1000000)
    r = _withdraw(client, token, amount=100)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["fee_usdt"] == 2
    assert body["net_usdt"] == 98
    assert body["hck_spent"] == 1000000  # 100 USDT * 10000 HCK
    assert body["status"] == "pending"
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["hck_balance"] == 0


def test_approve_without_pool_funds_waiting(client, db):
    _, token = make_user(client, db, "wd5", hck=1000000)
    wd_id = _withdraw(client, token, amount=100).json()["id"]
    _, admin_token = make_admin(client, db)
    r = client.post(f"/api/admin/withdrawals/{wd_id}/approve", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["status"] == "waiting_funds"  # nunca se inventa dinero


def test_approve_with_funds_then_mark_paid(client, db):
    _, token = make_user(client, db, "wd6", hck=1000000)
    wd_id = _withdraw(client, token, amount=100).json()["id"]
    _, admin_token = make_admin(client, db)
    r = client.post("/api/admin/reward-pool/fund", json={"amount_usdt": 500},
                    headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["balance_usdt"] == 500
    r = client.post(f"/api/admin/withdrawals/{wd_id}/approve", headers=auth_headers(admin_token))
    assert r.json()["status"] == "approved"
    pool = client.get("/api/admin/reward-pool", headers=auth_headers(admin_token)).json()
    assert pool["balance_usdt"] == 400  # reservado del pool
    r = client.post(f"/api/admin/withdrawals/{wd_id}/mark-paid", json={"tx_hash": "0xpay123456789"},
                    headers=auth_headers(admin_token))
    assert r.json()["status"] == "paid"
    assert r.json()["tx_hash"] == "0xpay123456789"
    pool = client.get("/api/admin/reward-pool", headers=auth_headers(admin_token)).json()
    assert pool["total_paid"] == 100


def test_reject_refunds_hck(client, db):
    _, token = make_user(client, db, "wd7", hck=500000)
    wd_id = _withdraw(client, token, amount=10).json()["id"]
    _, admin_token = make_admin(client, db)
    r = client.post(f"/api/admin/withdrawals/{wd_id}/reject", json={"reason": "direccion sospechosa"},
                    headers=auth_headers(admin_token))
    assert r.json()["status"] == "rejected"
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["hck_balance"] == 500000  # reembolso completo
