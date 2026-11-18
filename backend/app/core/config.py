"""Configuracion por variables de entorno. Sin valores reales por defecto."""
import os
import secrets

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/mining.db")

SECRET_KEY = os.environ.get("SECRET_KEY")
SECRET_KEY_GENERATED = False
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    SECRET_KEY_GENERATED = True

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

DEPOSIT_BSC_ADDRESS = os.environ.get("DEPOSIT_BSC_ADDRESS") or None
DEPOSIT_TRON_ADDRESS = os.environ.get("DEPOSIT_TRON_ADDRESS") or None
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY") or None
TRONGRID_API_KEY = os.environ.get("TRONGRID_API_KEY") or None

# Escaneo automatico de depositos (cada 5 min por defecto, solo si hay
# direcciones de deposito y API keys configuradas; ver services/scanner.py).
SCAN_ENABLED = os.environ.get("SCAN_ENABLED", "true").lower() in ("1", "true", "yes")
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "300"))
USDT_BSC_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
USDT_TRON_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
