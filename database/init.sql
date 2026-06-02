-- Connect to ipo_db
\c ipo_db;

-- ─── IPO Master Table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ipo_master (
    ipo_id          SERIAL PRIMARY KEY,
    ipo_name        VARCHAR(255) NOT NULL UNIQUE,
    issue_size      NUMERIC(15, 2),          -- in Crores INR
    offer_price     NUMERIC(10, 2),
    list_price      NUMERIC(10, 2),
    current_price   NUMERIC(10, 2),
    listing_gain    NUMERIC(8, 2),           -- %
    current_gain    NUMERIC(8, 2),           -- %
    open_date       DATE,
    close_date      DATE,
    listing_date    DATE,
    sector          VARCHAR(100),
    exchange        VARCHAR(10) DEFAULT 'NSE',
    status          VARCHAR(20) DEFAULT 'active',  -- active | delisted
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ─── IPO Subscription Table ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ipo_subscription (
    id              SERIAL PRIMARY KEY,
    ipo_id          INT NOT NULL REFERENCES ipo_master(ipo_id) ON DELETE CASCADE,
    qib             NUMERIC(10, 2),          -- Qualified Institutional Buyers (x times)
    hni             NUMERIC(10, 2),          -- High Net-worth Individuals
    rii             NUMERIC(10, 2),          -- Retail Individual Investors
    total_subscription NUMERIC(10, 2),
    recorded_at     TIMESTAMP DEFAULT NOW()
);

-- ─── Pipeline Run Log ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_log (
    log_id          SERIAL PRIMARY KEY,
    run_date        DATE NOT NULL,
    stage           VARCHAR(50) NOT NULL,    -- extract | validate | transform | load
    status          VARCHAR(20) NOT NULL,    -- success | failed | partial
    records_in      INT DEFAULT 0,
    records_out     INT DEFAULT 0,
    error_msg       TEXT,
    duration_sec    NUMERIC(8, 2),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ─── Validation Error Log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS validation_errors (
    error_id        SERIAL PRIMARY KEY,
    run_date        DATE NOT NULL,
    ipo_name        VARCHAR(255),
    error_type      VARCHAR(100),            -- missing_price | duplicate | negative_size etc.
    error_detail    TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ipo_master_open_date   ON ipo_master(open_date);
CREATE INDEX IF NOT EXISTS idx_ipo_master_sector      ON ipo_master(sector);
CREATE INDEX IF NOT EXISTS idx_subscription_ipo_id    ON ipo_subscription(ipo_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_log_run_date  ON pipeline_log(run_date);

-- ─── Grant permissions ───────────────────────────────────────────────────────
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO ipo_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ipo_user;
