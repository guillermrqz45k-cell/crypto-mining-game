"""Economia del juego: catalogo, hashrate, niveles, config, auditoria, serializacion."""
import secrets
import string
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.models import AppConfig, AuditLog, OwnedMachine, RewardPool, Transaction, User

MACHINES = {
    # 9 niveles de mineria (AMO, 2026-11-17). Nivel 0 gratis: es el minero
    # inicial que todo usuario recibe al registrarse. Niveles 1-8 se compran
    # con USDT depositado. Economia: 20,83 HCK por H/s por hora, 10.000 HCK =
    # 1 USDT, tope de almacen 24 h. Solo los niveles 0-4 estan disponibles;
    # 5-8 estan bloqueados ("Proximamente").
    "level_0": {"id": "level_0", "name": "Minero Inicial", "price_usdt": Decimal("0"), "hashrate": Decimal("5"), "available": True},
    "level_1": {"id": "level_1", "name": "Minero USB", "price_usdt": Decimal("10"), "hashrate": Decimal("10"), "available": True},
    "level_2": {"id": "level_2", "name": "Rig GPU", "price_usdt": Decimal("50"), "hashrate": Decimal("60"), "available": True},
    "level_3": {"id": "level_3", "name": "ASIC S9", "price_usdt": Decimal("150"), "hashrate": Decimal("200"), "available": True},
    "level_4": {"id": "level_4", "name": "Granja ASIC", "price_usdt": Decimal("350"), "hashrate": Decimal("500"), "available": True},
    "level_5": {"id": "level_5", "name": "Rig Cuántico", "price_usdt": Decimal("750"), "hashrate": Decimal("1200"), "available": False},
    "level_6": {"id": "level_6", "name": "Centro de Datos", "price_usdt": Decimal("1400"), "hashrate": Decimal("2500"), "available": False},
    "level_7": {"id": "level_7", "name": "Granja Cuántica", "price_usdt": Decimal("2800"), "hashrate": Decimal("5500"), "available": False},
    "level_8": {"id": "level_8", "name": "Núcleo HCK", "price_usdt": Decimal("5000"), "hashrate": Decimal("12000"), "available": False},
}
# Id del minero inicial gratuito (nivel 0). No se vende ni admite overclock.
STARTER_MACHINE_ID = "level_0"
MAX_OVERCLOCK = 5
# Deposito minimo en USDT que el escaner automatico acredita (anti-polvo).
MIN_DEPOSIT_USDT = Decimal("1")
DAILY_BONUS = [Decimal("100"), Decimal("200"), Decimal("300"), Decimal("400"),
               Decimal("500"), Decimal("750"), Decimal("1000")]


def payback_days(machine: dict, production_per_hash: Decimal, hck_to_usdt_rate: Decimal):
    """Dias para recuperar la inversion minando 24 h/dia y recogiendo a diario.
    None para el Minero Inicial (gratis). Con 20,83 HCK por H/s por hora y
    10.000 HCK = 1 USDT: nivel 1 -> 20 dias, nivel 2 -> 16,7, nivel 3 -> 15,
    nivel 4 -> 14, nivel 5 -> 12,5, nivel 6 -> 11,2, nivel 7 -> 10,2,
    nivel 8 -> 8,3."""
    price = Decimal(machine["price_usdt"])
    if price <= 0:
        return None
    daily_hck = Decimal(machine["hashrate"]) * Decimal(production_per_hash) * Decimal("24")
    daily_usdt = daily_hck / Decimal(hck_to_usdt_rate)
    if daily_usdt <= 0:
        return None
    return float(price / daily_usdt)


def get_config(db: Session) -> AppConfig:
    cfg = db.query(AppConfig).filter(AppConfig.id == 1).first()
    if cfg is None:
        cfg = AppConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def get_pool(db: Session) -> RewardPool:
    pool = db.query(RewardPool).filter(RewardPool.id == 1).first()
    if pool is None:
        pool = RewardPool(id=1)
        db.add(pool)
        db.commit()
        db.refresh(pool)
    return pool


def grant_starter_machine(db: Session, user: User) -> OwnedMachine | None:
    """Otorga el Minero Inicial (nivel 0, gratis) si el usuario aun no lo tiene.
    Idempotente: nunca duplica el minero inicial."""
    existing = db.query(OwnedMachine).filter(
        OwnedMachine.user_id == user.id, OwnedMachine.machine_id == STARTER_MACHINE_ID).first()
    if existing:
        return None
    om = OwnedMachine(user_id=user.id, machine_id=STARTER_MACHINE_ID)
    db.add(om)
    return om


def machine_hashrate(machine_id: str, overclock_level: int) -> Decimal:
    base = MACHINES[machine_id]["hashrate"]
    return base * (Decimal("1") + Decimal("0.25") * Decimal(overclock_level))


def user_hashrate(db: Session, user_id: int) -> Decimal:
    total = Decimal("0")
    for om in db.query(OwnedMachine).filter(OwnedMachine.user_id == user_id).all():
        total += machine_hashrate(om.machine_id, om.overclock_level)
    return total


def upgrade_cost(machine_id: str, next_level: int) -> Decimal:
    """Coste overclock: 20% del precio base * nivel destino."""
    return MACHINES[machine_id]["price_usdt"] * Decimal("0.20") * Decimal(next_level)


def generate_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def check_level_up(db: Session, user: User) -> bool:
    """Sube de nivel mientras xp >= 1000*nivel actual. Premio 500*nivel nuevo en HCK.
    Devuelve True si subio al menos un nivel."""
    leveled = False
    while user.xp >= 1000 * user.level:
        user.level += 1
        reward = Decimal(500 * user.level)
        user.hck_balance = Decimal(user.hck_balance) + reward
        user.total_hck_earned = Decimal(user.total_hck_earned) + reward
        add_transaction(db, user.id, "reward", amount_hck=reward,
                        description=f"Premio por subir a nivel {user.level}")
        leveled = True
    return leveled


def add_transaction(db: Session, user_id: int, type_: str, amount_hck=Decimal("0"),
                    amount_usdt=Decimal("0"), description: str = "") -> Transaction:
    tx = Transaction(user_id=user_id, type=type_, amount_hck=Decimal(amount_hck),
                     amount_usdt=Decimal(amount_usdt), description=description)
    db.add(tx)
    return tx


def audit(db: Session, action: str, user_id=None, details: str = "", ip: str = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, details=details, ip=ip))


def user_public(user: User, db: Session) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "level": user.level,
        "xp": user.xp,
        "usdt_balance": float(user.usdt_balance),
        "hck_balance": float(user.hck_balance),
        "hashrate": float(user_hashrate(db, user.id)),
        "referral_code": user.referral_code,
        "is_admin": user.is_admin,
        "is_banned": user.is_banned,
        "total_hck_earned": float(user.total_hck_earned),
        "daily_bonus_streak": user.daily_bonus_streak,
        "mining_active": user.mining_active,
        "bsc_address": user.bsc_address,
        "tron_address": user.tron_address,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
