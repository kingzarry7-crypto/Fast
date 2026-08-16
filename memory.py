import os
import re
import sqlite3
import asyncio
import threading
from datetime import datetime, timedelta, timezone

# =========================================================
# 👑 KING ZARRY AI - THREAD-SAFE & ASYNC-FRIENDLY SQLITE MEMORY CLASS
# =========================================================

class Memory:
    def __init__(self, database_path: str = "king_zarry_memory.db", retention_hours: int = 24):
        self.db_path = database_path
        self.retention_hours = retention_hours
        self.lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        # Connection configuration optimized for multithreading and async wrappers
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.lock:
            with self._get_connection() as conn:
                # Enable WAL mode for high concurrency read/write performance
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Optimal compound index for memory fetching by user and ID ordering
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_id_time 
                    ON conversation_memory(user_id, timestamp, id)
                """)
                conn.commit()

    def _clean_old_records(self, conn):
        """Purge records older than retention threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation_memory WHERE timestamp < ?", (cutoff_str,))

    def add(self, user_id: str, role: str, content: str):
        """Adds a message to memory and cleans up expired logs in a single lock pass."""
        with self.lock:
            with self._get_connection() as conn:
                self._clean_old_records(conn)
                cursor = conn.cursor()
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO conversation_memory (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (str(user_id), role, content, now_str)
                )
                conn.commit()

    def get_history(self, user_id: str, limit: int = 10) -> list:
        """Fetches history without writing/deleting to maximize read performance."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT role, content FROM (
                        SELECT id, role, content FROM conversation_memory 
                        WHERE user_id = ? AND timestamp >= ?
                        ORDER BY id DESC LIMIT ?
                    ) ORDER BY id ASC
                    """,
                    (str(user_id), cutoff_str, limit)
                )
                rows = cursor.fetchall()
                return [{"role": row["role"], "content": row["content"]} for row in rows]

    def clear(self, user_id: str):
        """Clears memory for a specific user."""
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversation_memory WHERE user_id = ?", (str(user_id),))
                conn.commit()

    def get_user_stats(self) -> dict:
        """Retrieves user count statistics."""
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        
        with self.lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM conversation_memory")
                total_users = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM conversation_memory WHERE timestamp >= ?",
                    (cutoff_24h,)
                )
                active_24h = cursor.fetchone()[0] or 0

                return {
                    "total_users": total_users,
                    "active_24h": active_24h
                }
