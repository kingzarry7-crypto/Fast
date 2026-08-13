import sqlite3
from typing import List, Dict


class Memory:
    """
    Simple persistent memory for King Zarry AI.
    Stores conversation history locally in SQLite.
    """

    def __init__(self, database_path="king_zarry_memory.db"):
        self.database_path = database_path
        self._create_database()

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _create_database(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str
    ):
        if not content:
            return

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages
                (user_id, role, content)
                VALUES (?, ?, ?)
                """,
                (
                    str(user_id),
                    role,
                    content
                )
            )
            conn.commit()

    def get_messages(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:

        with self._connect() as conn:

            cursor = conn.execute(
                """
                SELECT role, content
                FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    str(user_id),
                    limit
                )
            )

            rows = cursor.fetchall()

        rows.reverse()

        return [
            {
                "role": role,
                "content": content
            }
            for role, content in rows
        ]

    def clear(self, user_id: str):
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE user_id = ?
                """,
                (str(user_id),)
            )
            conn.commit()

    def get_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:

        return self.get_messages(
            user_id,
            limit
        )
