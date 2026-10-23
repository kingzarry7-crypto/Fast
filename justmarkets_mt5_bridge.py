"""Authenticated shadow-only JustMarkets MT5 bridge; never submits broker orders."""
import os, hmac, json, sqlite3, time, uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
router = APIRouter(prefix="/justmarkets-mt5", tags=["JustMarkets MT5 Shadow Bridge"])
SYMBOLS = {"BTC", "XAUUSD"}
def now(): return datetime.now(timezone.utc)
def dt(v):
    x = datetime.fromisoformat(str(v).replace("Z","+00:00"))
    if x.tzinfo is None: raise ValueError("timezone required")
    return x.astimezone(timezone.utc)
def db():
    p = (os.getenv("JUSTMARKETS_MT5_BRIDGE_DB_PATH") or "").strip()
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    if not p and not data_dir:
        raise HTTPException(503, "MT5 bridge disabled: configure persistent database storage")
    if not p: p = str(Path(data_dir)/"mt5-shadow.sqlite3")
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(p,timeout=15); c.row_factory=sqlite3.Row
    c.executescript("CREATE TABLE IF NOT EXISTS heartbeat(id INTEGER PRIMARY KEY, at TEXT, connected INTEGER, verified INTEGER, symbols TEXT); CREATE TABLE IF NOT EXISTS signals(id TEXT PRIMARY KEY,symbol TEXT,direction TEXT,candle TEXT,created TEXT,expires TEXT,entry REAL,stop REAL,metadata TEXT,state TEXT,epoch REAL); CREATE TABLE IF NOT EXISTS acks(id TEXT,status TEXT,code TEXT,reason TEXT,at TEXT,UNIQUE(id,status,code));")
    return c
def auth(authorization: str|None=Header(default=None)):
    s=(os.getenv("JUSTMARKETS_MT5_BRIDGE_TOKEN") or "").strip()
    if len(s)<32: raise HTTPException(503,"Bridge disabled: configure token")
    scheme,_,t=(authorization or "").partition(" ")
    if scheme.lower()!="bearer" or not hmac.compare_digest(t,s): raise HTTPException(401,"Invalid bridge credentials")
class Ack(BaseModel):
    signal_id:str=Field(min_length=1,max_length=80)
    status:str=Field(pattern="^(accepted|rejected|shadow_evaluated)$")
    code:str=Field(min_length=1,max_length=80)
    reason:str=Field(default="",max_length=500)
@router.get("/status",dependencies=[Depends(auth)])
def status():
    c=db()
    try:
        h=c.execute("SELECT * FROM heartbeat WHERE id=1").fetchone()
        return {"mode":"SHADOW_ONLY","heartbeat_received":bool(h),"last_heartbeat_at":h["at"] if h else None,"terminal_connected":bool(h and h["connected"]),"demo_verified":bool(h and h["verified"]),"verified_symbols":sorted(json.loads(h["symbols"])) if h else [],"execution_enabled":False}
    finally:c.close()
@router.post("/heartbeat",dependencies=[Depends(auth)])
def heartbeat(p:dict):
    allowed={x.strip() for x in (os.getenv("JUSTMARKETS_MT5_ALLOWED_ACCOUNTS") or "").split(",") if x.strip()}
    expected=(os.getenv("JUSTMARKETS_MT5_EXPECTED_SERVER") or "").strip()
    ok=bool(p.get("terminal_connected") is True and str(p.get("trade_mode","")).upper()=="DEMO" and expected and p.get("server")==expected and allowed and p.get("account_id") in allowed)
    symbols={}
    for s in p.get("symbols",[]):
        if not isinstance(s,dict) or s.get("name") not in SYMBOLS: continue
        try:
            if int(s["trade_mode"])>0 and float(s["volume_min"])>0 and float(s["volume_min"])<=float(s["volume_max"]) and float(s["volume_step"])>0 and float(s["tick_size"])>0: symbols[s["name"]]=s
        except (KeyError,TypeError,ValueError): pass
    if not ok: symbols={}
    c=db()
    try:
        c.execute("INSERT INTO heartbeat VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET at=excluded.at,connected=excluded.connected,verified=excluded.verified,symbols=excluded.symbols",(now().isoformat(),int(p.get("terminal_connected") is True),int(ok),json.dumps(symbols)));c.commit()
    finally:c.close()
    return {"accepted":True,"mode":"SHADOW_ONLY","demo_verified":ok,"verified_symbols":sorted(symbols),"execution_enabled":False}
def publish_shadow_signal(s:dict):
    """Queue a validated signal for shadow evaluation only."""
    sid=str(s.get("signal_id") or uuid.uuid4())
    try:
        symbol=str(s["symbol"]); direction=str(s["direction"]).upper()
        candle,created,expires=(dt(s[k]).isoformat() for k in ("candle_time","created_at","expires_at"))
        if symbol not in SYMBOLS:return {"published":False,"reason":"unsupported_symbol"}
        if direction not in {"BUY","SELL","NO_TRADE"}:return {"published":False,"reason":"invalid_direction"}
        if dt(expires)<=now() or dt(expires)<=dt(created):return {"published":False,"reason":"expired_signal"}
        if dt(candle)>dt(created) or dt(created)>(now()+timedelta(minutes=2)):return {"published":False,"reason":"invalid_signal_timestamps"}
        entry,stop=s.get("entry_reference"),s.get("stop_loss")
        if direction in {"BUY","SELL"} and (stop is None or float(stop)<=0):return {"published":False,"reason":"invalid_stop_loss"}
        if entry is not None and float(entry)<=0:return {"published":False,"reason":"invalid_entry"}
        state="informational" if direction=="NO_TRADE" else "queued"
        c=db()
        try:
            old=c.execute("SELECT state FROM signals WHERE id=?",(sid,)).fetchone()
            if old:return {"published":True,"duplicate":True,"state":old["state"],"signal_id":sid}
            c.execute("INSERT INTO signals VALUES(?,?,?,?,?,?,?,?,?,?,?)",(sid,symbol,direction,candle,created,expires,entry,stop,json.dumps(s.get("metadata") or {}),state,time.time()));c.commit()
        finally:c.close()
        return {"published":True,"duplicate":False,"state":state,"signal_id":sid}
    except (KeyError,TypeError,ValueError):return {"published":False,"reason":"invalid_signal","signal_id":sid}
@router.get("/work",dependencies=[Depends(auth)])
def work():
    c=db()
    try:
        h=c.execute("SELECT * FROM heartbeat WHERE id=1").fetchone()
        if not h or not h["verified"] or (now()-dt(h["at"])).total_seconds()>300:return {"work":None,"reason":"demo_identity_unverified_or_stale","execution_enabled":False}
        symbols=set(json.loads(h["symbols"]))
        rows=c.execute("SELECT * FROM signals WHERE state='queued' AND direction IN ('BUY','SELL') AND expires>? ORDER BY epoch LIMIT 20",(now().isoformat(),)).fetchall()
        for r in rows:
            if r["symbol"] in symbols:return {"work":{"signal_id":r["id"],"symbol":r["symbol"],"direction":r["direction"],"candle_time":r["candle"],"created_at":r["created"],"expires_at":r["expires"],"entry_reference":r["entry"],"stop_loss":r["stop"],"metadata":json.loads(r["metadata"])},"mode":"SHADOW_ONLY","execution_enabled":False}
        return {"work":None,"reason":"no_fresh_verified_signal","execution_enabled":False}
    finally:c.close()
@router.post("/ack",dependencies=[Depends(auth)])
def ack(p:Ack):
    c=db()
    try:
        r=c.execute("SELECT expires FROM signals WHERE id=?",(p.signal_id,)).fetchone()
        if not r:raise HTTPException(404,"Unknown signal")
        if dt(r["expires"])<=now():raise HTTPException(409,"Signal expired")
        c.execute("INSERT OR IGNORE INTO acks VALUES(?,?,?,?,?)",(p.signal_id,p.status,p.code,p.reason,now().isoformat()))
        if p.status in {"rejected","shadow_evaluated"}:c.execute("UPDATE signals SET state='completed' WHERE id=?",(p.signal_id,))
        c.commit()
        return {"accepted":True,"mode":"SHADOW_ONLY","execution_enabled":False}
    finally:c.close()
