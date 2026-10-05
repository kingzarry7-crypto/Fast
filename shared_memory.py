"""Safe bridge between existing SQLite memory and shared Neon memory.

Existing SQLite memory remains the fallback. When DATABASE_URL is available,
Neon becomes the shared persistent store. Existing per-user SQLite records are
migrated once on first access, so adding this layer does not erase old memory.
"""
import logging
from typing import Optional

from memory import Memory
from neon_memory import NeonMemory

logger = logging.getLogger("shared_memory")


class SharedMemory:
    def __init__(self, platform: str, legacy_path: Optional[str] = None):
        self.platform = str(platform or "unknown").lower()
        self.legacy = Memory(legacy_path or "king_zarry_memory.db")
        self.shared = None
        self._migrated = set()

        # Neon is optional at runtime. If it is unavailable, existing SQLite
        # memory continues to work exactly as before.
        try:
            import os
            if os.getenv("DATABASE_URL"):
                self.shared = NeonMemory()
                logger.info("🧠 Shared memory enabled for %s", self.platform)
            else:
                logger.info("ℹ️ DATABASE_URL missing; using existing SQLite memory for %s", self.platform)
        except Exception as exc:
            self.shared = None
            logger.warning("⚠️ Shared Neon memory unavailable for %s; SQLite fallback active: %s", self.platform, type(exc).__name__)

    def _key(self, user_id) -> str:
        raw = str(user_id)
        local = f"{self.platform}:{raw}"
        # Once a user links Web/Telegram/Discord identities, use the canonical
        # identity for all shared-memory reads/writes. Before linking, behavior
        # is exactly the existing platform namespace.
        try:
            if self.shared:
                resolved = self.shared.resolve_identity(self.platform, raw)
                if resolved:
                    return str(resolved)
        except Exception:
            pass
        return local

    def _migrate_user(self, user_id):
        if not self.shared:
            return
        raw = str(user_id)
        key = self._key(raw)
        if key in self._migrated:
            return
        try:
            # Migrate only the missing tail. This makes restarts safe and avoids
            # duplicating messages that were already copied to Neon.
            legacy_count = self.legacy.count(raw)
            shared_count = self.shared.count(key)
            if shared_count < legacy_count:
                legacy_history = self.legacy.get_history(raw, limit=200)
                missing = legacy_history[shared_count:]
                for item in missing:
                    self.shared.add_message(
                        key, item.get("role", "user"), item.get("content", ""),
                        source_platform=self.platform
                    )
            profile = self.legacy.get_user_profile(raw)
            if profile:
                self.shared.update_user_profile(
                    key, platform=self.platform,
                    username=profile.get("username"),
                    first_name=profile.get("first_name"),
                    last_name=profile.get("last_name"),
                    preferred_name=profile.get("preferred_name"),
                    language=profile.get("language"),
                    user_timezone=profile.get("timezone"),
                )
            for fact in self.legacy.get_facts(raw, limit=200):
                self.shared.add_fact(key, fact.get("fact", ""), fact.get("category", "general"), fact.get("source", "user"))
            prefs = self.legacy.get_trading_preferences(raw)
            if prefs:
                self.shared.save_trading_preferences(
                    key,
                    preferred_assets=prefs.get("preferred_assets"),
                    preferred_timeframe=prefs.get("preferred_timeframe"),
                    trading_style=prefs.get("trading_style"),
                    risk_preference=prefs.get("risk_preference"),
                    preferred_analysis=prefs.get("preferred_analysis"),
                    broker=prefs.get("broker"),
                    notes=prefs.get("notes"),
                )
            self.shared.add_identity(key, self.platform, raw, profile.get("username") if profile else None)
            self._migrated.add(key)
        except Exception as exc:
            # Never make a migration problem stop the bot.
            logger.warning("Memory migration deferred for %s: %s", key, type(exc).__name__)

    def _use(self, method, user_id, *args, **kwargs):
        if self.shared:
            self._migrate_user(user_id)
            try:
                return getattr(self.shared, method)(self._key(user_id), *args, **kwargs)
            except Exception as exc:
                logger.warning("Shared memory %s failed; using SQLite fallback: %s", method, type(exc).__name__)
        return getattr(self.legacy, method)(str(user_id), *args, **kwargs)

    def register_user(self, user_id, **kwargs):
        if self.shared:
            self._migrate_user(user_id)
            try:
                return self.shared.register_user(self._key(user_id), platform=self.platform, **kwargs)
            except Exception:
                pass
        return self.legacy.register_user(str(user_id), platform=self.platform, **kwargs)

    def update_user_profile(self, user_id, **kwargs):
        return self._use("update_user_profile", user_id, platform=self.platform, **kwargs)

    def get_user_profile(self, user_id):
        return self._use("get_user_profile", user_id)

    def get_preferred_name(self, user_id):
        return self._use("get_preferred_name", user_id)

    def set_user_subscription(self, user_id, is_subscribed, expires_at=None):
        return self._use("set_user_subscription", user_id, is_subscribed, expires_at)

    def add_message(self, user_id, role, content):
        return self._use("add_message", user_id, role, content, source_platform=self.platform)

    def save_message(self, user_id, role, content):
        return self.add_message(user_id, role, content)

    def remember(self, user_id, role, content):
        return self.add_message(user_id, role, content)

    def get_history(self, user_id, limit=20):
        return self._use("get_history", user_id, limit)

    def get_messages(self, user_id, limit=20):
        return self.get_history(user_id, limit)

    def load_history(self, user_id, limit=20):
        return self.get_history(user_id, limit)

    def get_context(self, user_id, limit=20):
        return self.get_history(user_id, limit)

    def get_chat_messages(self, user_id, limit=20):
        return self._use("get_chat_messages", user_id, limit)

    def add_fact(self, user_id, fact, category="general", source="user"):
        return self._use("add_fact", user_id, fact, category, source)

    def remember_fact(self, user_id, fact, category="general"):
        return self.add_fact(user_id, fact, category)

    def get_facts(self, user_id, category=None, limit=50):
        if category is None:
            return self._use("get_facts", user_id, limit=limit)
        return self._use("get_facts", user_id, category, limit)

    def get_memory_facts_text(self, user_id, limit=30):
        return self._use("get_memory_facts_text", user_id, limit)

    def delete_fact(self, user_id, fact):
        return self._use("delete_fact", user_id, fact)

    def save_trading_preferences(self, user_id, **kwargs):
        return self._use("save_trading_preferences", user_id, **kwargs)

    def get_trading_preferences(self, user_id):
        return self._use("get_trading_preferences", user_id)

    def get_trading_context(self, user_id):
        return self._use("get_trading_context", user_id)

    def search_memory(self, user_id, query, limit=20):
        return self._use("search_memory", user_id, query, limit)

    def clear_history(self, user_id):
        return self._use("clear_history", user_id)

    def clear_memory(self, user_id):
        return self.clear_history(user_id)

    def forget(self, user_id):
        return self.clear_history(user_id)

    def clear_all(self):
        if self.shared:
            try:
                return self.shared.clear_all()
            except Exception:
                pass
        return self.legacy.clear_all()

    def count(self, user_id=None):
        if user_id is None:
            if self.shared:
                try:
                    return self.shared.count()
                except Exception:
                    pass
            return self.legacy.count()
        return self._use("count", user_id)

    def health_check(self):
        if self.shared:
            try:
                if self.shared.health_check():
                    return True
            except Exception:
                pass
        return self.legacy.health_check()
