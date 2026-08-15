CREATE TABLE IF NOT EXISTS conversation_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,         -- 'telegram' or 'discord'
    user_id TEXT NOT NULL,           -- Telegram ID or Discord User ID
    role TEXT NOT NULL,              -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    platform TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT DEFAULT 'inactive',  -- 'active', 'inactive', 'trial'
    subscription_date DATETIME,
    PRIMARY KEY (platform, user_id)
);
