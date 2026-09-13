import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Memory:
    """
    👑 KING ZARRY AI
    Unified persistent SQLite memory.

    Preserves compatibility with existing code:

        Memory(DATABASE_PATH)
        memory.add_message(...)
        memory.save_message(...)
        memory.remember(...)
        memory.get_history(...)
        memory.get_messages(...)
        memory.load_history(...)
        memory.get_context(...)
        memory.clear_history(...)
        memory.clear_memory(...)
        memory.forget(...)
        memory.clear_all()
        memory.count(...)
        memory.get_chat_messages(...)

    Adds:

        User profiles
        Preferred names
        User facts
        Trading preferences
        Platform tracking
        Memory search
        Memory summaries
    """

    def __init__(
        self,
        database_path: str = "king_zarry_memory.db"
    ):
        self.database_path = os.getenv(
            "MEMORY_DB_PATH",
            database_path
        )

        self.lock = threading.RLock()

        self._init_database()

        print(
            "🧠 Persistent Memory initialized: "
            f"{self.database_path}"
        )

    # ======================================================
    # DATABASE CONNECTION
    # ======================================================

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(
            os.path.abspath(self.database_path)
        )

        if directory:
            os.makedirs(
                directory,
                exist_ok=True
            )

        conn = sqlite3.connect(
            self.database_path,
            timeout=30.0,
            check_same_thread=False
        )

        conn.row_factory = sqlite3.Row

        conn.execute(
            "PRAGMA busy_timeout = 30000"
        )

        conn.execute(
            "PRAGMA journal_mode = WAL"
        )

        conn.execute(
            "PRAGMA foreign_keys = ON"
        )

        conn.execute(
            "PRAGMA synchronous = NORMAL"
        )

        return conn

    # ======================================================
    # TIME HELPERS
    # ======================================================

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    # ======================================================
    # DATABASE INITIALIZATION
    # ======================================================

    def _init_database(self):
        with self.lock:
            conn = self._connect()

            try:
                # Existing conversation table.
                # It is intentionally preserved.
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

                # User profile table.
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_users (
                        user_id TEXT PRIMARY KEY,
                        platform TEXT NOT NULL DEFAULT 'unknown',
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        preferred_name TEXT,
                        language TEXT,
                        timezone TEXT,
                        is_subscribed INTEGER NOT NULL DEFAULT 0,
                        subscription_expires_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

                # Long-term facts explicitly remembered
                # about a user.
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        fact TEXT NOT NULL,
                        category TEXT NOT NULL DEFAULT 'general',
                        source TEXT NOT NULL DEFAULT 'user',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(user_id, fact)
                    )
                    """
                )

                # Trading preferences.
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trading_preferences (
                        user_id TEXT PRIMARY KEY,
                        preferred_assets TEXT,
                        preferred_timeframe TEXT,
                        trading_style TEXT,
                        risk_preference TEXT,
                        preferred_analysis TEXT,
                        broker TEXT,
                        notes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

                # Helpful indexes.
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_ai_memory_user
                    ON ai_memory(user_id)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_ai_memory_user_created
                    ON ai_memory(user_id, created_at)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_user_facts_user
                    ON user_facts(user_id)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_memory_users_platform
                    ON memory_users(platform)
                    """
                )

                conn.commit()

            finally:
                conn.close()

    # ======================================================
    # USER PROFILE
    # ======================================================

    def register_user(
        self,
        user_id,
        platform: str = "unknown",
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        preferred_name: Optional[str] = None
    ) -> bool:
        """
        Create or update a user profile.
        """

        user_id = str(user_id)
        platform = str(platform or "unknown")

        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    """
                    INSERT INTO memory_users (
                        user_id,
                        platform,
                        username,
                        first_name,
                        last_name,
                        preferred_name,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(user_id)
                    DO UPDATE SET
                        platform = COALESCE(
                            excluded.platform,
                            memory_users.platform
                        ),
                        username = COALESCE(
                            excluded.username,
                            memory_users.username
                        ),
                        first_name = COALESCE(
                            excluded.first_name,
                            memory_users.first_name
                        ),
                        last_name = COALESCE(
                            excluded.last_name,
                            memory_users.last_name
                        ),
                        preferred_name = COALESCE(
                            excluded.preferred_name,
                            memory_users.preferred_name
                        ),
                        updated_at = excluded.updated_at
                    """,
                    (
                        user_id,
                        platform,
                        username,
                        first_name,
                        last_name,
                        preferred_name,
                        self._now(),
                        self._now()
                    )
                )

                conn.commit()
                return True

            finally:
                conn.close()

    def update_user_profile(
        self,
        user_id,
        platform: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        preferred_name: Optional[str] = None,
        language: Optional[str] = None,
        user_timezone: Optional[str] = None
    ) -> bool:
        """
        Update only the profile values supplied.
        """

        self.register_user(
            user_id=user_id,
            platform=platform or "unknown",
            username=username,
            first_name=first_name,
            last_name=last_name,
            preferred_name=preferred_name
        )

        fields = []
        values = []

        updates = {
            "platform": platform,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "preferred_name": preferred_name,
            "language": language,
            "timezone": user_timezone
        }

        for field, value in updates.items():
            if value is not None:
                fields.append(f"{field} = ?")
                values.append(str(value))

        if not fields:
            return True

        fields.append(
            "updated_at = ?"
        )
        values.append(
            self._now()
        )
        values.append(
            str(user_id)
        )

        query = f"""
            UPDATE memory_users
            SET {", ".join(fields)}
            WHERE user_id = ?
        """

        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    query,
                    tuple(values)
                )

                conn.commit()
                return True

            finally:
                conn.close()

    def get_user_profile(
        self,
        user_id
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            conn = self._connect()

            try:
                row = conn.execute(
                    """
                    SELECT *
                    FROM memory_users
                    WHERE user_id = ?
                    """,
                    (str(user_id),)
                ).fetchone()

                if not row:
                    return None

                return dict(row)

            finally:
                conn.close()

    def get_preferred_name(
        self,
        user_id
    ) -> Optional[str]:
        profile = self.get_user_profile(
            user_id
        )

        if not profile:
            return None

        return (
            profile.get("preferred_name")
            or profile.get("first_name")
            or profile.get("username")
        )

    # ======================================================
    # SUBSCRIPTION COMPATIBILITY
    # ======================================================

    def set_user_subscription(
        self,
        user_id,
        is_subscribed: bool,
        expires_at: Optional[str] = None
    ) -> bool:
        self.register_user(user_id)

        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    """
                    UPDATE memory_users
                    SET
                        is_subscribed = ?,
                        subscription_expires_at = ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        1 if is_subscribed else 0,
                        expires_at,
                        self._now(),
                        str(user_id)
                    )
                )

                conn.commit()
                return True

            finally:
                conn.close()

    # ======================================================
    # ADD CONVERSATION MEMORY
    # ======================================================

    def add_message(
        self,
        user_id,
        role,
        content
    ):
        if content is None:
            return

        content = str(content).strip()
        role = str(role).strip()

        if not content or not role:
            return

        user_id = str(user_id)

        with self.lock:
            conn = self._connect()

            try:
                # Ensure the user exists.
                conn.execute(
                    """
                    INSERT OR IGNORE INTO memory_users (
                        user_id,
                        platform,
                        created_at,
                        updated_at
                    )
                    VALUES (?, 'unknown', ?, ?)
                    """,
                    (
                        user_id,
                        self._now(),
                        self._now()
                    )
                )

                conn.execute(
                    """
                    INSERT INTO ai_memory (
                        user_id,
                        role,
                        content,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        role,
                        content,
                        self._now()
                    )
                )

                conn.commit()

            finally:
                conn.close()

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
    # GET CONVERSATION HISTORY
    # ======================================================

    def get_history(
        self,
        user_id,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        safe_limit = max(
            1,
            min(int(limit), 200)
        )

        with self.lock:
            conn = self._connect()

            try:
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
                        safe_limit
                    )
                ).fetchall()

            finally:
                conn.close()

        rows = list(
            reversed(rows)
        )

        return [
            {
                "role": str(row["role"]),
                "content": str(row["content"]),
                "created_at": str(row["created_at"])
            }
            for row in rows
        ]

    def get_messages(
        self,
        user_id,
        limit: int = 20
    ):
        return self.get_history(
            user_id,
            limit
        )

    def load_history(
        self,
        user_id,
        limit: int = 20
    ):
        return self.get_history(
            user_id,
            limit
        )

    def get_context(
        self,
        user_id,
        limit: int = 20
    ):
        return self.get_history(
            user_id,
            limit
        )

    def get_chat_messages(
        self,
        user_id,
        limit: int = 20
    ):
        """
        OpenAI/Groq-compatible message format.
        """

        history = self.get_history(
            user_id,
            limit
        )

        return [
            {
                "role": item["role"],
                "content": item["content"]
            }
            for item in history
        ]

    # ======================================================
    # LONG-TERM USER FACTS
    # ======================================================

    def add_fact(
        self,
        user_id,
        fact: str,
        category: str = "general",
        source: str = "user"
    ) -> bool:
        """
        Save a long-term fact about a user.

        Example:
            memory.add_fact(
                user_id,
                "User prefers BTC analysis",
                "trading"
            )
        """

        if not fact:
            return False

        fact = str(fact).strip()

        if not fact:
            return False

        user_id = str(user_id)
        category = str(category or "general")
        source = str(source or "user")

        self.register_user(
            user_id
        )

        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    """
                    INSERT INTO user_facts (
                        user_id,
                        fact,
                        category,
                        source,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)

                    ON CONFLICT(user_id, fact)
                    DO UPDATE SET
                        category = excluded.category,
                        source = excluded.source,
                        updated_at = excluded.updated_at
                    """,
                    (
                        user_id,
                        fact,
                        category,
                        source,
                        self._now(),
                        self._now()
                    )
                )

                conn.commit()
                return True

            finally:
                conn.close()

    def remember_fact(
        self,
        user_id,
        fact: str,
        category: str = "general"
    ) -> bool:
        return self.add_fact(
            user_id,
            fact,
            category
        )

    def get_facts(
        self,
        user_id,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, str]]:
        safe_limit = max(
            1,
            min(int(limit), 200)
        )

        query = """
            SELECT id, fact, category, source, created_at
            FROM user_facts
            WHERE user_id = ?
        """

        params = [
            str(user_id)
        ]

        if category:
            query += """
                AND category = ?
            """
            params.append(
                str(category)
            )

        query += """
            ORDER BY updated_at DESC
            LIMIT ?
        """

        params.append(
            safe_limit
        )

        with self.lock:
            conn = self._connect()

            try:
                rows = conn.execute(
                    query,
                    tuple(params)
                ).fetchall()

                return [
                    {
                        "id": str(row["id"]),
                        "fact": str(row["fact"]),
                        "category": str(row["category"]),
                        "source": str(row["source"]),
                        "created_at": str(row["created_at"])
                    }
                    for row in rows
                ]

            finally:
                conn.close()

    def get_memory_facts_text(
        self,
        user_id,
        limit: int = 30
    ) -> str:
        facts = self.get_facts(
            user_id,
            limit=limit
        )

        if not facts:
            return ""

        return "\n".join(
            f"- {item['fact']}"
            for item in facts
        )

    def delete_fact(
        self,
        user_id,
        fact: str
    ) -> bool:
        with self.lock:
            conn = self._connect()

            try:
                cursor = conn.execute(
                    """
                    DELETE FROM user_facts
                    WHERE user_id = ? AND fact = ?
                    """,
                    (
                        str(user_id),
                        str(fact).strip()
                    )
                )

                conn.commit()

                return cursor.rowcount > 0

            finally:
                conn.close()

    # ======================================================
    # TRADING PREFERENCES
    # ======================================================

    def save_trading_preferences(
        self,
        user_id,
        preferred_assets: Optional[str] = None,
        preferred_timeframe: Optional[str] = None,
        trading_style: Optional[str] = None,
        risk_preference: Optional[str] = None,
        preferred_analysis: Optional[str] = None,
        broker: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Save trading preferences without deleting
        previously stored values.
        """

        user_id = str(user_id)

        self.register_user(
            user_id
        )

        existing = self.get_trading_preferences(
            user_id
        ) or {}

        values = {
            "preferred_assets": preferred_assets,
            "preferred_timeframe": preferred_timeframe,
            "trading_style": trading_style,
            "risk_preference": risk_preference,
            "preferred_analysis": preferred_analysis,
            "broker": broker,
            "notes": notes
        }

        for key, value in values.items():
            if value is None:
                values[key] = existing.get(key)

        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    """
                    INSERT INTO trading_preferences (
                        user_id,
                        preferred_assets,
                        preferred_timeframe,
                        trading_style,
                        risk_preference,
                        preferred_analysis,
                        broker,
                        notes,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(user_id)
                    DO UPDATE SET
                        preferred_assets = excluded.preferred_assets,
                        preferred_timeframe = excluded.preferred_timeframe,
                        trading_style = excluded.trading_style,
                        risk_preference = excluded.risk_preference,
                        preferred_analysis = excluded.preferred_analysis,
                        broker = excluded.broker,
                        notes = excluded.notes,
                        updated_at = excluded.updated_at
                    """,
                    (
                        user_id,
                        values["preferred_assets"],
                        values["preferred_timeframe"],
                        values["trading_style"],
                        values["risk_preference"],
                        values["preferred_analysis"],
                        values["broker"],
                        values["notes"],
                        existing.get(
                            "created_at",
                            self._now()
                        ),
                        self._now()
                    )
                )

                conn.commit()
                return True

            finally:
                conn.close()

    def get_trading_preferences(
        self,
        user_id
    ) -> Optional[Dict[str, Any]]:
        with self.lock:
            conn = self._connect()

            try:
                row = conn.execute(
                    """
                    SELECT *
                    FROM trading_preferences
                    WHERE user_id = ?
                    """,
                    (str(user_id),)
                ).fetchone()

                if not row:
                    return None

                return dict(row)

            finally:
                conn.close()

    def get_trading_context(
        self,
        user_id
    ) -> str:
        preferences = self.get_trading_preferences(
            user_id
        )

        if not preferences:
            return ""

        labels = {
            "preferred_assets": "Preferred assets",
            "preferred_timeframe": "Preferred timeframe",
            "trading_style": "Trading style",
            "risk_preference": "Risk preference",
            "preferred_analysis": "Preferred analysis",
            "broker": "Broker",
            "notes": "Trading notes"
        }

        lines = []

        for key, label in labels.items():
            value = preferences.get(key)

            if value:
                lines.append(
                    f"{label}: {value}"
                )

        return "\n".join(
            lines
        )

    # ======================================================
    # SEARCH MEMORY
    # ======================================================

    def search_memory(
        self,
        user_id,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """
        Search previous conversations and saved facts.
        """

        if not query:
            return []

        query = str(query).strip()

        if not query:
            return []

        safe_limit = max(
            1,
            min(int(limit), 100)
        )

        pattern = f"%{query}%"

        with self.lock:
            conn = self._connect()

            try:
                rows = conn.execute(
                    """
                    SELECT
                        role,
                        content,
                        created_at
                    FROM ai_memory
                    WHERE user_id = ?
                    AND content LIKE ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (
                        str(user_id),
                        pattern,
                        safe_limit
                    )
                ).fetchall()

                return [
                    {
                        "role": str(row["role"]),
                        "content": str(row["content"]),
                        "created_at": str(row["created_at"])
                    }
                    for row in rows
                ]

            finally:
                conn.close()

    # ======================================================
    # CLEAR USER MEMORY
    # ======================================================

    def clear_history(
        self,
        user_id
    ):
        """
        Clears conversation history and long-term memory
        for one user.
        """

        user_id = str(user_id)

        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    """
                    DELETE FROM ai_memory
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )

                conn.execute(
                    """
                    DELETE FROM user_facts
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )

                conn.execute(
                    """
                    DELETE FROM trading_preferences
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )

                conn.commit()

            finally:
                conn.close()

        print(
            "🧹 Memory cleared for user "
            f"{user_id}"
        )

    def clear_memory(
        self,
        user_id
    ):
        self.clear_history(
            user_id
        )

    def forget(
        self,
        user_id
    ):
        self.clear_history(
            user_id
        )

    # ======================================================
    # DELETE ALL MEMORY
    # ======================================================

    def clear_all(self):
        with self.lock:
            conn = self._connect()

            try:
                conn.execute(
                    "DELETE FROM ai_memory"
                )

                conn.execute(
                    "DELETE FROM user_facts"
                )

                conn.execute(
                    "DELETE FROM trading_preferences"
                )

                conn.execute(
                    "DELETE FROM memory_users"
                )

                conn.commit()

            finally:
                conn.close()

        print(
            "🧹 ALL AI MEMORY CLEARED"
        )

    # ======================================================
    # MEMORY COUNT
    # ======================================================

    def count(
        self,
        user_id=None
    ) -> int:
        with self.lock:
            conn = self._connect()

            try:
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

                return int(
                    row["count"]
                )

            finally:
                conn.close()

    # ======================================================
    # HEALTH CHECK
    # ======================================================

    def health_check(self) -> bool:
        try:
            with self.lock:
                conn = self._connect()

                try:
                    conn.execute(
                        "SELECT 1"
                    ).fetchone()

                    return True

                finally:
                    conn.close()

        except Exception as error:
            print(
                "❌ Memory health check failed:",
                repr(error)
            )

            return False
