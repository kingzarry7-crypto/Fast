#!/usr/bin/env python3
"""Explicit, checksum-tracked runner for ZARRY PostgreSQL migrations.

Dry-run is the default. Applying requires both --apply and
ZARRY_ALLOW_MIGRATIONS=1. Never invoke automatically during application startup.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import sys

import psycopg2

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "zarry_gateway" / "migrations"
LOCK_ID = 734_991_204


def load_migrations():
    files = sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
    return [(p.name, p.read_text(encoding="utf-8"), hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]


def run(dsn: str, apply: bool) -> list[str]:
    conn = psycopg2.connect(dsn, connect_timeout=10)
    applied_now: list[str] = []
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.web_users')")
                if cur.fetchone()[0] is None:
                    raise RuntimeError("Required parent table public.web_users does not exist; refusing ZARRY migrations")
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS zarry_schema_migrations (
                           migration_name TEXT PRIMARY KEY,
                           sha256 CHAR(64) NOT NULL,
                           applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                       )"""
                )
                for name, sql, digest in load_migrations():
                    cur.execute(
                        "SELECT sha256 FROM zarry_schema_migrations WHERE migration_name=%s",
                        (name,),
                    )
                    row = cur.fetchone()
                    if row:
                        if row[0].strip() != digest:
                            raise RuntimeError(f"Applied migration checksum changed: {name}")
                        continue
                    if not apply:
                        applied_now.append(name)
                        continue
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO zarry_schema_migrations (migration_name, sha256) VALUES (%s, %s)",
                        (name, digest),
                    )
                    applied_now.append(name)
        return applied_now
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply pending migrations (requires explicit env guard)")
    args = parser.parse_args()
    dsn = os.environ.get("ZARRY_MIGRATION_DATABASE_URL")
    if not dsn:
        parser.error("ZARRY_MIGRATION_DATABASE_URL is required")
    if args.apply and os.environ.get("ZARRY_ALLOW_MIGRATIONS") != "1":
        parser.error("--apply also requires ZARRY_ALLOW_MIGRATIONS=1")
    pending = run(dsn, apply=args.apply)
    if args.apply:
        print("Applied: " + (", ".join(pending) if pending else "none; schema is current"))
    else:
        print("Pending: " + (", ".join(pending) if pending else "none; schema is current"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Migration failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
