import sqlite3
import threading
from typing import List, Dict, Optional

class UserMemoryManager:
    def __init__(self, db_path: str = "king_zarry_memory.db", schema_path: str = "schema.sql"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db(schema_path)

    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self, schema_path: str):
        with self.lock:
            with self._get_connection() as conn:
                try:
                    with open(schema_path, "r") as f:
                        conn.executescript(f.read())
                    conn.commit()
                except Exception as e:
                    print(f"Database init warning: {e}")

    def set_user_name(self, user_id: str, platform: str, name: str):
        """Saves or updates what the user asks to be called."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (user_id, platform, preferred_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET preferred_name = excluded.preferred_name
                    """,
                    (str(user_id), platform, name)
                )
                conn.commit()

    def get_user_name(self, user_id: str) -> Optional[str]:
        """Retrieves user's preferred name if set."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT preferred_name FROM users WHERE user_id = ?", (str(user_id),))
                row = cursor.fetchone()
                return row[0] if row else None

    def add_chat(self, user_id: str, platform: str, role: str, content: str):
        """Logs every incoming prompt and assistant response persistently."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversation_memory (user_id, platform, role, content) VALUES (?, ?, ?, ?)",
                    (str(user_id), platform, role, content)
                )
                conn.commit()

    def get_user_history(self, user_id: str, platform: str, limit: int = 20) -> List[Dict[str, str]]:
        """Retrieves persistent chat context for model generation."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT role, content FROM conversation_memory
                    WHERE user_id = ? AND platform = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (str(user_id), platform, limit)
                )
                rows = cursor.fetchall()
                return [{"role": row[0], "content": row[1]} for row in reversed(rows)]
