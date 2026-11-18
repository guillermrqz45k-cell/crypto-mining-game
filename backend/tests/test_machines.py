"""Catalogo de 9 niveles, Minero Inicial gratis, compra y overclock."""
from tests.conftest import auth_headers, make_user

# Tabla final de 9 niveles (AMO + escalera GoMining en 6-8)
LEVELS = {
    "level_0": (0, 5),
    "level_1": (10, 10),
    "level_2": (50, 60),
    "level_3": (150, 200),
    "level_4": (350, 500),
    "level_5": (750, 1200),
    "level_6": (1400, 2500),
    "level_7": (2800, 5500),
    "level_8": (5000, 12000),
}


def test_catalog_has_nine_levels(client):
    r = client.get("/api/machines")
    assert r.status_code == 200
    assert len(r.json()) == 9
    by_id = {m["id"]: m for m in r.json()}
    for mid, (price, hr) in LEVELS.items():
        assert by_id[mid]["price_usdt"] == price, mid
        assert by_id[mid]["hashrate"] == hr, mid
    # Los ids viejos (5 maquinas) ya no existen
    for old in ("usb_miner", "gpu_rig", "asic_s9", "asic_farm", "quantum_rig"):
        assert old not in by_id
    assert by_id["level_0"]["is_starter"] is True
    assert by_id["level_0"]["level"] == 0
    assert by_id["level_8"]["level"] == 8
    # Disponibilidad: solo 0-4 disponibles; 5-8 bloqueados ("Proximamente")
    for mid in ("level_0", "level_1", "level_2", "level_3", "level_4"):
        assert by_id[mid]["available"] is True, mid
    for mid in ("level_5", "level_6", "level_7", "level_8"):
        assert by_id[mid]["available"] is False, mid
    # Payback con 20,83 HCK por H/s por hora y 10.000 HCK = 1 USDT:
    # nivel 1 -> 20 dias; a mayor inversion, mas rapida la recuperacion
    assert by_id["level_0"]["payback_days"] is None
    assert abs(by_id["level_1"]["payback_days"] - 20) < 0.1
    assert abs(by_id["level_2"]["payback_days"] - 16.7) < 0.1
    assert abs(by_id["level_3"]["payback_days"] - 15) < 0.1
    assert abs(by_id["level_4"]["payback_days"] - 14) < 0.1
    assert abs(by_id["level_5"]["payback_days"] - 12.5) < 0.1
    assert abs(by_id["level_8"]["payback_days"] - 8.3) < 0.1


def test_new_user_starts_with_free_starter(client, db):
    user, token = make_user(client, db, "starter1")
    mine = client.get("/api/machines/mine", headers=auth_headers(token)).json()
    assert len(mine) == 1
    assert mine[0]["machine_id"] == "level_0"
    assert mine[0]["hashrate"] == 5
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["hashrate"] == 5


def test_buy_starter_when_owned_422(client, db):
    _, token = make_user(client, db, "starter2")
    r = client.post("/api/machines/buy", json={"machine_id": "level_0"}, headers=auth_headers(token))
    assert r.status_code == 422


def test_buy_unknown_machine_404(client, db):
    _, token = make_user(client, db, "shop0")
    r = client.post("/api/machines/buy", json={"machine_id": "usb_miner"}, headers=auth_headers(token))
    assert r.status_code == 404


def test_buy_insufficient_402(client, db):
    _, token = make_user(client, db, "shop1", usdt=5)
    r = client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    assert r.status_code == 402


def test_buy_ok_discounts_and_raises_hashrate(client, db):
    _, token = make_user(client, db, "shop2", usdt=100)
    # Rig GPU 50 USDT, 60 H/s + Minero Inicial 5 H/s = 65 H/s
    r = client.post("/api/machines/buy", json={"machine_id": "level_2"}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json()["usdt_balance"] == 50
    assert r.json()["hashrate"] == 65
    mine = client.get("/api/machines/mine", headers=auth_headers(token)).json()
    assert len(mine) == 2
    assert {m["machine_id"] for m in mine} == {"level_0", "level_2"}


def test_buy_locked_level_403(client, db):
    # Niveles 5-8 bloqueados: ni con saldo se pueden comprar
    _, token = make_user(client, db, "shop7", usdt=20000)
    for mid in ("level_5", "level_6", "level_7", "level_8"):
        r = client.post("/api/machines/buy", json={"machine_id": mid}, headers=auth_headers(token))
        assert r.status_code == 403, (mid, r.text)
        assert "Proximamente" in r.json()["detail"]
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["usdt_balance"] == 20000  # no se desconto nada


def test_buy_each_level_price_and_hashrate(client, db):
    # Compra de cada nivel DISPONIBLE (1-4) con su precio exacto
    _, token = make_user(client, db, "shop5", usdt=20000)
    for mid, (price, hr) in LEVELS.items():
        if mid == "level_0":
            continue
        if mid in ("level_5", "level_6", "level_7", "level_8"):
            continue  # bloqueados
        r = client.post("/api/machines/buy", json={"machine_id": mid}, headers=auth_headers(token))
        assert r.status_code == 200, (mid, r.text)
    me = client.get("/api/me", headers=auth_headers(token)).json()
    total_hr = 5 + 10 + 60 + 200 + 500
    assert me["hashrate"] == total_hr
    total_price = 10 + 50 + 150 + 350
    assert me["usdt_balance"] == 20000 - total_price


def test_upgrade_overclock(client, db):
    _, token = make_user(client, db, "shop3", usdt=100)
    r = client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    owned_id = r.json()["owned_machine_id"]
    # Overclock nivel 1: 20% de 10 USDT = 2 USDT; la maquina pasa a 10 * 1.25 = 12.5 H/s
    # (el endpoint de upgrade devuelve el hashrate de la maquina, no el total del usuario)
    r = client.post("/api/machines/upgrade", json={"owned_machine_id": owned_id}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json()["overclock_level"] == 1
    assert r.json()["hashrate"] == 12.5
    assert r.json()["usdt_balance"] == 88
    # Total del usuario: 12.5 de la maquina + 5 del Minero Inicial = 17.5 H/s
    assert client.get("/api/me", headers=auth_headers(token)).json()["hashrate"] == 17.5


def test_upgrade_starter_422(client, db):
    _, token = make_user(client, db, "shop6")
    mine = client.get("/api/machines/mine", headers=auth_headers(token)).json()
    starter_id = mine[0]["id"]
    r = client.post("/api/machines/upgrade", json={"owned_machine_id": starter_id},
                    headers=auth_headers(token))
    assert r.status_code == 422


def test_upgrade_max_level_422(client, db):
    _, token = make_user(client, db, "shop4", usdt=10000)
    r = client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    owned_id = r.json()["owned_machine_id"]
    for _ in range(5):
        assert client.post("/api/machines/upgrade", json={"owned_machine_id": owned_id},
                           headers=auth_headers(token)).status_code == 200
    r = client.post("/api/machines/upgrade", json={"owned_machine_id": owned_id}, headers=auth_headers(token))
    assert r.status_code == 422
