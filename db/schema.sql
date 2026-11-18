-- ============================================================================
-- CRYPTO MINING GAME — Esquema PostgreSQL
-- ============================================================================
-- Economía del juego OFF-CHAIN: HCKCOIN (HCK) son puntos internos en la
-- base de datos. 10.000 HCK = 1 USDT al retirar (config.hck_per_usdt).
-- Los retiros USDT los paga el admin manualmente desde su propia wallet:
-- el sistema NUNCA guarda claves privadas.
--
-- Aplicar con:
--   psql "$DATABASE_URL" -f db/schema.sql
-- o dejar que docker-compose levante Postgres con este archivo montado en
-- /docker-entrypoint-initdb.d/ (solo la primera vez, con el volumen vacío).
-- Compatible con PostgreSQL 16.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
    is_banned     BOOLEAN      NOT NULL DEFAULT FALSE,
    level         INTEGER      NOT NULL DEFAULT 1 CHECK (level >= 1),
    xp            INTEGER      NOT NULL DEFAULT 0 CHECK (xp >= 0),
    usdt_balance  NUMERIC(18, 6) NOT NULL DEFAULT 0 CHECK (usdt_balance >= 0),
    hck_balance   NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (hck_balance >= 0),
    referral_code VARCHAR(20)  NOT NULL UNIQUE,
    referred_by   INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    ip_address    INET,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- machines_catalog — catálogo de máquinas comprables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS machines_catalog (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(50)  NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    price_usdt  NUMERIC(18, 6) NOT NULL CHECK (price_usdt >= 0),  -- 0 = nivel 0 gratis
    hashrate    INTEGER      NOT NULL CHECK (hashrate > 0),  -- H/s
    description TEXT         NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- user_machines — máquinas que posee cada usuario
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_machines (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    machine_id      INTEGER NOT NULL REFERENCES machines_catalog(id) ON DELETE RESTRICT,
    overclock_level INTEGER NOT NULL DEFAULT 0 CHECK (overclock_level >= 0),
    purchased_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- mining_sessions — sesiones de minería (inicio / fin / HCK recolectado)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mining_sessions (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stopped_at   TIMESTAMPTZ,
    collected_hck NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (collected_hck >= 0),
    CHECK (stopped_at IS NULL OR stopped_at >= started_at)
);

-- ---------------------------------------------------------------------------
-- transactions — historial contable de movimientos HCK/USDT
--   type: deposit | withdrawal | purchase | upgrade | reward | bonus
--         | mission | referral | level_up
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(20) NOT NULL CHECK (type IN (
                    'deposit', 'withdrawal', 'purchase', 'upgrade',
                    'reward', 'bonus', 'mission', 'referral', 'level_up'
                )),
    amount_hck  NUMERIC(20, 2) NOT NULL DEFAULT 0,
    amount_usdt NUMERIC(18, 6) NOT NULL DEFAULT 0,
    status      VARCHAR(20) NOT NULL DEFAULT 'completed' CHECK (status IN (
                    'pending', 'completed', 'failed', 'cancelled'
                )),
    reference   VARCHAR(100),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- deposits — depósitos USDT por BSC (BEP-20) / TRON (TRC-20), verificados
-- por el admin contra el tx_hash on-chain.
--   status: pending_verification | verified | rejected
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS deposits (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tx_hash    VARCHAR(100) NOT NULL UNIQUE,
    network    VARCHAR(10) NOT NULL CHECK (network IN ('BSC', 'TRON')),
    amount_usdt NUMERIC(18, 6) NOT NULL CHECK (amount_usdt > 0),
    status     VARCHAR(25) NOT NULL DEFAULT 'pending_verification' CHECK (status IN (
                   'pending_verification', 'verified', 'rejected'
               )),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- withdrawals — retiros USDT. El admin paga manualmente desde su wallet
-- y registra el hash on-chain en admin_tx_hash.
--   status: pending | approved | rejected | paid | waiting_funds
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS withdrawals (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_usdt   NUMERIC(18, 6) NOT NULL CHECK (amount_usdt > 0),
    fee_usdt      NUMERIC(18, 6) NOT NULL DEFAULT 0 CHECK (fee_usdt >= 0),
    net_usdt      NUMERIC(18, 6) NOT NULL CHECK (net_usdt >= 0),
    address       VARCHAR(100) NOT NULL,
    network       VARCHAR(10) NOT NULL CHECK (network IN ('BSC', 'TRON')),
    status        VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
                      'pending', 'approved', 'rejected', 'paid', 'waiting_funds'
                  )),
    admin_tx_hash VARCHAR(100),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at    TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- missions — misiones (diarias y de progreso)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS missions (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(50)  NOT NULL UNIQUE,
    title       VARCHAR(150) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    reward_hck  NUMERIC(20, 2) NOT NULL DEFAULT 0 CHECK (reward_hck >= 0),
    target      INTEGER      NOT NULL DEFAULT 1 CHECK (target > 0),
    type        VARCHAR(20)  NOT NULL DEFAULT 'daily' CHECK (type IN ('daily', 'progress', 'special'))
);

-- ---------------------------------------------------------------------------
-- user_missions — progreso de cada usuario en cada misión
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_missions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mission_id INTEGER NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    progress   INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0),
    completed  BOOLEAN NOT NULL DEFAULT FALSE,
    claimed    BOOLEAN NOT NULL DEFAULT FALSE,
    date       DATE    NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE (user_id, mission_id, date)
);

-- ---------------------------------------------------------------------------
-- daily_bonuses — racha de bono diario
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_bonuses (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    streak          INTEGER NOT NULL DEFAULT 0 CHECK (streak >= 0),
    last_claim_date DATE,
    UNIQUE (user_id)
);

-- ---------------------------------------------------------------------------
-- referrals — referidos y bono pagado
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referrals (
    id          SERIAL PRIMARY KEY,
    referrer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bonus_paid  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (referred_id),
    CHECK (referrer_id <> referred_id)
);

-- ---------------------------------------------------------------------------
-- reward_pool — fondo de recompensas real (una sola fila, id = 1).
-- balance_usdt: disponible para pagar retiros. El admin lo recarga
-- manualmente; total_funded / total_paid son acumulados históricos.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reward_pool (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    balance_usdt NUMERIC(18, 6) NOT NULL DEFAULT 0 CHECK (balance_usdt >= 0),
    total_funded NUMERIC(18, 6) NOT NULL DEFAULT 0 CHECK (total_funded >= 0),
    total_paid   NUMERIC(18, 6) NOT NULL DEFAULT 0 CHECK (total_paid >= 0)
);

-- ---------------------------------------------------------------------------
-- config — parámetros del juego (clave/valor, editables por el admin)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config (
    key         VARCHAR(50) PRIMARY KEY,
    value       VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- audit_logs — registro de acciones (admin y usuarios)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     VARCHAR(100) NOT NULL,
    details    JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- fraud_alerts — alertas anti-fraude (multi-cuenta, VPN, abuso, etc.)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    type        VARCHAR(50) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    severity    VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Índices (tx_hash, user_id, created_at y claves de búsqueda habituales)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_deposits_tx_hash      ON deposits (tx_hash);
CREATE INDEX IF NOT EXISTS idx_deposits_user_id      ON deposits (user_id);
CREATE INDEX IF NOT EXISTS idx_deposits_created_at   ON deposits (created_at);
CREATE INDEX IF NOT EXISTS idx_deposits_status       ON deposits (status);

CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id    ON withdrawals (user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawals_created_at ON withdrawals (created_at);
CREATE INDEX IF NOT EXISTS idx_withdrawals_status     ON withdrawals (status);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id    ON transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions (created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_type       ON transactions (type);

CREATE INDEX IF NOT EXISTS idx_user_machines_user_id ON user_machines (user_id);
CREATE INDEX IF NOT EXISTS idx_mining_sessions_user_id    ON mining_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_mining_sessions_started_at ON mining_sessions (started_at);
CREATE INDEX IF NOT EXISTS idx_user_missions_user_id ON user_missions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_missions_date    ON user_missions (date);
CREATE INDEX IF NOT EXISTS idx_daily_bonuses_user_id ON daily_bonuses (user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals (referrer_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id    ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_user_id    ON fraud_alerts (user_id);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_created_at ON fraud_alerts (created_at);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_resolved   ON fraud_alerts (resolved);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users (referral_code);

-- ============================================================================
-- Datos iniciales
-- ============================================================================

-- Catálogo de 9 niveles (nivel 0 gratis: Minero Inicial al registrarse)
INSERT INTO machines_catalog (key, name, price_usdt, hashrate, description) VALUES
    ('level_0', 'Minero Inicial',   0,     5,     'Minero inicial gratis: todo usuario lo recibe al registrarse.'),
    ('level_1', 'Minero USB',       10,    10,    'Minería básica por USB. Ideal para empezar.'),
    ('level_2', 'Rig GPU',          50,    60,    'Rig de GPUs para minar con más potencia.'),
    ('level_3', 'ASIC S9',          150,   200,   'Minero ASIC de alto rendimiento.'),
    ('level_4', 'Granja ASIC',      350,   500,   'Granja de ASICs: potencia seria para mineros avanzados.'),
    ('level_5', 'Rig Cuántico',     750,   1200,  'Potencia cuántica para granjas grandes.'),
    ('level_6', 'Centro de Datos',  1400,  2500,  'Un centro de datos completo a tu servicio.'),
    ('level_7', 'Granja Cuántica',  2800,  5500,  'Granja cuántica de élite. Producción masiva.'),
    ('level_8', 'Núcleo HCK',      5000,  12000, 'El núcleo definitivo del juego. Potencia máxima.')
ON CONFLICT (key) DO NOTHING;

-- Misiones diarias
INSERT INTO missions (key, title, description, reward_hck, target, type) VALUES
    ('daily_login',    'Conexión diaria',   'Entra al juego hoy.', 100, 1, 'daily'),
    ('daily_mine',     'Minero del día',    'Mina durante 1 hora hoy.', 250, 1, 'daily'),
    ('daily_collect',  'Recolecta tu botín','Recolecta HCK de tu sesión de minería.', 150, 1, 'daily'),
    ('daily_referral', 'Invita a un amigo','Consigue que un amigo se registre con tu código.', 500, 1, 'daily'),
    ('daily_machines', 'Granja en marcha',  'Ten al menos 2 máquinas minando.', 300, 2, 'daily')
ON CONFLICT (key) DO NOTHING;

-- Fondo de recompensas (una sola fila, id = 1; empieza vacío, el admin lo fondea)
INSERT INTO reward_pool (id, balance_usdt, total_funded, total_paid)
VALUES (1, 0, 0, 0)
ON CONFLICT (id) DO NOTHING;

-- Configuración por defecto
INSERT INTO config (key, value, description) VALUES
    ('hck_per_usdt',           '10000', 'HCK que vale 1 USDT al retirar (10.000 HCK = 1 USDT).'),
    ('withdrawal_fee_pct',     '2',     'Comisión de retiro en % sobre el importe en USDT.'),
    ('min_withdrawal_usdt',    '10',    'Retiro mínimo en USDT.'),
    ('hck_per_hash_per_hour',  '10',    'HCK generados por cada H/s por cada hora de minería.'),
    ('referral_bonus_hck',     '500',   'HCK de bono por cada referido que se registra.'),
    ('storage_hours',          '8',     'Horas de producción que caben en el almacén antes de recolectar.')
ON CONFLICT (key) DO NOTHING;

COMMIT;

-- ============================================================================
-- NOTA SQLite (fallback local del backend):
-- Este esquema es PostgreSQL (SERIAL, TIMESTAMPTZ, INET, JSONB, NUMERIC,
-- ON CONFLICT). El backend usa SQLAlchemy y crea las tablas en SQLite con
-- sus propios modelos cuando DATABASE_URL apunta a sqlite; este archivo es
-- la fuente de verdad para producción (PostgreSQL).
-- ============================================================================
