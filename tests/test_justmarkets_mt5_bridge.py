import os, tempfile, unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import justmarkets_mt5_bridge as bridge

def ts(seconds=0): return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()

class BridgeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"JUSTMARKETS_MT5_BRIDGE_DB_PATH":self.tmp.name+"/db.sqlite3","JUSTMARKETS_MT5_BRIDGE_TOKEN":"z"*40,"JUSTMARKETS_MT5_EXPECTED_SERVER":"ExactDemoServer","JUSTMARKETS_MT5_ALLOWED_ACCOUNTS":"demo-123"})
        self.env.start(); self.addCleanup(self.env.stop); self.addCleanup(self.tmp.cleanup)
        app=FastAPI(); app.include_router(bridge.router); self.client=TestClient(app)
        self.headers={"Authorization":"Bearer "+"z"*40}
    def heartbeat(self,**changes):
        p={"terminal_connected":True,"trade_mode":"DEMO","server":"ExactDemoServer","account_id":"demo-123","symbols":[{"name":"BTC","volume_min":0.01,"volume_max":5,"volume_step":0.01,"tick_size":0.01},{"name":"XAUUSD","volume_min":0.01,"volume_max":5,"volume_step":0.01,"tick_size":0.01},{"name":"BTCUSD","volume_min":0.01,"volume_max":5,"volume_step":0.01,"tick_size":0.01}]}
        p.update(changes); return self.client.post("/justmarkets-mt5/heartbeat",json=p,headers=self.headers)
    def signal(self,**changes):
        p={"signal_id":"signal-1","symbol":"BTC","direction":"BUY","candle_time":ts(-7200),"created_at":ts(-10),"expires_at":ts(1800),"entry_reference":60000,"stop_loss":59000}
        p.update(changes); return bridge.publish_shadow_signal(p)
    def test_token_required_and_missing_secret_disables(self):
        self.assertEqual(self.client.get("/justmarkets-mt5/status").status_code,503)
        with patch.dict(os.environ,{"JUSTMARKETS_MT5_BRIDGE_TOKEN":""}): self.assertEqual(self.client.get("/justmarkets-mt5/status",headers=self.headers).status_code,503)
        self.assertEqual(self.client.get("/justmarkets-mt5/status",headers={"Authorization":"Bearer bad"}).status_code,401)
    def test_demo_server_and_account_must_match(self):
        self.assertFalse(self.heartbeat(trade_mode="REAL").json()["demo_verified"])
        self.assertFalse(self.heartbeat(server="Live").json()["demo_verified"])
        self.assertFalse(self.heartbeat(account_id="other").json()["demo_verified"])
    def test_only_exact_known_symbols(self):
        self.assertEqual(self.heartbeat().json()["verified_symbols"],["BTC","XAUUSD"])
    def test_duplicate_signal_is_idempotent(self):
        self.assertFalse(self.signal()["duplicate"]); self.assertTrue(self.signal()["duplicate"])
    def test_expired_and_unknown_symbols_rejected(self):
        self.assertEqual(self.signal(expires_at=ts(-1))["reason"],"expired_signal")
        self.assertEqual(self.signal(symbol="BTCUSD")["reason"],"unsupported_symbol")
    def test_no_trade_is_not_actionable(self):
        self.assertEqual(self.signal(direction="NO_TRADE",stop_loss=None)["state"],"informational")
        self.heartbeat()
        self.assertIsNone(self.client.get("/justmarkets-mt5/work",headers=self.headers).json()["work"])
    def test_missing_stop_loss_rejected(self):
        self.assertEqual(self.signal(stop_loss=None)["reason"],"invalid_stop_loss")
    def test_work_requires_verified_recent_heartbeat(self):
        self.signal()
        self.assertIsNone(self.client.get("/justmarkets-mt5/work",headers=self.headers).json()["work"])
        self.heartbeat()
        self.assertEqual(self.client.get("/justmarkets-mt5/work",headers=self.headers).json()["work"]["signal_id"],"signal-1")
    def test_unknown_ack_rejected_and_status_never_enables_execution(self):
        self.assertEqual(self.client.post("/justmarkets-mt5/ack",headers=self.headers,json={"signal_id":"unknown","status":"shadow_evaluated","code":"OK"}).status_code,404)
        self.assertFalse(self.client.get("/justmarkets-mt5/status",headers=self.headers).json()["execution_enabled"])

if __name__=="__main__": unittest.main()
