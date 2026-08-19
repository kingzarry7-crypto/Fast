import os
import signal
import sys
import subprocess
import time


# =========================================================
# 👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER
# =========================================================

managed_processes = []


# =========================================================
# 🧠 MEMORY INITIALIZATION
# =========================================================

def initialize_memory():
    """Initialize persistent memory/database before bots start."""

    print("🧠 Initializing KING ZARRY AI User Memory...")

    memory_modules = [
        "king_zarry_memory",
        "user_memory",
        "memory",
    ]

    initialized = False

    for module_name in memory_modules:

        if not os.path.exists(f"{module_name}.py"):
            continue

        try:
            mod = __import__(module_name)

            if hasattr(mod, "init_db"):
                mod.init_db()

                print(
                    f"✅ Database initialized via "
                    f"{module_name}.init_db()"
                )

                initialized = True
                break

            if hasattr(mod, "setup"):
                mod.setup()

                print(
                    f"✅ Database setup completed via "
                    f"{module_name}.setup()"
                )

                initialized = True
                break

        except Exception as e:

            print(
                f"❌ Memory initialization error "
                f"in {module_name}: {e}"
            )

    if not initialized:

        print(
            "⚠️ No explicit memory initializer found."
        )

        print(
            "➡️ Continuing with bot startup..."
        )


# =========================================================
# 🚀 START PROCESS
# =========================================================

def start_process(name, script_name):

    print(
        f"🚀 Starting {name} Bot ({script_name})..."
    )

    if not os.path.exists(script_name):

        print(
            f"❌ {script_name} does not exist."
        )

        return None

    try:

        proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                script_name,
            ]
        )

        print(
            f"✅ {name} process started "
            f"(PID: {proc.pid})"
        )

        return [
            name,
            script_name,
            proc,
        ]

    except Exception as e:

        print(
            f"❌ Failed to start {name}: {e}"
        )

        return None


# =========================================================
# 🛑 SHUTDOWN
# =========================================================

def shutdown_handler(signum=None, frame=None):

    print(
        "\n🛑 Shutdown signal received!"
    )

    print(
        "⏹️ Stopping KING ZARRY AI processes..."
    )

    for item in managed_processes:

        if not item:
            continue

        name, script_name, proc = item

        if proc and proc.poll() is None:

            print(
                f"⏹️ Stopping {name} "
                f"(PID: {proc.pid})..."
            )

            try:

                proc.terminate()

                proc.wait(timeout=8)

            except subprocess.TimeoutExpired:

                print(
                    f"⚡ Force killing {name}..."
                )

                try:
                    proc.kill()
                    proc.wait(timeout=3)
                except Exception:
                    pass

            except Exception as e:

                print(
                    f"⚠️ Error stopping {name}: {e}"
                )

    print(
        "👋 All KING ZARRY AI processes stopped."
    )

    sys.exit(0)


# =========================================================
# 🔄 MONITOR
# =========================================================

def monitor_processes():

    while True:

        for item in managed_processes:

            if not item:
                continue

            name, script_name, proc = item

            exit_code = proc.poll()

            if exit_code is None:
                continue

            print(
                "\n" +
                "=" * 55
            )

            print(
                f"⚠️ {name} PROCESS STOPPED"
            )

            print(
                f"📄 Script: {script_name}"
            )

            print(
                f"💥 Exit code: {exit_code}"
            )

            print(
                "=" * 55
            )

            print(
                f"🔄 Restarting {name} in 10 seconds..."
            )

            time.sleep(10)

            new_proc = start_process(
                name,
                script_name
            )

            if new_proc:

                item[2] = new_proc[2]

        time.sleep(3)


# =========================================================
# 🚀 MAIN
# =========================================================

def main():

    print(
        "👑 ======================================="
    )

    print(
        "👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER"
    )

    print(
        "👑 ======================================="
    )

    # -----------------------------------------------------
    # Memory
    # -----------------------------------------------------

    initialize_memory()

    print("-" * 55)

    # -----------------------------------------------------
    # Discord
    # -----------------------------------------------------

    if os.path.exists("bot.py"):

        discord_process = start_process(
            "Discord",
            "bot.py"
        )

        if discord_process:
            managed_processes.append(
                discord_process
            )

    else:

        print(
            "⚠️ bot.py not found. "
            "Skipping Discord."
        )

    # -----------------------------------------------------
    # Telegram
    # -----------------------------------------------------

    if os.path.exists("telegram_bot.py"):

        telegram_process = start_process(
            "Telegram",
            "telegram_bot.py"
        )

        if telegram_process:
            managed_processes.append(
                telegram_process
            )

    else:

        print(
            "⚠️ telegram_bot.py not found. "
            "Skipping Telegram."
        )

    # -----------------------------------------------------
    # Check
    # -----------------------------------------------------

    if not managed_processes:

        print(
            "❌ No bot processes started."
        )

        sys.exit(1)

    # -----------------------------------------------------
    # Online
    # -----------------------------------------------------

    print(
        "\n" + "=" * 55
    )

    print(
        "📡 KING ZARRY AI IS FULLY OPERATIONAL"
    )

    print(
        "👑 Discord + Telegram + Persistent Memory"
    )

    print(
        "🔄 Process monitoring enabled"
    )

    print(
        "=" * 55
    )

    # -----------------------------------------------------
    # Signals
    # -----------------------------------------------------

    signal.signal(
        signal.SIGINT,
        shutdown_handler
    )

    signal.signal(
        signal.SIGTERM,
        shutdown_handler
    )

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

        print(
            f"❌ Launcher error: {e}"
        )

        shutdown_handler()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
