-- KING ZARRY AI - WEB FRONTEND DATABASE SCHEMA
-- WEB ONLY - Completely independent from Telegram databases
-- Database: Neon PostgreSQL
-- This file contains ONLY web/frontend user data
-- DO NOT migrate Telegram data (king_zarry_memory.db, etc.)

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. WEB USERS - Authentication and core account data
-- ============================================================
CREATE TABLE IF NOT EXISTS web_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Never store plaintext, use bcrypt/argon2
    username VARCHAR(100) UNIQUE,
    display_name VARCHAR(255),
    account_status VARCHAR(50) NOT NULL DEFAULT 'active'
        CHECK (account_status IN ('active', 'inactive', 'suspended', 'pending')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_web_users_email ON web_users(email);
CREATE INDEX IF NOT EXISTS idx_web_users_username ON web_users(username);
CREATE INDEX IF NOT EXISTS idx_web_users_status ON web_users(account_status);

-- ============================================================
-- 2. WEB SESSIONS - Secure web authentication sessions
-- ============================================================
-- Stores only a SHA-256 hash of the session token.
-- The raw session token is never stored in the database.
-- Sessions can expire or be explicitly revoked.
CREATE TABLE IF NOT EXISTS web_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_web_sessions_user_id ON web_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_web_sessions_expires_at ON web_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_web_sessions_user_active ON web_sessions(user_id, expires_at, revoked_at);
CREATE INDEX IF NOT EXISTS idx_web_sessions_token_hash ON web_sessions(token_hash);

-- ============================================================
-- 3. USER PROFILES - Extended web user information
-- ============================================================
CREATE TABLE IF NOT EXISTS web_user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES web_users(id) ON DELETE CASCADE,
    display_name VARCHAR(255),
    bio TEXT,
    avatar_url TEXT,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_user_profiles_user_id ON web_user_profiles(user_id);

-- ============================================================
-- 4. AI MEMORY - Web-only AI memory (separate from Telegram)
-- ============================================================
CREATE TABLE IF NOT EXISTS web_ai_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    memory_type VARCHAR(100) NOT NULL DEFAULT 'conversation'
        CHECK (memory_type IN ('conversation', 'fact', 'preference', 'context')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_ai_memories_user_id ON web_ai_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_web_ai_memories_created_at ON web_ai_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_ai_memories_user_created ON web_ai_memories(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_ai_memories_type ON web_ai_memories(memory_type);

-- ============================================================
-- 5. USER SETTINGS - Web-specific settings (flexible JSONB)
-- ============================================================
CREATE TABLE IF NOT EXISTS web_user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES web_users(id) ON DELETE CASCADE,
    ai_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    trading_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    notification_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    interface_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_user_settings_user_id ON web_user_settings(user_id);

-- ============================================================
-- 6. WEB SUBSCRIPTIONS - Separate from Telegram Stars
-- ============================================================
CREATE TABLE IF NOT EXISTS web_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    plan VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'inactive'
        CHECK (status IN ('active', 'inactive', 'canceled', 'expired', 'trialing', 'past_due')),
    start_date TIMESTAMPTZ,
    expiration_date TIMESTAMPTZ,
    payment_provider VARCHAR(100),
    provider_reference_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_subscriptions_user_id ON web_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_web_subscriptions_status ON web_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_web_subscriptions_plan ON web_subscriptions(plan);
CREATE INDEX IF NOT EXISTS idx_web_subscriptions_user_status ON web_subscriptions(user_id, status);

-- ============================================================
-- 7. WEB PAYMENTS - Future web payments
-- ============================================================
CREATE TABLE IF NOT EXISTS web_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,
    provider_transaction_id VARCHAR(255),
    provider_reference_id VARCHAR(255),
    plan VARCHAR(100),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'failed', 'refunded', 'canceled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_payments_user_id ON web_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_web_payments_status ON web_payments(status);
CREATE INDEX IF NOT EXISTS idx_web_payments_provider ON web_payments(provider);
CREATE INDEX IF NOT EXISTS idx_web_payments_transaction_id ON web_payments(provider_transaction_id);

-- ============================================================
-- 8. AI CONVERSATIONS - Web chat conversations
-- ============================================================
CREATE TABLE IF NOT EXISTS web_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_conversations_user_id ON web_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_web_conversations_updated_at ON web_conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_conversations_user_updated ON web_conversations(user_id, updated_at DESC);

-- ============================================================
-- 9. CONVERSATION MESSAGES - Messages in conversations
-- ============================================================
CREATE TABLE IF NOT EXISTS web_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES web_conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_messages_conversation_id ON web_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_web_messages_created_at ON web_messages(created_at ASC);
CREATE INDEX IF NOT EXISTS idx_web_messages_conversation_created ON web_messages(conversation_id, created_at ASC);

-- ============================================================
-- 10. WEB PERMISSIONS - Web-only permission infrastructure
-- ============================================================
CREATE TABLE IF NOT EXISTS web_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    service VARCHAR(100) NOT NULL,
    permission_level VARCHAR(50) NOT NULL
        CHECK (permission_level IN ('denied', 'read_once', 'read_session', 'read_only', 'draft_only', 'action_with_approval', 'automatic_action')),
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_operations JSONB NOT NULL DEFAULT '[]'::jsonb,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, service)
);

CREATE INDEX IF NOT EXISTS idx_web_permissions_user_id ON web_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_web_permissions_service ON web_permissions(service);
CREATE INDEX IF NOT EXISTS idx_web_permissions_user_service ON web_permissions(user_id, service);
CREATE INDEX IF NOT EXISTS idx_web_permissions_expires_at ON web_permissions(expires_at);

-- ============================================================
-- 11. WEB APPROVALS - Web-only exact one-time approvals
-- ============================================================
CREATE TABLE IF NOT EXISTS web_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES web_users(id) ON DELETE CASCADE,
    service VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    target TEXT NOT NULL,
    exact_content TEXT NOT NULL,
    amount VARCHAR(100),
    action_fingerprint VARCHAR(128) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'executed', 'expired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes')
);

CREATE INDEX IF NOT EXISTS idx_web_approvals_user_id ON web_approvals(user_id);
CREATE INDEX IF NOT EXISTS idx_web_approvals_status ON web_approvals(status);
CREATE INDEX IF NOT EXISTS idx_web_approvals_user_status ON web_approvals(user_id, status);
CREATE INDEX IF NOT EXISTS idx_web_approvals_fingerprint ON web_approvals(action_fingerprint);
CREATE INDEX IF NOT EXISTS idx_web_approvals_expires_at ON web_approvals(expires_at);

-- ============================================================
-- 12. WEB AUDIT LOGS - Web-only audit trail (never stores secrets)
-- ============================================================
CREATE TABLE IF NOT EXISTS web_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES web_users(id) ON DELETE SET NULL,
    event VARCHAR(255) NOT NULL,
    service VARCHAR(100),
    tool_name VARCHAR(255),
    approval_id UUID REFERENCES web_approvals(id) ON DELETE SET NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_audit_logs_user_id ON web_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_web_audit_logs_event ON web_audit_logs(event);
CREATE INDEX IF NOT EXISTS idx_web_audit_logs_created_at ON web_audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_audit_logs_user_created ON web_audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_web_audit_logs_approval_id ON web_audit_logs(approval_id);

-- ============================================================
-- TRIGGERS - Auto-update updated_at timestamps
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_web_users_updated_at ON web_users;
CREATE TRIGGER update_web_users_updated_at
    BEFORE UPDATE ON web_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_web_user_profiles_updated_at ON web_user_profiles;
CREATE TRIGGER update_web_user_profiles_updated_at
    BEFORE UPDATE ON web_user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_web_user_settings_updated_at ON web_user_settings;
CREATE TRIGGER update_web_user_settings_updated_at
    BEFORE UPDATE ON web_user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_web_subscriptions_updated_at ON web_subscriptions;
CREATE TRIGGER update_web_subscriptions_updated_at
    BEFORE UPDATE ON web_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_web_payments_updated_at ON web_payments;
CREATE TRIGGER update_web_payments_updated_at
    BEFORE UPDATE ON web_payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_web_conversations_updated_at ON web_conversations;
CREATE TRIGGER update_web_conversations_updated_at
    BEFORE UPDATE ON web_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_web_permissions_updated_at ON web_permissions;
CREATE TRIGGER update_web_permissions_updated_at
    BEFORE UPDATE ON web_permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- COMMENTS - Documentation
-- ============================================================
COMMENT ON TABLE web_users IS 'Web frontend authentication - separate from Telegram users';
COMMENT ON TABLE web_sessions IS 'Secure web authentication sessions - stores hashed session tokens only - raw tokens never stored - separate from Telegram';
COMMENT ON TABLE web_user_profiles IS 'Extended profile data for web users';
COMMENT ON TABLE web_ai_memories IS 'Web-only AI memory - DO NOT mix with king_zarry_memory.db';
COMMENT ON TABLE web_user_settings IS 'Web-specific settings (AI, trading, notifications, UI)';
COMMENT ON TABLE web_subscriptions IS 'Web subscriptions - separate from Telegram Stars';
COMMENT ON TABLE web_payments IS 'Web payments - future payment provider integration';
COMMENT ON TABLE web_conversations IS 'Web AI chat conversations';
COMMENT ON TABLE web_messages IS 'Messages within web conversations';
COMMENT ON TABLE web_permissions IS 'Web-only permission infrastructure - separate from Telegram - stores service permission levels with scopes and allowed_operations - never stores passwords, API keys, or secrets';
COMMENT ON TABLE web_approvals IS 'Web-only exact one-time approvals - separate from Telegram - represents a single approved action with SHA-256 fingerprint - an approval must never become a general permission - never stores secrets';
COMMENT ON TABLE web_audit_logs IS 'Web-only audit trail - separate from Telegram - security logging for permission and approval events - must NEVER store passwords, API keys, access tokens, refresh tokens, secrets, or authentication credentials';
