"""
KING ZARRY AI - Web Frontend Database Connection Layer
WEB ONLY - Completely independent from Telegram databases (king_zarry_memory.db, etc.)

This module connects ONLY to Neon PostgreSQL for web frontend users.
- Reads DATABASE_URL from environment
- Never contains secrets
- Server-side only
- Fails safely if DATABASE_URL missing
- Provides reusable connection and health-check

Usage:
    from backend.app.web.database import get_connection, check_database_health, get_db_cursor

    # Simple query
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM web_users WHERE id = %s", (user_id,))
        user = cur.fetchone()
"""
import os
import logging
from typing import Optional, Generator, Tuple, Any
from contextlib import contextmanager

logger = logging.getLogger("web_database")

# Global pool/cache - initialized lazily
_connection_pool = None
_pool_initialized = False


def get_database_url() -> Optional[str]:
    """
    Read DATABASE_URL from environment.
    Never hard-code real URL.
    Returns None if missing (fail-safe).
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.warning("DATABASE_URL not set - web database unavailable (expected in deployment)")
        return None
    # Basic validation - must be postgresql
    if not url.startswith("postgres"):
        logger.error("DATABASE_URL does not appear to be a PostgreSQL URL")
        return None
    return url


def is_database_configured() -> bool:
    """Check if DATABASE_URL is configured without exposing it"""
    return get_database_url() is not None


def _get_psycopg2_connection():
    """Create a direct psycopg2 connection"""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise ImportError(
            "PostgreSQL driver not installed. Install with: pip install psycopg2-binary"
        )

    db_url = get_database_url()
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Neon PostgreSQL: {type(e).__name__}")
        raise


def get_connection():
    """
    Get a raw PostgreSQL connection (psycopg2).
    Caller must close connection.
    For most use cases, prefer get_db_cursor() context manager.
    """
    return _get_psycopg2_connection()


@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """
    Context manager for database connection.
    Usage:
        with get_db_connection() as conn:
            ...
    Automatically handles commit/rollback and close.
    """
    conn = None
    try:
        conn = _get_psycopg2_connection()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"Database transaction failed: {type(e).__name__}: {str(e)[:200]}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@contextmanager
def get_db_cursor(commit: bool = True) -> Generator[Any, None, None]:
    """
    Context manager for database cursor - most common usage.
    Usage:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM web_users")
            users = cur.fetchall()

        # With parameters (safe from SQL injection):
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM web_users WHERE email = %s", (email,))

    Automatically commits if commit=True.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        # Use RealDictCursor if available for dict results
        try:
            import psycopg2.extras
            # We'll create a new cursor with RealDictCursor for better DX
            cur.close()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        except Exception:
            # Fallback to regular cursor
            pass

        try:
            yield cur
            if commit:
                conn.commit()
        finally:
            try:
                cur.close()
            except Exception:
                pass


def check_database_health() -> dict:
    """
    Simple health-check for web database.
    Returns dict with status, never exposes credentials.
    Safe to expose via /health endpoint (without details).

    Returns:
        {
            "configured": bool,
            "connected": bool,
            "status": "healthy" | "not_configured" | "connection_failed" | "driver_missing"
        }
    """
    if not is_database_configured():
        return {
            "configured": False,
            "connected": False,
            "status": "not_configured",
            "message": "DATABASE_URL not set"
        }

    try:
        # Check driver
        try:
            import psycopg2  # noqa: F401
        except ImportError:
            return {
                "configured": True,
                "connected": False,
                "status": "driver_missing",
                "message": "psycopg2-binary not installed"
            }

        # Try actual connection with short timeout
        conn = _get_psycopg2_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            return {
                "configured": True,
                "connected": True,
                "status": "healthy",
                "message": "Neon PostgreSQL connected"
            }
        finally:
            conn.close()

    except ValueError as ve:
        # DATABASE_URL missing
        return {
            "configured": False,
            "connected": False,
            "status": "not_configured",
            "message": str(ve)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {type(e).__name__}")
        return {
            "configured": True,
            "connected": False,
            "status": "connection_failed",
            "message": f"Connection failed: {type(e).__name__}"
        }


def init_web_database():
    """
    Initialize web database schema from web_database.sql
    Call this once during deployment or from migration script.

    This is WEB ONLY - does not touch Telegram databases.
    """
    import pathlib

    db_url = get_database_url()
    if not db_url:
        raise ValueError("DATABASE_URL not set - cannot init database")

    schema_path = pathlib.Path(__file__).parent / "web_database.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        # commit handled by context manager
        logger.info("Web database schema initialized successfully")


# For async frameworks (FastAPI) - optional async wrapper
async def check_database_health_async() -> dict:
    """
    Async wrapper for health check (runs blocking check in thread)
    """
    import asyncio
    return await asyncio.to_thread(check_database_health)
