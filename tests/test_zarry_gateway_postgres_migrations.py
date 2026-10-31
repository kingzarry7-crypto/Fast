#!/usr/bin/env python3
"""Apply ZARRY migrations to a disposable PostgreSQL database and verify constraints."""
import os
import pathlib
import uuid

import psycopg2
from psycopg2 import IntegrityError

ROOT = pathlib.Path(__file__).resolve().parents[1]
dsn = os.environ["ZARRY_TEST_DATABASE_URL"]
conn = psycopg2.connect(dsn)
conn.autocommit = False


def must_reject(cur, sql, params=()):
    cur.execute("SAVEPOINT expected_constraint_failure")
    try:
        cur.execute(sql, params)
    except IntegrityError:
        cur.execute("ROLLBACK TO SAVEPOINT expected_constraint_failure")
        cur.execute("RELEASE SAVEPOINT expected_constraint_failure")
    else:
        cur.execute("ROLLBACK TO SAVEPOINT expected_constraint_failure")
        cur.execute("RELEASE SAVEPOINT expected_constraint_failure")
        raise AssertionError("Expected PostgreSQL constraint to reject statement")


try:
    with conn.cursor() as cur:
        # Minimal parent table matching the production FK target; this database is
        # created for this workflow run and is never the user's Neon database.
        cur.execute("CREATE TABLE web_users (id UUID PRIMARY KEY)")
        for migration in (
            "zarry_gateway/migrations/001_general_memory.sql",
            "zarry_gateway/migrations/002_hf_budget.sql",
        ):
            cur.execute((ROOT / migration).read_text(encoding="utf-8"))

        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        request_id = uuid.uuid4()
        cur.execute("INSERT INTO web_users (id) VALUES (%s)", (str(user_id),))

        cur.execute(
            "SELECT enabled FROM zarry_general_memory_preferences WHERE user_id=%s",
            (str(user_id),),
        )
        assert cur.fetchone() is None  # no consent row means memory remains off

        cur.execute(
            "INSERT INTO zarry_general_memory_preferences (user_id) VALUES (%s) RETURNING enabled",
            (str(user_id),),
        )
        assert cur.fetchone()[0] is False

        must_reject(
            cur,
            "UPDATE zarry_general_memory_preferences SET enabled=TRUE WHERE user_id=%s",
            (str(user_id),),
        )
        cur.execute(
            """UPDATE zarry_general_memory_preferences
               SET enabled=TRUE, consented_at=NOW(), revoked_at=NULL
               WHERE user_id=%s""",
            (str(user_id),),
        )
        cur.execute(
            """INSERT INTO zarry_general_messages
               (user_id, conversation_id, role, content)
               VALUES (%s, %s, 'user', 'migration integration test')""",
            (str(user_id), str(conversation_id)),
        )
        must_reject(
            cur,
            """INSERT INTO zarry_general_messages
               (user_id, conversation_id, role, content)
               VALUES (%s, %s, 'system', 'not an allowed persisted role')""",
            (str(user_id), str(conversation_id)),
        )
        must_reject(
            cur,
            """INSERT INTO zarry_general_messages
               (user_id, conversation_id, role, content)
               VALUES (%s, %s, 'user', '')""",
            (str(user_id), str(conversation_id)),
        )

        cur.execute(
            """INSERT INTO zarry_hf_monthly_budget
               (billing_month, limit_micro_usd, reserved_micro_usd, spent_micro_usd)
               VALUES (DATE '2026-10-01', 2000000, 500000, 0)"""
        )
        cur.execute(
            """INSERT INTO zarry_hf_budget_reservations
               (request_id, billing_month, reserved_micro_usd, status)
               VALUES (%s, DATE '2026-10-01', 500000, 'reserved')""",
            (str(request_id),),
        )
        must_reject(
            cur,
            """UPDATE zarry_hf_monthly_budget
               SET reserved_micro_usd=2000001
               WHERE billing_month=DATE '2026-10-01'""",
        )
        must_reject(
            cur,
            """INSERT INTO zarry_hf_budget_reservations
               (request_id, billing_month, reserved_micro_usd, status)
               VALUES (%s, DATE '2026-10-01', 0, 'reserved')""",
            (str(uuid.uuid4()),),
        )

        # Both tables must cascade with deletion of the owning web account.
        cur.execute("DELETE FROM web_users WHERE id=%s", (str(user_id),))
        cur.execute(
            "SELECT COUNT(*) FROM zarry_general_messages WHERE user_id=%s",
            (str(user_id),),
        )
        assert cur.fetchone()[0] == 0
        cur.execute(
            "SELECT COUNT(*) FROM zarry_general_memory_preferences WHERE user_id=%s",
            (str(user_id),),
        )
        assert cur.fetchone()[0] == 0

    conn.commit()
    print("PASS: both ZARRY migrations applied; defaults, constraints, FKs and cascade verified.")
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()
