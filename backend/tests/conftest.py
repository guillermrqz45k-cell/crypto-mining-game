"""Fixtures: SQLite temporal, override de get_db, reseteo del rate limiter."""
import os
import tempfile
from decimal import Decimal

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-para-tests"
os.environ["ADMIN_USERNAME"] = ""
os.environ["ADMIN_PASSWORD"] = ""
os.environ["DEPOSIT_BSC_ADDRESS"] = ""
os.environ["DEPOSIT_TRON_ADDRESS"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.rate_limit import reset_store  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402  (importa los modelos -> registra tablas en Base.metadata)
from app.models.models import User  # noqa: E402

TEST_ENGINE = create_engine(f"sqlite:///{_tmp}/test.db", connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)


def _override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_db


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    reset_store()
    yield
    reset_store()


@pytest.fixture(autouse=True)
def _clean_db():
    """Aislamiento total entre tests: vacia todas las tablas y restaura
    config y reward pool a sus valores por defecto antes de cada test."""
    from app.models.models import AppConfig, RewardPool
    session = TestSession()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.add(AppConfig(id=1))
    session.add(RewardPool(id=1))
    session.commit()
    session.close()
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()


def register(client, username, password="secret123", referral_code=None):
    payload = {"username": username, "password": password}
    if referral_code:
        payload["referral_code"] = referral_code
    return client.post("/api/auth/register", json=payload)


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def make_user(client, db, username, password="secret123", usdt=0, hck=0, referral_code=None):
    r = register(client, username, password, referral_code)
    assert r.status_code == 201, r.text
    data = r.json()
    if usdt or hck:
        u = db.query(User).filter(User.username == username).first()
        u.usdt_balance = Decimal(str(usdt))
        u.hck_balance = Decimal(str(hck))
        u.total_hck_earned = Decimal(str(hck))
        db.commit()
    return data["user"], data["access_token"]


def make_admin(client, db, username="admin1", password="admin123"):
    u = User(username=username, password_hash=hash_password(password),
             is_admin=True, referral_code="ADMIN001")
    db.add(u)
    db.commit()
    db.refresh(u)
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return u, r.json()["access_token"]
