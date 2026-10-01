import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None


class NeonMemory:
    """Shared persistent KING ZARRY AI memory in Neon PostgreSQL."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for NeonMemory")
        if psycopg2 is None:
            raise RuntimeError("psycopg2-binary is required for NeonMemory")
        self.lock = threading.RLock()
        self._init_database()
        print("🧠 Shared Neon Memory initialized", flush=True)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    def _connect(self):
        return psycopg2.connect(self.database_url, connect_timeout=8, sslmode="require")

    def _cursor(self, conn):
        return conn.cursor(cursor_factory=RealDictCursor) if RealDictCursor else conn.cursor()

    def _init_database(self):
        with self.lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("""
                CREATE TABLE IF NOT EXISTS kz_memory_users (
                    user_id TEXT PRIMARY KEY, platform TEXT NOT NULL DEFAULT 'unknown',
                    username TEXT, first_name TEXT, last_name TEXT, preferred_name TEXT,
                    language TEXT, timezone TEXT, is_subscribed BOOLEAN NOT NULL DEFAULT FALSE,
                    subscription_expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS kz_memory_identities (
                    platform TEXT NOT NULL, external_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES kz_memory_users(user_id) ON DELETE CASCADE,
                    username TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY(platform, external_id)
                );
                CREATE INDEX IF NOT EXISTS idx_kz_identity_user ON kz_memory_identities(user_id);
                CREATE TABLE IF NOT EXISTS kz_memory_messages (
                    id BIGSERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES kz_memory_users(user_id) ON DELETE CASCADE,
                    conversation_id TEXT, role TEXT NOT NULL, content TEXT NOT NULL,
                    source_platform TEXT NOT NULL DEFAULT 'unknown', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_kz_messages_user_created ON kz_memory_messages(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_kz_messages_conversation ON kz_memory_messages(user_id, conversation_id, created_at ASC);
                CREATE TABLE IF NOT EXISTS kz_memories (
                    id BIGSERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES kz_memory_users(user_id) ON DELETE CASCADE,
                    content TEXT NOT NULL, memory_type TEXT NOT NULL DEFAULT 'fact', source TEXT NOT NULL DEFAULT 'user',
                    importance DOUBLE PRECISION NOT NULL DEFAULT 0.5, confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_accessed_at TIMESTAMPTZ, UNIQUE(user_id, content)
                );
                CREATE INDEX IF NOT EXISTS idx_kz_memories_user_updated ON kz_memories(user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS kz_trading_preferences (
                    user_id TEXT PRIMARY KEY REFERENCES kz_memory_users(user_id) ON DELETE CASCADE,
                    preferred_assets TEXT, preferred_timeframe TEXT, trading_style TEXT, risk_preference TEXT,
                    preferred_analysis TEXT, broker TEXT, notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS kz_conversation_summaries (
                    id BIGSERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES kz_memory_users(user_id) ON DELETE CASCADE,
                    conversation_id TEXT, summary TEXT NOT NULL, message_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS kz_memory_events (
                    id BIGSERIAL PRIMARY KEY, user_id TEXT, event_type TEXT NOT NULL,
                    source_platform TEXT, details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_kz_memory_events_user ON kz_memory_events(user_id, created_at DESC);
                """)
                conn.commit()
            finally:
                conn.close()

    def _ensure_user(self, user_id, platform="unknown", username=None, first_name=None, last_name=None, preferred_name=None):
        uid = str(user_id)
        with self.lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute("""INSERT INTO kz_memory_users(user_id,platform,username,first_name,last_name,preferred_name)
                    VALUES(%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(user_id) DO UPDATE SET
                    platform=CASE WHEN EXCLUDED.platform='unknown' THEN kz_memory_users.platform ELSE EXCLUDED.platform END,
                    username=COALESCE(EXCLUDED.username,kz_memory_users.username),
                    first_name=COALESCE(EXCLUDED.first_name,kz_memory_users.first_name),
                    last_name=COALESCE(EXCLUDED.last_name,kz_memory_users.last_name),
                    preferred_name=COALESCE(EXCLUDED.preferred_name,kz_memory_users.preferred_name),
                    updated_at=NOW()""",
                    (uid, str(platform or "unknown"), username, first_name, last_name, preferred_name))
                conn.commit()
            finally:
                conn.close()
        return uid

    def register_user(self, user_id, platform="unknown", username=None, first_name=None, last_name=None, preferred_name=None):
        self._ensure_user(user_id, platform, username, first_name, last_name, preferred_name)
        return True

    def update_user_profile(self, user_id, platform=None, username=None, first_name=None, last_name=None, preferred_name=None, language=None, user_timezone=None):
        self._ensure_user(user_id, platform or "unknown", username, first_name, last_name, preferred_name)
        fields=[]; vals=[]
        for col,val in (("platform",platform),("username",username),("first_name",first_name),("last_name",last_name),
                        ("preferred_name",preferred_name),("language",language),("timezone",user_timezone)):
            if val is not None: fields.append(col+"=%s"); vals.append(str(val))
        if fields:
            vals.append(str(user_id))
            conn=self._connect()
            try:
                cur=conn.cursor(); cur.execute("UPDATE kz_memory_users SET "+",".join(fields)+",updated_at=NOW() WHERE user_id=%s",vals); conn.commit()
            finally: conn.close()
        return True

    def get_user_profile(self,user_id):
        conn=self._connect()
        try:
            cur=self._cursor(conn); cur.execute("SELECT * FROM kz_memory_users WHERE user_id=%s",(str(user_id),)); row=cur.fetchone()
            return dict(row) if row else None
        finally: conn.close()

    def get_preferred_name(self,user_id):
        p=self.get_user_profile(user_id) or {}
        return p.get("preferred_name") or p.get("first_name") or p.get("username")

    def set_user_subscription(self,user_id,is_subscribed,expires_at=None):
        self._ensure_user(user_id)
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("UPDATE kz_memory_users SET is_subscribed=%s,subscription_expires_at=%s,updated_at=NOW() WHERE user_id=%s",(bool(is_subscribed),expires_at,str(user_id))); conn.commit()
        finally: conn.close()
        return True

    def add_identity(self,user_id,platform,external_id,username=None):
        self._ensure_user(user_id,platform,username)
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("""INSERT INTO kz_memory_identities(platform,external_id,user_id,username) VALUES(%s,%s,%s,%s)
                ON CONFLICT(platform,external_id) DO UPDATE SET user_id=EXCLUDED.user_id,username=COALESCE(EXCLUDED.username,kz_memory_identities.username),updated_at=NOW()""",
                (str(platform),str(external_id),str(user_id),username)); conn.commit()
        finally: conn.close()
        return True

    def resolve_identity(self,platform,external_id):
        conn=self._connect()
        try:
            cur=self._cursor(conn); cur.execute("SELECT user_id FROM kz_memory_identities WHERE platform=%s AND external_id=%s",(str(platform),str(external_id))); row=cur.fetchone()
            return str(row["user_id"] if isinstance(row,dict) else row[0]) if row else None
        finally: conn.close()

    def add_message(self,user_id,role,content,conversation_id=None,source_platform="unknown"):
        if content is None or not str(content).strip(): return
        self._ensure_user(user_id,source_platform)
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("INSERT INTO kz_memory_messages(user_id,conversation_id,role,content,source_platform) VALUES(%s,%s,%s,%s,%s)",
                (str(user_id),conversation_id,str(role),str(content).strip(),str(source_platform or "unknown"))); conn.commit()
        finally: conn.close()

    def save_message(self,user_id,role,content): return self.add_message(user_id,role,content)
    def remember(self,user_id,role,content): return self.add_message(user_id,role,content)

    def get_history(self,user_id,limit=20):
        limit=max(1,min(int(limit),200)); conn=self._connect()
        try:
            cur=self._cursor(conn); cur.execute("SELECT role,content,created_at FROM kz_memory_messages WHERE user_id=%s ORDER BY id DESC LIMIT %s",(str(user_id),limit)); rows=list(cur.fetchall())
        finally: conn.close()
        rows.reverse()
        return [{"role":str(r["role"]),"content":str(r["content"]),"created_at":str(r["created_at"])} for r in rows]

    def get_messages(self,user_id,limit=20): return self.get_history(user_id,limit)
    def load_history(self,user_id,limit=20): return self.get_history(user_id,limit)
    def get_context(self,user_id,limit=20): return self.get_history(user_id,limit)
    def get_chat_messages(self,user_id,limit=20): return [{"role":x["role"],"content":x["content"]} for x in self.get_history(user_id,limit)]

    def add_fact(self,user_id,fact,category="general",source="user"):
        fact=str(fact or "").strip()
        if not fact: return False
        self._ensure_user(user_id); conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("""INSERT INTO kz_memories(user_id,content,memory_type,source,importance,confidence)
                VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id,content) DO UPDATE SET memory_type=EXCLUDED.memory_type,source=EXCLUDED.source,updated_at=NOW()""",
                (str(user_id),fact,str(category or "general"),str(source or "user"),0.8 if category in ("preference","goal","instruction") else 0.5,1.0)); conn.commit()
        finally: conn.close()
        return True

    def remember_fact(self,user_id,fact,category="general"): return self.add_fact(user_id,fact,category)

    def get_facts(self,user_id,category=None,limit=50):
        limit=max(1,min(int(limit),200)); conn=self._connect()
        try:
            cur=self._cursor(conn)
            if category: cur.execute("SELECT id,content,memory_type,source,created_at FROM kz_memories WHERE user_id=%s AND memory_type=%s ORDER BY updated_at DESC LIMIT %s",(str(user_id),str(category),limit))
            else: cur.execute("SELECT id,content,memory_type,source,created_at FROM kz_memories WHERE user_id=%s ORDER BY updated_at DESC LIMIT %s",(str(user_id),limit))
            rows=cur.fetchall()
        finally: conn.close()
        return [{"id":str(r["id"]),"fact":str(r["content"]),"category":str(r["memory_type"]),"source":str(r["source"]),"created_at":str(r["created_at"])} for r in rows]

    def get_memory_facts_text(self,user_id,limit=30): return "\n".join("- "+x["fact"] for x in self.get_facts(user_id,limit=limit))

    def delete_fact(self,user_id,fact):
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("DELETE FROM kz_memories WHERE user_id=%s AND content=%s",(str(user_id),str(fact).strip())); ok=cur.rowcount>0; conn.commit(); return ok
        finally: conn.close()

    def save_trading_preferences(self,user_id,preferred_assets=None,preferred_timeframe=None,trading_style=None,risk_preference=None,preferred_analysis=None,broker=None,notes=None):
        self._ensure_user(user_id); old=self.get_trading_preferences(user_id) or {}
        vals=[preferred_assets,preferred_timeframe,trading_style,risk_preference,preferred_analysis,broker,notes]
        keys=["preferred_assets","preferred_timeframe","trading_style","risk_preference","preferred_analysis","broker","notes"]
        vals=[v if v is not None else old.get(k) for k,v in zip(keys,vals)]
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("""INSERT INTO kz_trading_preferences(user_id,preferred_assets,preferred_timeframe,trading_style,risk_preference,preferred_analysis,broker,notes)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET
                preferred_assets=EXCLUDED.preferred_assets,preferred_timeframe=EXCLUDED.preferred_timeframe,trading_style=EXCLUDED.trading_style,
                risk_preference=EXCLUDED.risk_preference,preferred_analysis=EXCLUDED.preferred_analysis,broker=EXCLUDED.broker,notes=EXCLUDED.notes,updated_at=NOW()""",
                (str(user_id),*vals)); conn.commit()
        finally: conn.close()
        return True

    def get_trading_preferences(self,user_id):
        conn=self._connect()
        try:
            cur=self._cursor(conn); cur.execute("SELECT * FROM kz_trading_preferences WHERE user_id=%s",(str(user_id),)); row=cur.fetchone(); return dict(row) if row else None
        finally: conn.close()

    def get_trading_context(self,user_id):
        p=self.get_trading_preferences(user_id) or {}
        labels={"preferred_assets":"Preferred assets","preferred_timeframe":"Preferred timeframe","trading_style":"Trading style","risk_preference":"Risk preference","preferred_analysis":"Preferred analysis","broker":"Broker","notes":"Trading notes"}
        return "\n".join(f"{label}: {p[key]}" for key,label in labels.items() if p.get(key))

    def search_memory(self,user_id,query,limit=20):
        q=str(query or "").strip()
        if not q:return []
        conn=self._connect()
        try:
            cur=self._cursor(conn); cur.execute("SELECT role,content,created_at FROM kz_memory_messages WHERE user_id=%s AND content ILIKE %s ORDER BY id DESC LIMIT %s",(str(user_id),"%"+q+"%",max(1,min(int(limit),100)))); return [dict(r) for r in cur.fetchall()]
        finally: conn.close()

    def clear_history(self,user_id):
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("DELETE FROM kz_memory_messages WHERE user_id=%s",(str(user_id),)); cur.execute("DELETE FROM kz_memories WHERE user_id=%s",(str(user_id),)); cur.execute("DELETE FROM kz_trading_preferences WHERE user_id=%s",(str(user_id),)); conn.commit()
        finally: conn.close()

    def clear_memory(self,user_id): return self.clear_history(user_id)
    def forget(self,user_id): return self.clear_history(user_id)

    def clear_all(self):
        conn=self._connect()
        try:
            cur=conn.cursor()
            for table in ("kz_memory_messages","kz_memories","kz_trading_preferences","kz_memory_identities","kz_memory_users"): cur.execute("DELETE FROM "+table)
            conn.commit()
        finally: conn.close()

    def count(self,user_id=None):
        conn=self._connect()
        try:
            cur=conn.cursor(); cur.execute("SELECT COUNT(*) FROM kz_memory_messages"+("" if user_id is None else " WHERE user_id=%s"),(() if user_id is None else (str(user_id),))); return int(cur.fetchone()[0])
        finally: conn.close()

    def health_check(self):
        try:
            conn=self._connect()
            try: conn.cursor().execute("SELECT 1")
            finally: conn.close()
            return True
        except Exception as exc:
            print("❌ Neon Memory health check failed:",type(exc).__name__,flush=True); return False
