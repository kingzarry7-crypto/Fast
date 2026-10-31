-- ZARRY general assistant memory is web-account scoped and opt-in only.
CREATE TABLE IF NOT EXISTS zarry_general_memory_preferences (
    user_id UUID PRIMARY KEY REFERENCES web_users(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    consented_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((enabled = FALSE) OR (consented_at IS NOT NULL AND revoked_at IS NULL))
);

CREATE TABLE IF NOT EXISTS zarry_general_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL,
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL CHECK (char_length(content) BETWEEN 1 AND 12000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_zarry_general_messages_history
    ON zarry_general_messages(user_id, conversation_id, id DESC);
