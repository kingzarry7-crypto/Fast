"""Opt-in, web-account-scoped conversation memory for ZARRY."""
from __future__ import annotations

from uuid import UUID

from database import get_db_cursor


class PostgresConversationMemory:
    """Stores only web conversations after explicit per-user opt-in.

    This adapter never consults legacy cross-platform identity mappings.
    Apply migrations/001_general_memory.sql before enabling the feature.
    """

    def __init__(self, cursor_factory=get_db_cursor):
        self.cursor_factory = cursor_factory

    @staticmethod
    def _user_id(principal) -> UUID:
        if getattr(principal, "platform", None) != "web":
            raise ValueError("Persistent ZARRY memory is not enabled for this platform")
        return UUID(str(principal.platform_user_id))

    def is_enabled(self, principal) -> bool:
        user_id = self._user_id(principal)
        with self.cursor_factory(commit=False) as cur:
            cur.execute(
                "SELECT enabled FROM zarry_general_memory_preferences WHERE user_id = %s",
                (str(user_id),),
            )
            row = cur.fetchone()
        if not row:
            return False
        return bool(row.get("enabled") if isinstance(row, dict) else row[0])

    def set_enabled(self, principal, enabled: bool) -> bool:
        user_id = self._user_id(principal)
        with self.cursor_factory() as cur:
            if enabled:
                cur.execute(
                    """INSERT INTO zarry_general_memory_preferences
                       (user_id, enabled, consented_at, revoked_at)
                       VALUES (%s, TRUE, NOW(), NULL)
                       ON CONFLICT (user_id) DO UPDATE SET enabled=TRUE,
                       consented_at=NOW(), revoked_at=NULL, updated_at=NOW()""",
                    (str(user_id),),
                )
            else:
                cur.execute(
                    """INSERT INTO zarry_general_memory_preferences
                       (user_id, enabled, revoked_at)
                       VALUES (%s, FALSE, NOW())
                       ON CONFLICT (user_id) DO UPDATE SET enabled=FALSE,
                       revoked_at=NOW(), updated_at=NOW()""",
                    (str(user_id),),
                )
                cur.execute("DELETE FROM zarry_general_messages WHERE user_id=%s", (str(user_id),))
        return bool(enabled)

    def get_history(self, principal, conversation_id: UUID, limit: int = 12) -> list[dict]:
        user_id = self._user_id(principal)
        limit = max(1, min(int(limit), 12))
        with self.cursor_factory(commit=False) as cur:
            cur.execute(
                """SELECT role, content FROM (
                       SELECT id, role, content FROM zarry_general_messages
                       WHERE user_id=%s AND conversation_id=%s
                       ORDER BY id DESC LIMIT %s
                   ) recent ORDER BY id ASC""",
                (str(user_id), str(conversation_id), limit),
            )
            rows = cur.fetchall()
        return [
            {"role": row.get("role"), "content": row.get("content")}
            if isinstance(row, dict) else {"role": row[0], "content": row[1]}
            for row in rows
        ]

    def append_turn(self, principal, conversation_id: UUID, user_message: str, assistant_message: str) -> None:
        user_id = self._user_id(principal)
        with self.cursor_factory() as cur:
            cur.execute(
                """INSERT INTO zarry_general_messages(user_id, conversation_id, role, content)
                   SELECT %s, %s, 'user', %s
                   WHERE EXISTS (
                       SELECT 1 FROM zarry_general_memory_preferences
                       WHERE user_id=%s AND enabled=TRUE
                   )""",
                (str(user_id), str(conversation_id), user_message, str(user_id)),
            )
            cur.execute(
                """INSERT INTO zarry_general_messages(user_id, conversation_id, role, content)
                   SELECT %s, %s, 'assistant', %s
                   WHERE EXISTS (
                       SELECT 1 FROM zarry_general_memory_preferences
                       WHERE user_id=%s AND enabled=TRUE
                   )""",
                (str(user_id), str(conversation_id), assistant_message, str(user_id)),
            )
