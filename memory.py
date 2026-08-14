import sqlite3
from typing import List, Dict


class Memory:
    """
    Persistent memory for King Zarry AI.
    Stores conversation history locally in SQLite with WAL mode, thread-safe connections,
    and automated 24-hour retention management.
    """

    def __init__(self, database_path="king_zarry_memory.db", retention_hours=24):
        self.database_path = database_path
        self.retention_hours = retention_hours
        self._create_database()

    def _connect(self):
        # timeout=10 prevents "database is locked" during concurrent async writes
        # check_same_thread=False allows multi-threaded/async access without crashes
        return sqlite3.connect(self.database_path, timeout=10, check_same_thread=False)

    def _create_database(self):
        with self._connect() as conn:
            # Enable Write-Ahead Logging (WAL) and Normal sync for high concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Index user_id and timestamp for fast history filtering and cleanup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_time 
                ON messages(user_id, created_at)
            """)
            conn.commit()

    def cleanup_expired(self):
        """Removes messages older than the specified retention window across all users."""
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE created_at < datetime('now', '-' || ? || ' hours')
                """,
                (self.retention_hours,)
            )
            conn.commit()

    def add_message(self, user_id: str, role: str, content: str):
        if not content or not str(content).strip():
            return

        # Run a quick cleanup of expired logs before writing
        self.cleanup_expired()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (user_id, role, content)
                VALUES (?, ?, ?)
                """,
                (str(user_id), role, str(content).strip())
            )
            conn.commit()

    # Alias for convenience (e.g. self.memory.add(...))
    def add(self, user_id: str, role: str, content: str):
        self.add_message(user_id, role, content)

    def get_messages(self, user_id: str, limit: int = 20, hours: int = None) -> List[Dict]:
        """
        Retrieves recent messages for a user within the retention time window (default: 24h).
        """
        time_window = hours if hours is not None else self.retention_hours

        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT role, content
                FROM messages
                WHERE user_id = ?
                  AND created_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), time_window, limit)
            )
            rows = cursor.fetchall()

        # Reverse to return chronological order (oldest -> newest)
        rows.reverse()

        return [
            {
                "role": role,
                "content": content
            }
            for role, content in rows
        ]

    def get_history(self, user_id: str, limit: int = 20, hours: int = None) -> List[Dict]:
        return self.get_messages(user_id, limit=limit, hours=hours)

    def clear(self, user_id: str):
        """Clears all stored history for a specific user immediately."""
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE user_id = ?
                """,
                (str(user_id),)
            )
            conn.commit()

    def prune_history(self, user_id: str, keep_limit: int = 50):
        """
        Keeps only the most recent N messages for a user to optimize prompt context size.
        """
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM messages
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (str(user_id), str(user_id), keep_limit)
            )
            conn.commit()
