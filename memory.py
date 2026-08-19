import sqlite3
import threading
from datetime import datetime, timezone


class Memory:
    """
    Persistent SQLite memory for King Zarry AI.

    Database:
        king_zarry_memory.db

    Compatible with:
        Memory(DATABASE_PATH)
        memory.clear_history(user_id)
        AIEngine(memory)
    """

    def __init__(self, database_path="king_zarry_memory.db"):
        self.database_path = database_path
        self.lock = threading.RLock()

        self._init_database()

        print(
            f"🧠 Persistent Memory initialized: "
            f"{self.database_path}"
        )

    # ======================================================
    # DATABASE
    # ======================================================

    def _connect(self):
        conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False
        )

        conn.row_factory = sqlite3.Row

        return conn

    def _init_database(self):
        with self.lock:
            conn = self._connect()

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_ai_memory_user
                ON ai_memory(user_id)
                """
            )

            conn.commit()
            conn.close()

    # ======================================================
    # ADD MEMORY
    # ======================================================

    def add_message(
        self,
        user_id,
        role,
        content
    ):
        if not content:
            return

        with self.lock:
            conn = self._connect()

            conn.execute(
                """
                INSERT INTO ai_memory
                (user_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    str(role),
                    str(content),
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                )
            )

            conn.commit()
            conn.close()

    # Common aliases used by AI engines

    def save_message(
        self,
        user_id,
        role,
        content
    ):
        self.add_message(
            user_id,
            role,
            content
        )

    def remember(
        self,
        user_id,
        role,
        content
    ):
        self.add_message(
            user_id,
            role,
            content
        )

    # ======================================================
    # GET MEMORY
    # ======================================================

    def get_history(
        self,
        user_id,
        limit=20
    ):
        with self.lock:
            conn = self._connect()

            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM ai_memory
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    str(user_id),
                    int(limit),
                )
            ).fetchall()

            conn.close()

        rows = list(reversed(rows))

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_messages(
        self,
        user_id,
        limit=20
    ):
        return self.get_history(
            user_id,
            limit
        )

    def load_history(
        self,
        user_id,
        limit=20
    ):
        return self.get_history(
            user_id,
            limit
        )

    def get_context(
        self,
        user_id,
        limit=20
    ):
        return self.get_history(
            user_id,
            limit
        )

    # ======================================================
    # CLEAR MEMORY
    # ======================================================

    def clear_history(self, user_id):
        with self.lock:
            conn = self._connect()

            conn.execute(
                """
                DELETE FROM ai_memory
                WHERE user_id = ?
                """,
                (str(user_id),)
            )

            conn.commit()
            conn.close()

        print(
            f"🧹 Memory cleared for user "
            f"{user_id}"
        )

    def clear_memory(self, user_id):
        self.clear_history(user_id)

    def forget(self, user_id):
        self.clear_history(user_id)

    # ======================================================
    # DELETE ALL
    # ======================================================

    def clear_all(self):
        with self.lock:
            conn = self._connect()

            conn.execute(
                "DELETE FROM ai_memory"
            )

            conn.commit()
            conn.close()

        print("🧹 ALL AI MEMORY CLEARED")

    # ======================================================
    # MEMORY COUNT
    # ======================================================

    def count(self, user_id=None):
        with self.lock:
            conn = self._connect()

            if user_id is None:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM ai_memory
                    """
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM ai_memory
                    WHERE user_id = ?
                    """,
                    (str(user_id),)
                ).fetchone()

            conn.close()

        return int(row["count"])

    # ======================================================
    # CONVERSATION FORMAT
    # ======================================================

    def get_chat_messages(
        self,
        user_id,
        limit=20
    ):
        """
        Returns messages in OpenAI/Groq-compatible format.
        """

        history = self.get_history(
            user_id,
            limit
        )

        return [
            {
                "role": item["role"],
                "content": item["content"],
            }
            for item in history
        ]
