import os
import signal
import sys
import subprocess
import time


# =========================================================
# 👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER
# =========================================================
# Runs FastAPI (for Vercel) + Telegram bot (with Discord in a
# thread) inside one Railway container.
# =========================================================

managed_processes = []


# =========================================================
# 🧠 MEMORY INITIALIZATION (best-effort, non-fatal)
# =========================================================

def initialize_memory():
    print("🧠 Initializing KING ZARRY AI User Memory...")

    memory_modules = [
        "king_zarry_memory",
        "user_memory",
        "memory",
    ]

    for module_name in memory_modules:
        if not os.path.exists(f"{module_name}.py"):
            continue

        try:
            mod = __import__(module_name)

            if hasattr(mod, "init_db"):
                mod.init_db()
                print(f"✅ Database initialized via {module_name}.init_db()")
                return

            if hasattr(mod, "setup"):
                mod.setup()
                print(f"✅ Database setup completed via {module_name}.setup()")
                return

        except Exception as e:
            print(f"❌ Memory initialization error in {module_name}: {e}")

    print("⚠️ No explicit memory initializer found — continuing.")


# =========================================================
# 🚀 START PROCESS
# =========================================================

def start_process(name, command):
    """
    Launch a subprocess. `command` is a list of argv tokens.
    Returns [name, command, proc] or None.
    """
    print(f"🚀 Starting {name}: {' '.join(command)}")

    try:
        proc = subprocess.Popen(
            command,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print(f"✅ {name} process started (PID: {proc.pid})")
        return [name, command, proc]

    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None


# =========================================================
# 🛑 SHUTDOWN
# =========================================================

def shutdown_handler(signum=None, frame=None):
    print("\n🛑 Shutdown signal received!")
    print("⏹️ Stopping KING ZARRY AI processes...")

    for item in managed_processes:
        if not item:
            continue

        name, command, proc = item

        if proc and proc.poll() is None:
            print(f"⏹️ Stopping {name} (PID: {proc.pid})...")
            try:
                proc.terminate()
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                print(f"⚡ Force killing {name}...")
                try:
                    proc.kill()
                    proc.wait(timeout=3)
                except Exception:
                    pass
            except Exception as e:
                print(f"⚠️ Error stopping {name}: {e}")

    print("👋 All KING ZARRY AI processes stopped.")
    sys.exit(0)


# =========================================================
# 🔄 MONITOR
# =========================================================

def monitor_processes():
    while True:
        for item in managed_processes:
            if not item:
                continue

            name, command, proc = item
            exit_code = proc.poll()

            if exit_code is None:
                continue

            print("\n" + "=" * 55)
            print(f"⚠️ {name} PROCESS STOPPED")
            print(f"💥 Exit code: {exit_code}")
            print("=" * 55)
            print(f"🔄 Restarting {name} in 10 seconds...")

            time.sleep(10)

            new_proc = start_process(name, command)
            if new_proc:
                item[2] = new_proc[2]

        time.sleep(3)


# =========================================================
# 🚀 MAIN
# =========================================================

def main():
    print("👑 =======================================")
    print("👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER")
    print("👑 =======================================")

    # -----------------------------------------------------
    # Memory
    # -----------------------------------------------------
    initialize_memory()
    print("-" * 55)

    # -----------------------------------------------------
    # FastAPI (for Vercel frontend)
    # -----------------------------------------------------
    if not os.path.exists("api.py"):
        print("❌ api.py not found — Vercel will not be able to reach the backend!")
        sys.exit(1)

    port = os.environ.get("PORT", "8000")
    print(f"🔌 FastAPI will bind to 0.0.0.0:{port}")

    api_process = start_process(
        "FastAPI",
        [
            sys.executable,
            "-u",
            "-m",
            "uvicorn",
            "api:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ],
    )
    if api_process:
        managed_processes.append(api_process)

    # Give FastAPI time to bind before bots start
    time.sleep(3)

    # -----------------------------------------------------
    # Telegram bot (bot.py also spawns Discord in a thread)
    # -----------------------------------------------------
    if os.path.exists("bot.py"):
        bot_process = start_process(
            "Telegram+Discord",
            [sys.executable, "-u", "bot.py"],
        )
        if bot_process:
            managed_processes.append(bot_process)
    else:
        print("⚠️ bot.py not found — skipping Telegram/Discord.")

    # -----------------------------------------------------
    # Check
    # -----------------------------------------------------
    if not managed_processes:
        print("❌ No processes started.")
        sys.exit(1)

    # -----------------------------------------------------
    # Online
    # -----------------------------------------------------
    print("\n" + "=" * 55)
    print("📡 KING ZARRY AI IS FULLY OPERATIONAL")
    print("🌐 FastAPI: serving Vercel")
    print("👑 Telegram + Discord: running")
    print("🔄 Process monitoring enabled")
    print("=" * 55)

    # -----------------------------------------------------
    # Signals
    # -----------------------------------------------------
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # -----------------------------------------------------
    # Monitor
    # -----------------------------------------------------
    try:
        monitor_processes()
    except KeyboardInterrupt:
        shutdown_handler()
    except SystemExit:
        shutdown_handler()
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        shutdown_handler()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
