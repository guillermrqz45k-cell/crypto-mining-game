"""Mineria: produccion por tiempo, tope de capacidad, sin mineria no produce,
collect suma XP y sube de nivel. Todo usuario empieza con el Minero Inicial
(nivel 0, gratis, 5 H/s), asi que el hashrate base es 5 H/s."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from tests.conftest import auth_headers, make_user
from app.models.models import User


def _backdate(db, username, hours):
    u = db.query(User).filter(User.username == username).first()
    u.mining_started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    db.commit()


def test_start_with_starter_only_ok(client, db):
    # El usuario nuevo ya puede minar con su Minero Inicial gratis (5 H/s)
    _, token = make_user(client, db, "miner1")
    r = client.post("/api/mining/start", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json()["mining_active"] is True
    assert r.json()["hashrate"] == 5


def test_start_twice_422(client, db):
    _, token = make_user(client, db, "miner2", usdt=100)
    assert client.post("/api/machines/buy", json={"machine_id": "level_1"},
                       headers=auth_headers(token)).status_code == 200
    assert client.post("/api/mining/start", headers=auth_headers(token)).status_code == 200
    assert client.post("/api/mining/start", headers=auth_headers(token)).status_code == 422


def test_production_over_time_and_capacity_cap(client, db):
    # Minero Inicial 5 H/s + level_1 10 H/s = 15 H/s -> 312,45 HCK/h (20,83 por H/s),
    # capacidad 24 h = 7.498,8 HCK
    _, token = make_user(client, db, "miner3", usdt=100)
    client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    client.post("/api/mining/start", headers=auth_headers(token))
    _backdate(db, "miner3", 2)
    r = client.get("/api/mining/status", headers=auth_headers(token))
    assert r.status_code == 200
    assert abs(r.json()["pending_hck"] - 624.9) < 1
    assert abs(r.json()["capacity_hck"] - 7498.8) < 1
    assert r.json()["storage_full"] is False
    _backdate(db, "miner3", 10)
    r = client.get("/api/mining/status", headers=auth_headers(token))
    assert abs(r.json()["pending_hck"] - 3124.5) < 1  # aun no llega al tope de 24 h
    assert r.json()["storage_full"] is False
    _backdate(db, "miner3", 30)
    r = client.get("/api/mining/status", headers=auth_headers(token))
    assert abs(r.json()["pending_hck"] - 7498.8) < 1  # tope de capacidad
    assert r.json()["storage_full"] is True


def test_no_mining_no_production(client, db):
    _, token = make_user(client, db, "miner4", usdt=100)
    client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    r = client.get("/api/mining/status", headers=auth_headers(token))
    assert r.json()["pending_hck"] == 0
    assert r.json()["mining_active"] is False


def test_stop_then_collect(client, db):
    _, token = make_user(client, db, "miner5", usdt=100)
    client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    client.post("/api/mining/start", headers=auth_headers(token))
    _backdate(db, "miner5", 2)
    r = client.post("/api/mining/stop", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["mining_active"] is False
    assert abs(r.json()["pending_hck"] - 624.9) < 1
    r = client.post("/api/mining/collect", headers=auth_headers(token))
    assert r.status_code == 200
    assert abs(r.json()["collected_hck"] - 624.9) < 1
    assert r.json()["xp_gained"] == 6  # 1 XP por cada 100 HCK
    r = client.get("/api/me", headers=auth_headers(token))
    assert abs(r.json()["hck_balance"] - 624.9) < 1
    assert r.json()["xp"] == 6


def test_collect_levels_up(client, db):
    # Granja ASIC 500 H/s + inicial 5 = 505 H/s -> 10.519,15 HCK/h (20,83 por H/s).
    # Con xp=990, recolectar 10.519,15 HCK -> +105 XP -> nivel 2 + premio 1000 HCK
    _, token = make_user(client, db, "miner6", usdt=1000)
    client.post("/api/machines/buy", json={"machine_id": "level_4"}, headers=auth_headers(token))
    u = db.query(User).filter(User.username == "miner6").first()
    u.xp = 990
    db.commit()
    client.post("/api/mining/start", headers=auth_headers(token))
    _backdate(db, "miner6", 1)
    r = client.post("/api/mining/collect", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["level_up"] is True
    assert r.json()["level"] == 2
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["level"] == 2
    # 10.519,15 recolectados + 1000 de premio por subir a nivel 2
    assert abs(me["hck_balance"] - 11519.15) < 1


def test_status_reports_production_rate_and_storage(client, db):
    # El frontend necesita la tasa y el tope para el contador en vivo
    _, token = make_user(client, db, "miner7")
    r = client.get("/api/mining/status", headers=auth_headers(token))
    assert r.json()["production_per_hash"] == 20.83
    assert r.json()["storage_hours"] == 24
    # Minero Inicial 5 H/s -> 5 * 20,83 / 3600 HCK por segundo
    assert abs(r.json()["hck_per_second"] - (5 * 20.83 / 3600)) < 1e-6
