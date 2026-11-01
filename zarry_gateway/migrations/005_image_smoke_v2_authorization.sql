-- Preserve the consumed v1 authorization and allow one separately approved v2 claim.
-- The migration runner applies this only as an explicit, checksum-tracked release step.
ALTER TABLE zarry_image_smoke_test_lock
    DROP CONSTRAINT IF EXISTS zarry_image_smoke_test_lock_key_check;

ALTER TABLE zarry_image_smoke_test_lock
    ADD CONSTRAINT zarry_image_smoke_test_lock_key_check
    CHECK (lock_key IN ('replicate-one-shot-v1', 'replicate-one-shot-v2'));
