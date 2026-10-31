-- Durable, globally one-use admin image-generation smoke-test claim and audit record.
-- The application role needs only INSERT/UPDATE/SELECT on this table after migration.
CREATE TABLE IF NOT EXISTS zarry_image_smoke_test_lock (
    lock_key TEXT PRIMARY KEY,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'claimed'
        CHECK (status IN ('claimed', 'running', 'succeeded', 'failed')),
    request_id TEXT,
    provider TEXT,
    image_url TEXT,
    error_type TEXT,
    completed_at TIMESTAMPTZ,
    CONSTRAINT zarry_image_smoke_test_lock_key_check
        CHECK (lock_key = 'replicate-one-shot-v1')
);

CREATE INDEX IF NOT EXISTS zarry_image_smoke_test_lock_status_idx
    ON zarry_image_smoke_test_lock (status);
