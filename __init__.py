"""
Web package - King Zarry AI Web Frontend Database Layer
This package is WEB ONLY and independent from Telegram.
"""
from .database import (
    get_database_url,
    is_database_configured,
    get_connection,
    get_db_connection,
    get_db_cursor,
    check_database_health,
    check_database_health_async,
    init_web_database,
)

__all__ = [
    "get_database_url",
    "is_database_configured",
    "get_connection",
    "get_db_connection",
    "get_db_cursor",
    "check_database_health",
    "check_database_health_async",
    "init_web_database",
]
