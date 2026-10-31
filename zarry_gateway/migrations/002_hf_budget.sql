-- Atomic, application-side paid Hugging Face inference budget.
-- USD amounts are stored as integer microdollars to avoid floating point drift.
CREATE TABLE IF NOT EXISTS zarry_hf_monthly_budget (
    billing_month DATE PRIMARY KEY,
    limit_micro_usd BIGINT NOT NULL CHECK (limit_micro_usd > 0),
    reserved_micro_usd BIGINT NOT NULL DEFAULT 0 CHECK (reserved_micro_usd >= 0),
    spent_micro_usd BIGINT NOT NULL DEFAULT 0 CHECK (spent_micro_usd >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (reserved_micro_usd + spent_micro_usd <= limit_micro_usd)
);

CREATE TABLE IF NOT EXISTS zarry_hf_budget_reservations (
    request_id UUID PRIMARY KEY,
    billing_month DATE NOT NULL REFERENCES zarry_hf_monthly_budget(billing_month),
    reserved_micro_usd BIGINT NOT NULL CHECK (reserved_micro_usd > 0),
    settled_micro_usd BIGINT,
    status VARCHAR(16) NOT NULL CHECK (status IN ('reserved', 'settled', 'released')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (settled_micro_usd IS NULL OR settled_micro_usd >= 0)
);
CREATE INDEX IF NOT EXISTS idx_zarry_hf_budget_reservations_month
    ON zarry_hf_budget_reservations(billing_month, status);
