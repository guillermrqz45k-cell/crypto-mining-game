from tests.conftest import auth_headers, make_user, register


def test_register_ok(client):
    r = register(client, "alice")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["access_token"]
    assert body["user"]["username"] == "alice"
    assert body["user"]["level"] == 1
    assert body["user"]["hck_balance"] == 0
    assert body["user"]["referral_code"]


def test_register_duplicate(client):
    assert register(client, "bob").status_code == 201
    r = register(client, "bob")
    assert r.status_code == 400


def test_register_short_password(client):
    r = client.post("/api/auth/register", json={"username": "carl", "password": "123"})
    assert r.status_code == 422


def test_login_ok_and_wrong(client, db):
    make_user(client, db, "dave")
    r = client.post("/api/auth/login", json={"username": "dave", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "dave"
    r = client.post("/api/auth/login", json={"username": "dave", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_token(client, db):
    assert client.get("/api/me").status_code == 401
    _, token = make_user(client, db, "erin")
    r = client.get("/api/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["username"] == "erin"
