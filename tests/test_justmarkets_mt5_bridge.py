import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

import justmarkets_mt5_bridge as bridge


def stamp(delta=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta)).isoformat()


class JustMarketsBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "JUSTMARKETS_MT5_BRIDGE_DB_PATH": os.path.join(self.temp.name, "bridge.sqlite3"),
            "JUSTMARKETS_MT5_BRIDGE_TOKEN": "t" * 48,
            "JUSTMARKETS_MT5_EXPECTED_SERVER": "JustMarkets-Demo3",
            "JUSTMARKETS_MT5_ALLOWED_ACCOUNTS": "demo-account-1",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)
        bridge._init_db()
        app = FastAPI()
        app.include_router(bridge.router)
        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer " + "t" * 48}

    def heartbeat(self, **overrides):
        data = {
            "terminal_connected": True, "trade_mode": "DEMO",
            "server": "JustMarkets-Demo3", "account_id": "demo-account-1",
            "symbols": [
                {"name": "BTC", "trade_mode": 4, "volume_min": 0.01, "volume_max": 10,
                 "volume_step": 0.01, "tick_size": 0.01, "tick_value": 0.01, "digits": 2, "stops_level": 0},
                {"name": "XAUUSD", "trade_mode": 4, "volume_min": 0.01, "volume_max": 10,
                 "volume_step": 0.01, "tick_size": 0.01, "tick_value": 0.01, "digits": 2, "stops_level": 0},
                {"name": "BTCUSD", "trade_mode": 4, "volume_min": 0.01, "volume_max": 10,
                 "volume_step": 0.01, "tick_size": 0.01, "tick_value": 0.01, "digits": 2, "stops_level": 0},
            ],
        }
        data.update(overrides)
        return self.client.post("/justmarkets-mt5/heartbeat", json=data, headers=self.headers)

    def signal(self, **overrides):
        value = {"signal_id": "sig-1", "symbol": "BTC", "direction": "BUY",
                 "candle_time": stamp(-3600), "created_at": stamp(-30), "expires_at": stamp(1800),
                 "entry_reference": 60000, "stop_loss": 59000, "metadata": {"timeframe": "1h"}}
        value.update(overrides)
        return bridge.publish_shadow_signal(value)

    def test_missing_and_invalid_token_fail(self):
        self.assertEqual(self.client.get("/justmarkets-mt5/status").status_code, 503)
        self.assertEqual(self.client.get("/justmarkets-mt5/status", headers={"Authorization": "Bearer bad"}).status_code, 503)
        with patch.dict(os.environ, {"JUSTMARKETS_MT5_BRIDGE_TOKEN": "t" * 48}):
            self.assertEqual(self.client.get("/justmarkets-mt5/status", headers={"Authorization": "Bearer bad"}).status_code, 401)

    def test_absent_secret_disables_operations(self):
        with patch.dict(os.environ, {"JUSTMARKETS_MT5_BRIDGE_TOKEN": ""}):
            self.assertEqual(self.client.get("/justmarkets-mt5/status", headers=self.headers).status_code, 503)

    def test_non_demo_wrong_server_and_account_fail_closed(self):
        self.assertFalse(self.heartbeat(trade_mode="REAL").json()["demo_verified"])
        self.assertFalse(self.heartbeat(server="JustMarkets-Live").json()["demo_verified"])
        self.assertFalse(self.heartbeat(account_id="unknown").json()["demo_verified"])
        status = self.client.get("/justmarkets-mt5/status", headers=self.headers).json()
        self.assertFalse(status["demo_verified"])

    def test_symbol_alias_is_not_accepted(self):
        result = self.heartbeat().json()
        self.assertEqual(result["verified_symbols"], ["BTC", "XAUUSD"])
        self.assertNotIn("BTCUSD", result["verified_symbols"])

    def test_duplicate_signal_id_is_idempotent(self):
        first = self.signal()
        second = self.signal()
        self.assertTrue(first["published"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["signal_id"], second["signal_id"])

    def test_expired_signal_never_published_or_returned(self):
        result = self.signal(expires_at=stamp(-1))
        self.assertFalse(result["published"])
        self.heartbeat()
        self.assertIsNone(self.client.get("/justmarkets-mt5/work", headers=self.headers).json()["work"])

    def test_no_trade_is_informational_not_actionable(self):
        result = self.signal(direction="NO_TRADE", stop_loss=None)
        self.assertTrue(result["published"])
        self.assertEqual(result["state"], "informational")
        self.heartbeat()
        self.assertIsNone(self.client.get("/justmarkets-mt5/work", headers=self.headers).json()["work"])

    def test_unknown_symbols_and_missing_stop_are_rejected(self):
        self.assertEqual(self.signal(symbol="BTCUSD")["reason"], "unsupported_symbol")
        self.assertEqual(self.signal(signal_id="no-sl", stop_loss=None)["reason"], "missing_or_invalid_stop_loss")

    def test_unknown_acknowledgement_rejected(self):
        response = self.client.post("/justmarkets-mt5/ack",
            json={"signal_id": "missing", "status": "shadow_evaluated", "code": "OK"}, headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_work_requires_recent_verified_demo_heartbeat(self):
        self.signal()
        self.assertEqual(self.client.get("/justmarkets-mt5/work", headers=self.headers).json()["work"], None)
        self.heartbeat()
        work = self.client.get("/justmarkets-mt5/work", headers=self.headers).json()["work"]
        self.assertEqual(work["signal_id"], "sig-1")
        self.assertFalse(self.client.get("/justmarkets-mt5/status", headers=self.headers).json()["execution_enabled"])

    def test_secrets_not_returned(self):
        self.heartbeat()
        body = str(self.client.get("/justmarkets-mt5/status", headers=self.headers).json())
        self.assertNotIn("t" * 48, body)
        self.assertNotIn("demo-account-1", body)


if __name__ == "__main__":
    unittest.main()
