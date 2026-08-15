import subprocess
import sys
import os
import signal
import time

def initialize_memory():
    """Initializes persistent memory/database prior to bot execution."""
    print("🧠 Initializing KING ZARRY AI User Memory...")
    try:
        # Check if user_memory.py exists in the directory
        if os.path.exists("user_memory.py"):
            # Import and execute memory setup/initialization dynamically
            import user_memory
            if hasattr(user_memory, "init_db"):
                user_memory.init_db()
                print("✅ Database memory initialized successfully.")
            elif hasattr(user_memory, "setup"):
                user_memory.setup()
                print("✅ User memory setup completed.")
            else:
                print("✅ user_memory module loaded successfully.")
        else:
            print("⚠️ Warning: user_memory.py not found. Proceeding without explicit pre-init...")
    except Exception as e:
        print(f"❌ Error initializing user memory: {e}")
        print("⚠️ Proceeding with bot launch, but memory features may fail if DB is uninitialized.")

def main():
    print("👑 =======================================")
    print("👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER")
    print("👑 =======================================")

    # Step 1: Initialize User Memory DB
    initialize_memory()
    print("-" * 43)

    processes = []

    try:
        # Step 2: Start Discord Bot
        print("🚀 Starting Discord Bot (bot.py)...")
        discord_process = subprocess.Popen(
            [sys.executable, "bot.py"]
        )
        processes.append(("Discord", discord_process))
        print(f"✅ Discord process started (PID: {discord_process.pid})")

        # Step 3: Start Telegram Bot
        print("🚀 Starting Telegram Bot (telegram_bot.py)...")
        telegram_process = subprocess.Popen(
            [sys.executable, "telegram_bot.py"]
        )
        processes.append(("Telegram", telegram_process))
        print(f"✅ Telegram process started (PID: {telegram_process.pid})")

        print("=" * 43)
        print("📡 KING ZARRY AI IS FULLY OPERATIONAL")
        print("👑 Discord + Telegram + Persistent Memory active.")
        print("💡 Press Ctrl+C to stop all processes cleanly.")
        print("=" * 43)

        # Monitor processes while running
        while True:
            for name, proc in processes:
                poll = proc.poll()
                if poll is not None:
                    print(f"⚠️ {name} process exited unexpectedly with code: {poll}")
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received! Terminating processes gracefully...")
        for name, proc in processes:
            if proc.poll() is None:
                print(f"⏹️ Stopping {name} process (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"⚡ Force killing {name} process...")
                    proc.kill()
        print("👋 All KING ZARRY AI processes stopped safely.")
        sys.exit(0)

if __name__ == "__main__":
    main()
