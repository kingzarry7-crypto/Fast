-- Safe, allowlisted diagnostics for the one-time image smoke test.
ALTER TABLE zarry_image_smoke_test_lock
    ADD COLUMN IF NOT EXISTS failure_stage TEXT,
    ADD COLUMN IF NOT EXISTS http_status_code INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'zarry_image_smoke_failure_stage_check'
    ) THEN
        ALTER TABLE zarry_image_smoke_test_lock
            ADD CONSTRAINT zarry_image_smoke_failure_stage_check
            CHECK (
                failure_stage IS NULL OR failure_stage IN (
                    'replicate_submit', 'replicate_poll',
                    'provider_image_download', 'provider_generate_other',
                    'image_validation', 'r2_public_retrieval', 'storage_save'
                )
            );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'zarry_image_smoke_http_status_check'
    ) THEN
        ALTER TABLE zarry_image_smoke_test_lock
            ADD CONSTRAINT zarry_image_smoke_http_status_check
            CHECK (http_status_code IS NULL OR http_status_code BETWEEN 100 AND 599);
    END IF;
END $$;
