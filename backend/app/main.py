"""CRYPTO MINING GAME - Backend FastAPI (Python, real, sin simulaciones).

Arranque: crea tablas, config y reward pool por defecto, y el primer admin
desde ADMIN_USERNAME / ADMIN_PASSWORD (si estan definidos y no existe).
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import config as cfg
from app.core.database import Base, SessionLocal, db_kind, engine
from app.core.rate_limit import rate_limit_middleware
from app.core.security import hash_password
from app.models.models import AppConfig, RewardPool, User
from app.services.economy import grant_starter_machine
from app.routers import admin, auth, machines, mining, missions, public, wallet, withdrawals

log = logging.getLogger("crypto-mining-game")


async def _deposit_scanner_loop():
    """Tarea en segundo plano: escanea depositos USDT entrantes cada
    SCAN_INTERVAL_SECONDS. Solo acredita cuando hay direcciones de deposito y
    API keys configuradas; si no, queda inactiva sin romper nada."""
    from app.services import scanner
    while True:
        try:
            if scanner.scan_configured()["active"]:
                db = SessionLocal()
                try:
                    result = scanner.scan_all(db)
                    if (result.get("bsc") or {}).get("credited"):
                        log.info("Escaneo de depositos: %s", result)
                finally:
                    db.close()
        except Exception as e:  # noqa: BLE001 - el loop nunca debe morir
            log.warning("Error en el escaneo de depositos: %s", e)
        await asyncio.sleep(cfg.SCAN_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if cfg.SECRET_KEY_GENERATED:
        log.warning("SECRET_KEY no definida: se genero una efimera solo para desarrollo. "
                    "Define SECRET_KEY en produccion o las sesiones se invalidaran al reiniciar.")
    if not cfg.DEPOSIT_BSC_ADDRESS:
        log.warning("Sin DEPOSIT_BSC_ADDRESS: los depositos quedaran en "
                    "pending_verification y NUNCA se acreditaran automaticamente.")
    init_db()
    scanner_task = None
    if cfg.SCAN_ENABLED:
        scanner_task = asyncio.create_task(_deposit_scanner_loop())
        log.info("Escaneo automatico de depositos activado (cada %ss, solo con "
                 "direcciones y API keys configuradas)", cfg.SCAN_INTERVAL_SECONDS)
    yield
    if scanner_task is not None:
        scanner_task.cancel()


app = FastAPI(title="Crypto Mining Game API", version="1.0.0", lifespan=lifespan)
app.middleware("http")(rate_limit_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(AppConfig).filter(AppConfig.id == 1).first():
            db.add(AppConfig(id=1))
        if not db.query(RewardPool).filter(RewardPool.id == 1).first():
            db.add(RewardPool(id=1))
        db.commit()
        if cfg.ADMIN_USERNAME and cfg.ADMIN_PASSWORD:
            existing = db.query(User).filter(User.username == cfg.ADMIN_USERNAME).first()
            if not existing:
                admin_user = User(username=cfg.ADMIN_USERNAME,
                                  password_hash=hash_password(cfg.ADMIN_PASSWORD),
                                  is_admin=True, referral_code="ADMIN001")
                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
                grant_starter_machine(db, admin_user)
                db.commit()
                log.info("Admin inicial creado: %s", cfg.ADMIN_USERNAME)
    finally:
        db.close()


@app.get("/health")
def health():
    from app.services import scanner
    return {"status": "ok", "db": db_kind(),
            "deposits_configured": bool(cfg.DEPOSIT_BSC_ADDRESS),
            "auto_credit": scanner.scan_configured()}


app.include_router(auth.router)
app.include_router(mining.router)
app.include_router(machines.router)
app.include_router(missions.router)
app.include_router(wallet.router)
app.include_router(withdrawals.router)
app.include_router(public.router)
app.include_router(admin.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
