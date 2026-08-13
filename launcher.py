import subprocess
import sys

print("👑 =======================================")
print("👑 KING ZARRY AI MULTI-PLATFORM")
print("👑 =======================================")

print("🚀 Starting Discord...")
discord_process = subprocess.Popen(
    [sys.executable, "bot.py"]
)

print(f"✅ Discord process started (PID: {discord_process.pid})")

print("🚀 Starting Telegram...")
telegram_process = subprocess.Popen(
    [sys.executable, "telegram_bot.py"]
)

print(f"✅ Telegram process started (PID: {telegram_process.pid})")

print("📡 KING ZARRY AI IS RUNNING.")
print("👑 Discord + Telegram are active.")

discord_code = discord_process.wait()
telegram_code = telegram_process.wait()

print(f"Discord exited with code: {discord_code}")
print(f"Telegram exited with code: {telegram_code}")
