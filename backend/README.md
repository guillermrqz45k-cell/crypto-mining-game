# CRYPTO MINING GAME — Backend (FastAPI, Python, REAL)

Plataforma de minería virtual de criptomonedas. **Todo es real en el sentido
que importa: el código es Python/FastAPI de verdad, la producción se calcula
en el servidor por tiempo transcurrido, los depósitos se verifican on-chain
por tx_hash + monto + dirección, y los retiros solo los paga un admin a mano.
No hay depósitos simulados, ni acreditación ficticia, ni claves privadas
guardadas en ningún sitio.**

## Regla de oro (decisión de AMO)

> La minería es virtual (HCKCOIN es un punto interno, NO un token on-chain),
> las recompensas están respaldadas por fondos reales disponibles, y **no hay
> depósitos, ganancias ni retiros simulados**. Sin rentabilidades garantizadas.

## Arranque rápido

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # rellenar SECRET_KEY y (cuando AMO las pase) las direcciones
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
# Docs interactivas: http://localhost:8000/docs
# Tests: .venv/bin/python -m pytest -q
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | no | SQLite por defecto (`sqlite:///./data/mining.db`); PostgreSQL si es `postgres://...` |
| `SECRET_KEY` | **sí en prod.** | Clave JWT. Sin ella se genera una efímera solo para desarrollo (se avisa en logs) y las sesiones se invalidan al reiniciar |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | sí para admin | Primer admin, creado al arrancar si no existe |
| `DEPOSIT_BSC_ADDRESS` | **sí (ya definida)** | Dirección USDT BEP-20 que recibe los depósitos: `0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d` (la de AMO, misma que en Dragon Land). **Sin ella, ningún depósito BSC se acredita**. UNA SOLA dirección: no hay TRON |
| `BSCSCAN_API_KEY` | cuando AMO la pase | Clave BscScan para verificar depósitos BSC on-chain (y para el escaneo automático) |

**Sin dirección de depósito y sin clave de API, todo depósito queda en
`pending_verification` y NUNCA se acredita automáticamente.** La dirección
BSC ya está definida en `.env.example` (`0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d`).
No hay ninguna dirección inventada en el código.

## Economía (valores por defecto, configurables en `/api/admin/config`)

- **HCKCOIN (HCK)**: moneda del juego, puntos internos, NO token on-chain.
  Tasa de retiro: **10.000 HCK = 1 USDT** (`hck_to_usdt_rate`).
- **Producción**: HCK/hora = `hashrate_total × 20,83` (`production_per_hash`).
  Ej: 10 H/s → 208,3 HCK/h. Se calcula en el **servidor** por tiempo
  transcurrido (sesión con `started_at`); sin minería activa no hay producción.
- **Capacidad ("nido")**: 24 horas de producción (`storage_hours`); si se llena,
  la minería se detiene hasta recolectar. Recogiendo a diario se captura el día
  completo: el nivel 1 ($10, 10 H/s) **recupera su inversión en 20 días** y a
  mayor inversión, más rápida la recuperación (nivel 2: ~16,7 días; nivel 3:
  15 días; nivel 4: 14 días). Tasa fija: **10.000 HCK = 1 USDT**.
- **Máquinas** — 9 niveles (compra con saldo USDT depositado, salvo el nivel 0
  que es gratis y lo recibe todo usuario al registrarse). Precios guiados por
  la escalera de GoMining (potencia casi duplicada por nivel, ~$17-22 por TH
  en sus niveles altos): los niveles 6-8 usan $1.400 / $2.800 / $5.000.
  **Solo los niveles 0-4 están disponibles; los niveles 5-8 están bloqueados
  ("Próximamente")** y comprarlos devuelve 403. El catálogo muestra
  `available` y `payback_days` por máquina.

  | id | Nivel | Nombre | Precio | Hashrate |
  |---|---|---|---|---|
  | `level_0` | 0 | Minero Inicial | GRATIS | 5 H/s |
  | `level_1` | 1 | Minero USB | 10 USDT | 10 H/s |
  | `level_2` | 2 | Rig GPU | 50 USDT | 60 H/s |
  | `level_3` | 3 | ASIC S9 | 150 USDT | 200 H/s |
  | `level_4` | 4 | Granja ASIC | 350 USDT | 500 H/s |
  | `level_5` | 5 | Rig Cuántico | 750 USDT | 1200 H/s |
  | `level_6` | 6 | Centro de Datos | 1400 USDT | 2500 H/s |
  | `level_7` | 7 | Granja Cuántica | 2800 USDT | 5500 H/s |
  | `level_8` | 8 | Núcleo HCK | 5000 USDT | 12000 H/s |

  **Overclock**: +25% hashrate por nivel, coste = 20% del precio base × nivel,
  máx. 5 niveles.
- **XP / niveles**: 1 XP por cada 100 HCK recolectados. Subir al nivel `n`
  requiere 1000×n XP acumulados. Al subir, premio = 500×n HCK.
- **Bono diario** (racha 7 días): 100, 200, 300, 400, 500, 750, 1000 HCK.
- **Referidos**: código único por usuario; referido y referente ganan **500 HCK**
  cada uno cuando el referido compra su **primera** máquina.
- **Misiones diarias** (resetean cada día): Mina 1 hora (300 HCK),
  Recolecta 1000 HCK (200 HCK), Compra tu primera máquina (500 HCK, una vez),
  Invita 1 amigo (500 HCK), Reclama el bono diario (100 HCK).

## Depósitos USDT (verificación on-chain REAL, una sola dirección BSC)

Dirección única de depósito (BSC/BEP-20): `0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d`
(la de AMO, misma que en Dragon Land). **No hay dirección TRON.**

`POST /api/wallet/deposits {tx_hash, network: "BSC", amount_usdt}` (registro
manual) y `GET /api/wallet/deposit-info` (dirección, mínimo 1 USDT, estado de
la acreditación automática, dirección BSC guardada del usuario):

1. **Idempotente por `tx_hash` único**: repetirlo devuelve **409** y no hay
   doble crédito.
2. **Sin `BSCSCAN_API_KEY`** → estado `pending_verification`, **nunca se
   acredita automáticamente**. El admin lo aprueba a mano con
   `POST /api/admin/deposits/{id}/approve` tras revisar el tx_hash en BscScan
   (acredita el saldo y queda en el audit log).
3. **Con clave**, se verifica on-chain con BscScan `tokentx` del contrato USDT
   BEP-20 `0x55d398326f99059fF775485246999027B3197955`. El tx debe existir,
   `to == DEPOSIT_BSC_ADDRESS` y `value == amount` (18 decimales).
4. Solo si **todo coincide** se acredita el USDT. Si no, estado `rejected`
   con el motivo. Error de red/API → queda pendiente, nunca se acredita.

### Acreditación automática (escaneo en segundo plano)

El usuario guarda su dirección BSC en su perfil (`PUT /api/wallet/addresses`).
Cada 5 minutos (`SCAN_INTERVAL_SECONDS`, desactivable con `SCAN_ENABLED=false`)
el backend consulta BscScan por las transferencias USDT entrantes a la
dirección de depósito; por cada una busca al usuario cuya dirección guardada
coincida con el remitente y acredita el depósito (idempotente por tx_hash,
mínimo 1 USDT, con audit log). Solo activo con dirección + `BSCSCAN_API_KEY`
configuradas; sin ellas queda inactivo sin romper nada. El admin puede
disparar un escaneo manual con `POST /api/wallet/deposits/scan`.
La sala de minería del frontend (`MiningRoom`) muestra los equipos reales del
usuario con ventiladores, LEDs, temperatura y hashrate, y un contador de HCK
en vivo.

## Retiros (nunca automáticos)

`POST /api/withdrawals {amount_usdt, address, network}`: mínimo **10 USDT**,
comisión **2%** (configurable). Se descuentan los HCK al crear el retiro
(10.000 HCK por USDT). Validación de formato: BSC `0x` + 40 hex; TRON base58
que empieza por `T` (34 caracteres). El retiro queda `pending`.

El admin lo aprueba solo si el **reward pool** tiene saldo suficiente; si no,
queda `waiting_funds` (nunca se inventa dinero). `mark-paid` registra el
`tx_hash` del pago que el admin envía **desde su propia wallet**. El sistema
**NUNCA guarda claves privadas ni paga on-chain automáticamente**.

El **reward pool** (`/api/admin/reward-pool`) solo registra saldo: el admin
transfiere los fondos reales por fuera y anota el fondeo con
`POST /api/admin/reward-pool/fund`.

## Seguridad

- Contraseñas **bcrypt** (directo, sin passlib), JWT Bearer con expiración de
  7 días (`SECRET_KEY` de env).
- Saldo, recompensas y producción se calculan **siempre en el servidor**;
  ningún endpoint acepta saldo/HCK/hashrate del cliente.
- Rate limiting propio (middleware): 100 req/min general, 10/min
  login/register, 5/min creación de depósitos y retiros.
- IP de registro/login registrada para detección de fraude.
- **Auditoría**: tabla `audit_logs` con cada acción financiera y de admin.
- Montos con `Decimal`, nunca `float`, para dinero.

## Endpoints

Auth: `POST /api/auth/register`, `POST /api/auth/login` · Perfil: `GET /api/me`
· Minería: `GET /api/mining/status`, `POST /api/mining/start|stop|collect`
· Máquinas: `GET /api/machines`, `GET /api/machines/mine`,
`POST /api/machines/buy|upgrade` · Misiones: `GET /api/missions`,
`POST /api/missions/claim`, `POST /api/daily-bonus/claim` · Wallet:
`GET /api/wallet`, `POST /api/wallet/deposits`, `GET /api/wallet/deposits`,
`GET /api/wallet/transactions` · Retiros: `POST /api/withdrawals`,
`GET /api/withdrawals` · `GET /api/referrals`, `GET /api/leaderboard`,
`GET /api/stats`, `GET /health`.

Admin (requiere `is_admin=true`): `GET /api/admin/stats`,
`GET /api/admin/users?search=`, `GET /api/admin/users/{id}`,
`POST /api/admin/users/{id}/ban|unban`, `GET /api/admin/deposits`,
`POST /api/admin/deposits/{id}/approve` (acreditación manual de depósitos),
`GET /api/admin/withdrawals`, `POST /api/admin/withdrawals/{id}/approve|reject|mark-paid`,
`GET /api/admin/reward-pool`, `POST /api/admin/reward-pool/fund`,
`GET|PUT /api/admin/config`, `GET /api/admin/audit`,
`GET /api/admin/fraud-alerts`.

## Tests

```bash
.venv/bin/python -m pytest -q   # 53 tests, SQLite temporal, mocks para BscScan
```

Cubren: registro/login (duplicado, contraseña corta), minería (producción por
tiempo a 20,83 HCK por H/s por hora, tope de capacidad 24 h, sin minería no
produce, collect suma XP y sube de nivel), compra de máquina (402 sin saldo,
descuento y hashrate; niveles bloqueados → 403), catálogo con disponibilidad
y payback (nivel 1 = 20 días), depósito idempotente (409 y un solo crédito;
mock: éxito acredita, monto distinto no acredita, sin claves queda pendiente),
escaneo automático (acredita por remitente mockeado, idempotente, remitente
desconocido no se acredita, inactivo sin configurar, error de API no rompe),
aprobación manual de depósitos por el admin (acredita una sola vez),
retiro con comisión y aprobación (mínimo, 2%, sin fondos → `waiting_funds`,
con fondos → `approved`, `mark-paid` con tx_hash), anti-manipulación de
saldo y rate limiting (11.º login en un minuto → 429).

## Pendiente (lo tiene que pasar AMO)

- `BSCSCAN_API_KEY` (para la acreditación automática; mientras tanto, el admin
  aprueba depósitos a mano tras revisar BscScan).
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` y `SECRET_KEY` de producción.
- Despliegue (no desplegado: solo local + tests). La dirección BSC de depósito
  ya está definida: `0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d`. No hay TRON.
