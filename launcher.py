import os
import signal
import subprocess
import sys
import time


print("👑 =======================================")
print("👑 KING ZARRY AI MULTI-PLATFORM")
print("👑 =======================================")

processes = []


def start_process(name, script):
    print(f"🚀 Starting {name}...")

    process = subprocess.Popen(
        [sys.executable, script],
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=os.environ.copy(),
    )

    processes.append((name, process))

    print(
        f"✅ {name} process started "
        f"(PID: {process.pid})"
    )

    return process


def shutdown(signum=None, frame=None):
    print("")
    print("🛑 Shutting down King Zarry AI...")

    for name, process in processes:
        if process.poll() is None:
            print(f"🛑 Stopping {name}...")

            try:
                process.terminate()
            except Exception:
                pass

    time.sleep(2)

    for name, process in processes:
        if process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass

    print("👑 King Zarry AI stopped.")


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


try:

    discord_process = start_process(
        "Discord",
        "bot.py"
    )

    telegram_process = start_process(
        "Telegram",
        "telegram_bot.py"
    )

    print("")
    print("📡 KING ZARRY AI IS RUNNING.")
    print("👑 Discord + Telegram are active.")
    print("")

    while True:

        discord_code = discord_process.poll()
        telegram_code = telegram_process.poll()

        if discord_code is not None:

            print(
                f"❌ Discord process stopped "
                f"with exit code {discord_code}"
            )

            break

        if telegram_code is not None:

            print(
                f"❌ Telegram process stopped "
                f"with exit code {telegram_code}"
            )

            break

        time.sleep(2)


except KeyboardInterrupt:

    pass

except Exception as e:

    print(
        f"❌ Launcher error: {e}"
    )

finally:

    shutdown()
