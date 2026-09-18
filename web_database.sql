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
-- 2. USER PROFILES - Extended web user information
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
-- 3. AI MEMORY - Web-only AI memory (separate from Telegram)
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
-- 4. USER SETTINGS - Web-specific settings (flexible JSONB)
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
-- 5. WEB SUBSCRIPTIONS - Separate from Telegram Stars
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
-- 6. WEB PAYMENTS - Future web payments
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
-- 7. AI CONVERSATIONS - Web chat conversations
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
-- 8. CONVERSATION MESSAGES - Messages in conversations
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
-- TRIGGERS - Auto-update updated_at timestamps
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at
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

-- ============================================================
-- COMMENTS - Documentation
-- ============================================================
COMMENT ON TABLE web_users IS 'Web frontend authentication - separate from Telegram users';
COMMENT ON TABLE web_user_profiles IS 'Extended profile data for web users';
COMMENT ON TABLE web_ai_memories IS 'Web-only AI memory - DO NOT mix with king_zarry_memory.db';
COMMENT ON TABLE web_user_settings IS 'Web-specific settings (AI, trading, notifications, UI)';
COMMENT ON TABLE web_subscriptions IS 'Web subscriptions - separate from Telegram Stars';
COMMENT ON TABLE web_payments IS 'Web payments - future payment provider integration';
COMMENT ON TABLE web_conversations IS 'Web AI chat conversations';
COMMENT ON TABLE web_messages IS 'Messages within web conversations';
