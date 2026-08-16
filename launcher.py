import os
import signal
import sys
import subprocess
import time

def initialize_memory():
    """Initializes persistent memory/database prior to bot execution."""
    print("🧠 Initializing KING ZARRY AI User Memory...")
    
    # List candidate memory modules
    memory_modules = ["king_zarry_memory", "user_memory", "memory"]
    initialized = False

    for module_name in memory_modules:
        if os.path.exists(f"{module_name}.py"):
            try:
                mod = __import__(module_name)
                if hasattr(mod, "init_db"):
                    mod.init_db()
                    print(f"✅ Database initialized via {module_name}.init_db()")
                    initialized = True
                    break
                elif hasattr(mod, "setup"):
                    mod.setup()
                    print(f"✅ Database setup completed via {module_name}.setup()")
                    initialized = True
                    break
            except Exception as e:
                print(f"❌ Error initializing {module_name}: {e}")

    if not initialized:
        print("⚠️ Warning: No explicit memory pre-init found or run. Proceeding with bot launch...")

def start_process(name, script_name):
    """Starts a subprocess and returns a list of [name, script_name, process_object]."""
    print(f"🚀 Starting {name} Bot ({script_name})...")
    proc = subprocess.Popen([sys.executable, script_name])
    print(f"✅ {name} process started (PID: {proc.pid})")
    return [name, script_name, proc]

def main():
    print("👑 =======================================")
    print("👑 KING ZARRY AI MULTI-PLATFORM LAUNCHER")
    print("👑 =======================================")

    # Step 1: Initialize User Memory DB
    initialize_memory()
    print("-" * 43)

    # Step 2: Track active processes
    managed_processes = []
    
    if os.path.exists("bot.py"):
        managed_processes.append(start_process("Discord", "bot.py"))
    else:
        print("⚠️ bot.py not found. Skipping Discord bot startup.")

    if os.path.exists("telegram_bot.py"):
        managed_processes.append(start_process("Telegram", "telegram_bot.py"))
    else:
        print("⚠️ telegram_bot.py not found. Skipping Telegram bot startup.")

    if not managed_processes:
        print("❌ No bot scripts found to execute. Exiting.")
        sys.exit(1)

    print("=" * 43)
    print("📡 KING ZARRY AI IS FULLY OPERATIONAL")
    print("👑 Discord + Telegram + Persistent Memory active.")
    print("💡 Press Ctrl+C to stop all processes cleanly.")
    print("=" * 43)

    def shutdown_handler(signum, frame):
        print("\n🛑 Shutdown signal received! Terminating processes gracefully...")
        for item in managed_processes:
            name, _, proc = item
            if proc and proc.poll() is None:
                print(f"⏹️ Stopping {name} process (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"⚡ Force killing {name} process...")
                    proc.kill()
        print("👋 All KING ZARRY AI processes stopped safely.")
        sys.exit(0)

    # Register handlers for clean container stop signals
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Step 3: Monitor and Auto-Restart Loop
    while True:
        try:
            for item in managed_processes:
                name, script_name, proc = item
                exit_code = proc.poll()
                
                if exit_code is not None:
                    print(f"⚠️ {name} process exited with code: {exit_code}")
                    print(f"🔄 Restarting {name} process in 5 seconds...")
                    time.sleep(5)
                    # Restart the failed process
                    new_proc = subprocess.Popen([sys.executable, script_name])
                    item[2] = new_proc
                    print(f"✅ {name} restarted successfully (PID: {new_proc.pid})")

            time.sleep(3)
        except (KeyboardInterrupt, SystemExit):
            shutdown_handler(None, None)
        except Exception as e:
            print(f"❌ Error in launcher loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
