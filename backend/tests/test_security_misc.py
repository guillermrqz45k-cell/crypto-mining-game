"""Anti-manipulacion de saldo, rate limiting, misiones, bono diario,
referidos, leaderboard, stats y admin."""
from tests.conftest import auth_headers, make_admin, make_user, register


def test_collect_ignores_client_supplied_balance(client, db):
    _, token = make_user(client, db, "sec1", usdt=100)
    client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    client.post("/api/mining/start", headers=auth_headers(token))
    # Intento de manipulacion: enviar hck_balance en el body
    r = client.post("/api/mining/collect", json={"hck_balance": 999999, "collected_hck": 999999},
                    headers=auth_headers(token))
    assert r.status_code == 200
    me = client.get("/api/me", headers=auth_headers(token)).json()
    assert me["hck_balance"] < 1  # sin tiempo transcurrido no hay nada que recolectar
    # Tambien en compra: campos extra no crean saldo
    r = client.post("/api/machines/buy",
                    json={"machine_id": "level_8", "usdt_balance": 99999, "hck_balance": 99999},
                    headers=auth_headers(token))
    assert r.status_code == 402  # saldo real insuficiente (90 USDT < 5000), no el inventado


def test_rate_limit_login_11th_429(client, db):
    make_user(client, db, "rl1")
    responses = [client.post("/api/auth/login",
                             json={"username": "rl1", "password": "secret123"})
                 for _ in range(11)]
    assert responses[8].status_code == 200  # 9o login = peticion 10 (con el registro), permitido
    assert responses[9].status_code == 429  # 10o login -> 429
    assert responses[10].status_code == 429


def test_daily_bonus_and_mission_claim(client, db):
    _, token = make_user(client, db, "bonus1")
    r = client.post("/api/daily-bonus/claim", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["streak"] == 1
    assert r.json()["reward_hck"] == 100
    assert client.post("/api/daily-bonus/claim", headers=auth_headers(token)).status_code == 422
    missions = client.get("/api/missions", headers=auth_headers(token)).json()
    assert len(missions) == 5
    claim_daily = next(m for m in missions if m["id"] == "claim_daily")
    assert claim_daily["completed"] is True
    r = client.post("/api/missions/claim", json={"mission_id": "claim_daily"},
                    headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["reward_hck"] == 100
    # Segunda reclamacion el mismo dia -> 422
    assert client.post("/api/missions/claim", json={"mission_id": "claim_daily"},
                       headers=auth_headers(token)).status_code == 422


def test_referral_bonus_on_first_machine(client, db):
    referrer, ref_token = make_user(client, db, "ref1")
    code = referrer["referral_code"]
    _, token = make_user(client, db, "ref2", usdt=100, referral_code=code)
    r = client.post("/api/machines/buy", json={"machine_id": "level_1"}, headers=auth_headers(token))
    assert r.status_code == 200
    # Referido y referente ganan 500 HCK cada uno en la primera compra
    assert client.get("/api/me", headers=auth_headers(token)).json()["hck_balance"] == 500
    assert client.get("/api/me", headers=auth_headers(ref_token)).json()["hck_balance"] == 500
    refs = client.get("/api/referrals", headers=auth_headers(ref_token)).json()
    assert refs["referred_count"] == 1
    assert refs["referred_users"][0]["username"] == "ref2"
    assert refs["referral_code"] == code


def test_leaderboard_and_stats(client, db):
    make_user(client, db, "lb1", hck=1000)
    make_user(client, db, "lb2", hck=5000)
    lb = client.get("/api/leaderboard").json()
    assert lb["by_hck"][0]["username"] == "lb2"
    stats = client.get("/api/stats").json()
    assert stats["total_users"] >= 2
    assert len(stats["production_history"]) == 14


def test_admin_endpoints_and_ban(client, db):
    user, token = make_user(client, db, "adm1")
    _, admin_token = make_admin(client, db)
    # No admin -> 403
    assert client.get("/api/admin/users", headers=auth_headers(token)).status_code == 403
    # Admin lista con filtro
    r = client.get("/api/admin/users?search=adm1", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert any(u["username"] == "adm1" for u in r.json())
    # Config get/put
    cfg = client.get("/api/admin/config", headers=auth_headers(admin_token)).json()
    assert cfg["hck_to_usdt_rate"] == 10000
    r = client.put("/api/admin/config", json={"withdrawal_fee_percent": 3},
                   headers=auth_headers(admin_token))
    assert r.json()["withdrawal_fee_percent"] == 3
    # Ban / unban
    r = client.post(f"/api/admin/users/{user['id']}/ban", headers=auth_headers(admin_token))
    assert r.json()["is_banned"] is True
    assert client.get("/api/me", headers=auth_headers(token)).status_code == 403
    assert client.post(f"/api/admin/users/{user['id']}/unban",
                       headers=auth_headers(admin_token)).json()["is_banned"] is False
    # Auditoria y alertas de fraude
    assert client.get("/api/admin/audit", headers=auth_headers(admin_token)).status_code == 200
    alerts = client.get("/api/admin/fraud-alerts", headers=auth_headers(admin_token)).json()
    assert isinstance(alerts, list)
    stats = client.get("/api/admin/stats", headers=auth_headers(admin_token)).json()
    assert "total_users" in stats
