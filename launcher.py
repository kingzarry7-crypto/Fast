import os
import signal
import sys
import subprocess
import time
import hashlib

managed_processes = []

def start_process(name, command):
    print(f"🚀 Starting {name}: {' '.join(command)}", flush=True)
    try:
        proc = subprocess.Popen(command)
        print(f"✅ {name} process started (PID: {proc.pid})", flush=True)
        return [name, command, proc]
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}", flush=True)
        return None

def shutdown_handler(signum=None, frame=None):
    print("\n🛑 Shutdown signal received!", flush=True)
    for item in managed_processes:
        if not item:
            continue
        name, command, proc = item
        if proc and proc.poll() is None:
            print(f"⏹️ Stopping {name} (PID: {proc.pid})", flush=True)
            try:
                proc.terminate()
                proc.wait(timeout=8)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    print("👋 All processes stopped.", flush=True)
    sys.exit(0)

def monitor_processes():
    while True:
        for item in managed_processes:
            if not item:
                continue
            name, command, proc = item
            exit_code = proc.poll()
            if exit_code is None:
                continue
            print("=" * 55, flush=True)
            print(f"⚠️ {name} PROCESS STOPPED (exit code {exit_code})", flush=True)
            print("=" * 55, flush=True)
            print(f"🔄 Restarting {name} in 10s...", flush=True)
            time.sleep(10)
            new_proc = start_process(name, command)
            if new_proc:
                item[2] = new_proc[2]
        time.sleep(3)

def verify_bot_py():
    """
    Print bot.py fingerprint so we know which version is deployed.
    NEVER exits — only logs. Launcher continues regardless.
    """
    print("=" * 60, flush=True)
    print("🔍 LAUNCHER: verifying bot.py...", flush=True)
    print("=" * 60, flush=True)

    if not os.path.exists("bot.py"):
        print("⚠️ bot.py DOES NOT EXIST — will skip Telegram", flush=True)
        return False

    try:
        with open("bot.py", "rb") as f:
            content = f.read()
        md5 = hashlib.md5(content).hexdigest()
        size = len(content)
        print(f"📄 bot.py: {size} bytes | md5={md5}", flush=True)

        text = content.decode("utf-8", errors="replace")
        first_line = text.splitlines()[0] if text else "<EMPTY>"
        print(f"📄 bot.py first line: {first_line}", flush=True)

        # Detect the diagnostic Telegram version
        if "BOOT: bot.py starting" in text and "from telegram" in text:
            print("✅ bot.py is the NEW Telegram diagnostic version", flush=True)
            return True
        # Detect old Discord content masquerading as bot.py
        elif "import discord" in text and "from telegram" not in text:
            print("❌ bot.py contains DISCORD code (wrong file!)", flush=True)
            print("➡️ ACTION: replace bot.py contents on GitHub with the Telegram version.", flush=True)
            print("➡️ Launcher will CONTINUE anyway so FastAPI/Discord still run.", flush=True)
            return False
        else:
            print("⚠️ bot.py is an unknown version — will try to run anyway", flush=True)
            return False
    except Exception as e:
        print(f"⚠️ Cannot read bot.py: {e} — will try to run anyway", flush=True)
        return False

def main():
    print("=" * 60, flush=True)
    print("🇳🇬 LAUNCHER-V4-NO-CRASH 🇳🇬", flush=True)
    print("👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER v4", flush=True)
    print("=" * 60, flush=True)

    # ---- Verify bot.py is the right file (NON-FATAL now) ----
    bot_py_ok = verify_bot_py()
    if not bot_py_ok:
        print("⚠️ bot.py verification failed but launcher will CONTINUE.", flush=True)
        print("⚠️ FastAPI + Discord will still start. Only Telegram may fail.", flush=True)

    # ---- FastAPI ----
    if not os.path.exists("api.py"):
        print("❌ api.py not found — aborting (FastAPI is required for Vercel)", flush=True)
        sys.exit(1)

    port = os.environ.get("PORT", "8000")
    print(f"🔌 FastAPI will bind to 0.0.0.0:{port}", flush=True)

    api_process = start_process(
        "FastAPI",
        [sys.executable, "-u", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", str(port)],
    )
    if api_process:
        managed_processes.append(api_process)

    time.sleep(3)

    # ---- Telegram bot.py ----
    if os.path.exists("bot.py"):
        bot_process = start_process(
            "TelegramBot",
            [sys.executable, "-u", "bot.py"],
        )
        if bot_process:
            managed_processes.append(bot_process)
    else:
        print("ℹ️ bot.py not found — skipping Telegram", flush=True)

    # ---- Discord bot ----
    if os.path.exists("discord_bot.py"):
        discord_process = start_process(
            "DiscordBot",
            [sys.executable, "-u", "discord_bot.py"],
        )
        if discord_process:
            managed_processes.append(discord_process)
    else:
        print("ℹ️ discord_bot.py not found — skipping Discord", flush=True)

    if not managed_processes:
        print("❌ No processes started — exiting", flush=True)
        sys.exit(1)

    print("\n" + "=" * 55, flush=True)
    print("📡 KING ZARRY AI IS FULLY OPERATIONAL", flush=True)
    print(f"📦 Processes running: {[p[0] for p in managed_processes]}", flush=True)
    print("=" * 55, flush=True)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        monitor_processes()
    except KeyboardInterrupt:
        shutdown_handler()
    except Exception as e:
        print(f"❌ Launcher error: {e}", flush=True)
        shutdown_handler()

if __name__ == "__main__":
    main()
