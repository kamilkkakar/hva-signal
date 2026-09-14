CREATE TABLE IF NOT EXISTS hva_acquisitions (
    scope text NOT NULL,
    fingerprint text NOT NULL,
    generation integer NOT NULL CHECK (generation > 0),
    reservation_id uuid NOT NULL UNIQUE,
    reserved_day date NOT NULL,
    request_payload jsonb NOT NULL,
    state text NOT NULL CHECK (state IN (
        'SUBMITTING', 'ACTIVITY_ID_PERSISTED', 'RESULT_RECEIVED',
        'UNKNOWN_VENDOR_STATE', 'FAILED_POST_SUBMIT'
    )),
    activity_id text,
    result_payload jsonb,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (scope, fingerprint, generation),
    CHECK ((state IN ('SUBMITTING', 'UNKNOWN_VENDOR_STATE')) = (activity_id IS NULL)),
    CHECK ((state = 'RESULT_RECEIVED') = (result_payload IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS hva_acquisitions_allowance
    ON hva_acquisitions (scope, reserved_day);
