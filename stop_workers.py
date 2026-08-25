#!/usr/bin/env python3
import os
import sys
import subprocess
import psutil

def load_dotenv(dotenv_path=".env"):
    if not os.path.exists(dotenv_path):
        return False
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                os.environ[key] = val
    return True

def kill_all_processes(clients_dir_name):
    terminated_count = 0
    my_pid = os.getpid()

    for proc in psutil.process_iter():
        try:
            pid = proc.pid
            if pid == my_pid:
                continue

            name = proc.name()
            cmdline = proc.cmdline()

            if not name or not cmdline:
                continue

            cmdline_str = " ".join(cmdline).lower()
            name_lower = name.lower()

            is_worker = ("python" in name_lower or "wine" in name_lower) and "worker.py" in cmdline_str
            is_terminal = ("terminal64.exe" in name_lower or "terminal.exe" in name_lower or "wine" in name_lower) and (clients_dir_name.lower() in cmdline_str or "clone_" in cmdline_str)

            if is_worker or is_terminal:
                proc.kill()
                if is_worker:
                    print(f"  [x] Terminated Python Worker Process (PID: {pid})")
                else:
                    print(f"  [x] Terminated Cloned MT5 Terminal Process (PID: {pid})")
                terminated_count += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError, Exception):
            pass

    return terminated_count

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")
    
    if load_dotenv(dotenv_path):
        print("Loaded environment configuration from .env")
    else:
        print("Warning: .env file not found. Falling back to OS environment variables.")
        
    clients_dir = os.environ.get("CLIENTS_DIR", "mock_clients_output")
    clients_dir_name = os.path.basename(os.path.normpath(clients_dir))
    
    print(f"\nScanning and stopping all processes matching workers or clients in '{clients_dir_name}'...")
    
    count = kill_all_processes(clients_dir_name)
        
    if count > 0:
        print(f"\nSuccessfully terminated {count} process(es).")
    else:
        print("\nNo matching running processes were found.")

if __name__ == "__main__":
    main()
