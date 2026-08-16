CREATE TABLE IF NOT EXISTS conversation_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL CHECK (platform IN ('telegram', 'discord')),
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index to quickly query history for a specific user on a specific platform
CREATE INDEX IF NOT EXISTS idx_conversation_user 
ON conversation_memory (platform, user_id, timestamp);

CREATE TABLE IF NOT EXISTS subscriptions (
    platform TEXT NOT NULL CHECK (platform IN ('telegram', 'discord')),
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inactive' CHECK (status IN ('active', 'inactive', 'trial')),
    subscription_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform, user_id)
);
