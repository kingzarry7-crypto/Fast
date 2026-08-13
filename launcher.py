import subprocess
import sys
import signal


processes = []


def start_bot(filename):
    print(f"🚀 Starting {filename}...")

    process = subprocess.Popen(
        [sys.executable, filename]
    )

    processes.append(process)

    return process


def shutdown(signum, frame):

    print("🛑 Shutting down King Zarry AI...")

    for process in processes:

        if process.poll() is None:

            process.terminate()

    sys.exit(0)


signal.signal(
    signal.SIGTERM,
    shutdown
)

signal.signal(
    signal.SIGINT,
    shutdown
)


print("👑 =======================================")
print("👑 KING ZARRY AI MULTI-PLATFORM")
print("👑 =======================================")
print("🤖 Starting Discord...")
print("📱 Starting Telegram...")


discord_process = start_bot("bot.py")
telegram_process = start_bot("telegram_bot.py")


print("✅ Discord process started.")
print("✅ Telegram process started.")
print("📡 KING ZARRY AI IS RUNNING.")


while True:

    discord_status = discord_process.poll()
    telegram_status = telegram_process.poll()

    if discord_status is not None:

        print(
            f"❌ Discord bot stopped with code "
            f"{discord_status}"
        )

    if telegram_status is not None:

        print(
            f"❌ Telegram bot stopped with code "
            f"{telegram_status}"
        )

    if (
        discord_status is not None
        and telegram_status is not None
    ):

        print("❌ Both bots have stopped.")
        sys.exit(1)

    import time

    time.sleep(10)
