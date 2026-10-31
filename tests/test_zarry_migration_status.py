import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from zarry_gateway.migration_status import get_migration_status
from zarry_gateway.router import create_general_router


class FakeCursor:
    def __init__(self, ledger_exists=True, recorded=None):
        self.ledger_exists = ledger_exists
        self.recorded = recorded or {}
        self.last_query = None
        self.queries = []

    def execute(self, query, params=None):
        self.last_query = " ".join(query.split())
        self.queries.append(self.last_query)

    def fetchone(self):
        if "to_regclass" in (self.last_query or ""):
            return ("public.zarry_schema_migrations" if self.ledger_exists else None,)
        return None

    def fetchall(self):
        if "SELECT migration_name, sha256" in (self.last_query or ""):
            return list(self.recorded.items())
        return []


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class MigrationStatusTests(unittest.TestCase):
    def setUp(self):
        self.migration_dir = Path(__file__).resolve().parents[1] / "zarry_gateway" / "migrations"
        self.expected = {
            name: hashlib.sha256((self.migration_dir / name).read_bytes()).hexdigest()
            for name in (
                "004_image_smoke_diagnostics.sql",
                "005_image_smoke_v2_authorization.sql",
            )
        }

    def test_reports_pending_migrations_using_read_only_transaction(self):
        cursor = FakeCursor(ledger_exists=False)
        connection = FakeConnection(cursor)
        with patch.dict(os.environ, {"ZARRY_MIGRATION_DATABASE_URL": "postgresql://safe-test"}), patch(
            "zarry_gateway.migration_status.psycopg2.connect", return_value=connection
        ):
            result = get_migration_status()
        self.assertEqual([item["status"] for item in result["migrations"]], ["pending", "pending"])
        self.assertEqual(cursor.queries[0], "SET TRANSACTION READ ONLY")
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)

    def test_reports_applied_migrations_only_when_checksum_matches(self):
        cursor = FakeCursor(recorded=self.expected)
        connection = FakeConnection(cursor)
        with patch.dict(os.environ, {"ZARRY_MIGRATION_DATABASE_URL": "postgresql://safe-test"}), patch(
            "zarry_gateway.migration_status.psycopg2.connect", return_value=connection
        ):
            result = get_migration_status()
        self.assertEqual([item["status"] for item in result["migrations"]], ["applied", "applied"])

    def test_reports_checksum_mismatch_without_returning_hashes(self):
        cursor = FakeCursor(recorded={"004_image_smoke_diagnostics.sql": "0" * 64})
        connection = FakeConnection(cursor)
        with patch.dict(os.environ, {"ZARRY_MIGRATION_DATABASE_URL": "postgresql://safe-test"}), patch(
            "zarry_gateway.migration_status.psycopg2.connect", return_value=connection
        ):
            result = get_migration_status()
        self.assertEqual(result["migrations"][0]["status"], "checksum_mismatch")
        self.assertNotIn("sha256", str(result))

    def test_missing_database_configuration_fails_safely(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                get_migration_status()

    def test_admin_endpoint_returns_status_without_exposing_connection_details(self):
        app = FastAPI()
        app.include_router(
            create_general_router(
                lambda request: {"id": "user"},
                object(),
                admin_check=lambda request: ({"id": "admin"}, "admin@example.com"),
            )
        )
        expected = {
            "status": "ok",
            "migrations": [
                {"name": "004_image_smoke_diagnostics.sql", "status": "pending"},
                {"name": "005_image_smoke_v2_authorization.sql", "status": "applied"},
            ],
        }
        with patch("zarry_gateway.migration_status.get_migration_status", return_value=expected):
            response = TestClient(app).get("/api/assistant/admin/migration-status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertNotIn("database_url", response.text)
        self.assertNotIn("sha256", response.text)

    def test_admin_endpoint_requires_existing_admin_gate(self):
        app = FastAPI()

        def deny_admin(request):
            raise HTTPException(status_code=403, detail="Admin access denied")

        app.include_router(
            create_general_router(lambda request: {"id": "user"}, object(), admin_check=deny_admin)
        )
        response = TestClient(app).get("/api/assistant/admin/migration-status")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
