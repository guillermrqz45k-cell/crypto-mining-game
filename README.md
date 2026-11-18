# CRYPTO MINING GAME — Plataforma de minería virtual de criptomonedas

**Creador por Dark Mous**

Plataforma web profesional de minería virtual, inspirada en Notcoin y Hamster Kombat.
**La minería es virtual.** Las recompensas en HCK son puntos internos del juego y los
retiros en USDT se pagan únicamente desde el fondo de recompensas real del proyecto.
**Sin rentabilidad garantizada. Nunca se simulan depósitos, ganancias ni retiros reales.**

> Estado: código completo en local. **Nada desplegado.** Pendiente la API key de
> BscScan (para la acreditación automática) y las credenciales de producción
> (ver [Pendientes](#pendientes)).

## Estructura

```
crypto-mining-game/
├── backend/            # FastAPI (Python) — API REST, SQLite local / PostgreSQL en producción
│   ├── app/            # main, core (config, db, seguridad, rate limit), models,
│   │                   # services (economía, minería, verificación on-chain,
│   │                   #          escáner de depósitos, misiones),
│   │                   # routers (auth, mining, machines, missions, wallet, withdrawals,
│   │                   #          public, admin)
│   ├── tests/          # pytest — 53 tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md       # detalle de economía, depósitos, retiros y seguridad
├── frontend/           # React 18 + Vite — interfaz en español, móvil primero
│   ├── src/pages/      # Auth, Dashboard (minería), Machines, Missions, Wallet,
│   │                   # Withdrawals, Referrals, Leaderboard, Profile, Admin
│   ├── src/components/ # Layout, ProductionChart (SVG), MiningRoom (sala de minería),
│   │                   # Confetti, WalletConnectButton
│   └── src/api/client.js
├── contracts/          # HCKCOIN.sol (ERC-20 de referencia, NO desplegado) + README
├── db/                 # schema.sql — PostgreSQL, 15 tablas + seeds
├── docker/             # Dockerfile.frontend, nginx.conf
├── docker-compose.yml  # postgres + api + frontend
├── .env.example
└── README.md           # este archivo
```

## Economía (decisiones por defecto — AMO puede cambiarlas)

| Regla | Valor por defecto | Dónde se cambia |
|---|---|---|
| Moneda del juego | **HCKCOIN (HCK)**, puntos internos (no token on-chain) | — |
| Tasa de retiro | **10.000 HCK = 1 USDT** | Admin → Configuración (`hck_per_usdt`) |
| Producción | **20,83 HCK por H/s por hora** | `hck_per_hash_per_hour` |
| Capacidad ("nido") | **24 horas** de producción; lleno = minería parada hasta recolectar | `storage_hours` |
| Recuperación (payback) | Nivel 1 ($10) **20 días**; nivel 2 ~16,7 días; nivel 3 15 días; nivel 4 14 días — a mayor inversión, más rápida la recuperación (recogiendo a diario) | `payback_days` en el catálogo |
| Máquinas | 9 niveles: Nivel 0 Minero Inicial GRATIS/5 H/s · 1 Minero USB 10/10 · 2 Rig GPU 50/60 · 3 ASIC S9 150/200 · 4 Granja ASIC 350/500 · 5 Rig Cuántico 750/1200 · 6 Centro de Datos 1400/2500 · 7 Granja Cuántica 2800/5500 · 8 Núcleo HCK 5000/12000 — **solo 0-4 disponibles; 5-8 bloqueados ("Próximamente")** | Catálogo en DB / admin |
| Mejora (overclock) | +25% hashrate por nivel, máx. 5 niveles; coste 20% del precio base × nivel | — |
| XP / niveles | 1 XP por cada 100 HCK recolectados; nivel n = 1000×n XP; premio al subir = 500×n HCK | — |
| Bono diario | Racha 7 días: 100, 200, 300, 400, 500, 750, 1000 HCK | — |
| Referidos | 500 HCK al referido y 500 HCK al referente (al comprar la primera máquina) | `referral_bonus_hck` |
| Retiro | Mínimo **10 USDT**, comisión **2%** | `min_withdrawal_usdt`, `withdrawal_fee_pct` |

## Minería

La producción se calcula **siempre en el servidor** por tiempo transcurrido con la
minería activa. Sin minería activa no hay producción. El cliente nunca puede inventarse
saldo, hashrate ni recompensas: ningún endpoint acepta esos valores del cliente.

## Depósitos USDT (REAL, sin simulación)

- **UNA SOLA dirección de depósito (BSC/BEP-20):** `0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d`
  (la de AMO, misma que en Dragon Land). No hay dirección TRON.
- El usuario envía USDT a esa dirección y registra su `tx_hash` en la
  billetera. El servidor verifica on-chain con **BscScan API**: la transacción
  debe existir, ir a la dirección de depósito y coincidir en monto y token USDT.
- **Acreditación automática:** el usuario guarda su dirección BSC en su perfil
  y un escáner en segundo plano (cada 5 min) consulta BscScan por las
  transferencias USDT entrantes; si el remitente coincide con un usuario, el
  depósito se acredita solo. Solo activo con `BSCSCAN_API_KEY` configurada.
- **Aprobación manual:** sin la API key, el admin revisa el tx_hash en BscScan
  y aprueba el depósito desde el panel (`POST /api/admin/deposits/{id}/approve`),
  acreditando el saldo con audit log.
- **Idempotencia:** `tx_hash` único en la base de datos. El mismo hash dos veces → 409,
  un solo crédito. Jamás se acredita dos veces la misma transacción.
- **Sin la API key, nada se acredita automáticamente:** sin `BSCSCAN_API_KEY`,
  todo depósito queda en `pending_verification` hasta la aprobación manual.
  Verificado en tests (con mocks).

## Sala de minería (realista)

El Dashboard muestra la **sala de minería**: una unidad ASIC por cada máquina
que el usuario posee de verdad (incluido el Minero Inicial gratis), con
ventiladores girando, LEDs de estado, temperatura, hashrate y consumo por
equipo. Un contador de HCK en vivo sube cada segundo según el hashrate real y
la tasa de producción, y cada 100 HCK se registra un "bloque" visual. También
muestra el saldo del fondo de recompensas.

## Retiros USDT

- Mínimo 10 USDT, comisión 2%, validación de formato de dirección (BSC `0x` + 40 hex;
  TRON base58 que empieza por `T`).
- Estados: `pending` → `approved` / `rejected` / `waiting_funds` → `paid`.
- **Fondo de recompensas:** los retiros solo se aprueban si el fondo tiene saldo
  suficiente. Si el fondo está vacío, el retiro queda en `waiting_funds` — nunca se
  inventa dinero.
- **El pago on-chain es manual:** el admin envía el USDT desde **su propia wallet** y
  marca el retiro como pagado con el `tx_hash`. El sistema **nunca guarda claves
  privadas** de nadie.

## Panel de administración

Usuarios (buscar, banear), depósitos, retiros (aprobar / rechazar / marcar pagado),
fondo de recompensas (saldo + fondeo), configuración de economía, auditoría completa
y alertas de fraude (múltiples cuentas con la misma IP, retiros inusuales, velocidad
de recolección anormal, referidos masivos). Primer admin por variables de entorno
`ADMIN_USERNAME` / `ADMIN_PASSWORD`.

## Seguridad

- Contraseñas con **bcrypt** (passlib se descartó: incompatible con bcrypt ≥ 4.1).
- **JWT** (7 días), saldos y recompensas calculados solo en el servidor, montos con
  `Decimal` (nunca float), rate limiting (100 req/min general, 10/min login/registro,
  5/min depósitos y retiros), registro de IP, auditoría de cada acción financiera y
  de admin. Nunca se almacenan claves privadas.

## Cómo correrlo en local

```bash
# 1. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # rellenar SECRET_KEY y ADMIN_* (el resto vacío está bien)
uvicorn app.main:app --reload --port 8000
# API en http://localhost:8000 — /health, docs en /docs

# 2. Frontend (otra terminal)
cd frontend
npm install
npm run dev                 # http://localhost:5173
npm run build               # build de producción

# 3. Tests del backend
cd backend
python -m pytest -q         # 35 passed
```

### Con Docker (sin Docker no se pudo probar en este entorno)

```bash
cp .env.example .env        # rellenar variables
docker compose up --build
# API http://localhost:8000 — Frontend http://localhost:3000 — Postgres :5432
```

## Despliegue en Railway (cuando AMO lo apruebe)

1. Crear proyecto en Railway con servicio **PostgreSQL** y servicio **API** desde
   `backend/` (o usar el `docker-compose.yml` como referencia).
2. Variables en Railway: `DATABASE_URL` (la de Postgres), `SECRET_KEY`,
   `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DEPOSIT_BSC_ADDRESS`, `DEPOSIT_TRON_ADDRESS`,
   `BSCSCAN_API_KEY`, `TRONGRID_API_KEY`, `CORS_ORIGINS` (URL pública del frontend).
3. Servicio **frontend** desde `frontend/` con `VITE_API_URL` = URL pública de la API
   (Vite la incrusta en el build: definirla **antes** de `npm run build`).
4. Verificar `/health` con `db: postgres` y registrar el webhook/URL pública si aplica.
5. Contratos: `contracts/HCKCOIN.sol` es solo referencia; no se despliega salvo que
   AMO decida lanzar el token on-chain (ver `contracts/README.md`).

## Verificado

- **Backend:** `pytest` → **53 passed, 1 warning** (solo deprecations sin efecto).
  Cubre registro/login, minería y cálculo de recompensas (20,83 HCK por H/s por
  hora, tope 24 h), compra de máquina (niveles bloqueados → 403), depósito
  idempotente (sin doble crédito), escaneo automático por remitente (mockeado,
  idempotente), aprobación manual de depósitos por el admin, retiro con comisión
  y aprobación, anti-manipulación de saldo y rate limiting.
- **Smoke test en vivo (uvicorn + curl, SQLite):** `/health` ok; registro/login/`/api/me`;
  catálogo de 9 niveles (0-4 disponibles, 5-8 bloqueados, payback nivel 1 = 20 días);
  bono diario día 1 = 100 HCK; depósito sin claves →
  `pending_verification` (`sin BSCSCAN_API_KEY`), saldo 0; mismo `tx_hash` → 409;
  iniciar minería sin máquinas → 422; admin login y `/api/admin/stats` ok.
- **Frontend:** `npm run build` → éxito (47 módulos).
- **Contrato:** `npx solc --bin --abi HCKCOIN.sol` → exit 0, sin errores ni warnings
  (solc 0.8.38, bytecode 9.698 bytes).
- **Compose:** YAML válido (postgres + api + frontend). `docker compose up` **no** se
  pudo probar: no hay Docker en este entorno.

## Pendientes

- **AMO debe pasar:** `BSCSCAN_API_KEY` (cuenta BscScan creada como
  guillermrqz45k, pendiente de verificación de correo y de crear la key),
  `SECRET_KEY` y credenciales admin de producción.
- La verificación on-chain real contra BscScan con datos reales no se ha
  probado en vivo (implementada y testeada con mocks); necesita la API key.
- `docker compose up` pendiente de probar en un entorno con Docker.
- WalletConnect: falta el Project ID (gratis en https://cloud.walletconnect.com) y
  la variable `VITE_WALLETCONNECT_PROJECT_ID`; el botón hoy conecta vía la wallet
  del navegador y el flujo con modal QR está documentado en
  `frontend/src/components/WalletConnectButton.jsx`.
- Despliegue a Railway: **bloqueado** — el plan Trial está lleno (2 proyectos:
  Robin Dark y Rifa) y AMO no quiso pasar al plan Hobby ("ya quedó así").
  El repo con el código completo está en
  https://github.com/guillermrqz45k-cell/crypto-mining-game.
- Dirección de depósito BSC ya definida: `0x71457a5a883ae25b21fdf2cc8784201d56e8bc2d`.
  No hay TRON.
