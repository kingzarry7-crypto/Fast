"""Read-only status inspection for checksum-tracked ZARRY database migrations."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg2


MIGRATION_FILES = (
    "004_image_smoke_diagnostics.sql",
    "005_image_smoke_v2_authorization.sql",
)
MIGRATION_DIR = Path(__file__).resolve().parent / "migrations"


def get_migration_status() -> dict:
    """Read the production migration ledger without permitting database writes."""
    dsn = os.environ.get("ZARRY_MIGRATION_DATABASE_URL")
    if not dsn:
        raise RuntimeError("ZARRY migration database is not configured")

    expected = {}
    for name in MIGRATION_FILES:
        path = MIGRATION_DIR / name
        if path.is_file():
            expected[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    connection = psycopg2.connect(dsn, connect_timeout=5)
    cursor = None
    try:
        cursor = connection.cursor()
        # This must be the first statement in the transaction. It ensures a
        # future accidental write added to this diagnostic is rejected by PG.
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("SELECT to_regclass('public.zarry_schema_migrations')")
        ledger_exists = cursor.fetchone()[0] is not None

        recorded = {}
        if ledger_exists:
            cursor.execute(
                "SELECT migration_name, sha256 "
                "FROM public.zarry_schema_migrations "
                "WHERE migration_name = ANY(%s)",
                (list(MIGRATION_FILES),),
            )
            recorded = {
                str(name): str(digest).strip()
                for name, digest in (cursor.fetchall() or [])
            }

        migrations = []
        for name in MIGRATION_FILES:
            if name not in expected:
                status = "migration_file_missing"
            elif name not in recorded:
                status = "pending"
            elif recorded[name] == expected[name]:
                status = "applied"
            else:
                status = "checksum_mismatch"
            migrations.append({"name": name, "status": status})

        return {"status": "ok", "migrations": migrations}
    finally:
        if cursor is not None:
            cursor.close()
        # End the read-only transaction without committing anything.
        connection.rollback()
        connection.close()
