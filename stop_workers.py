#!/usr/bin/env python3
import os
import sys
import subprocess

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

def kill_windows_processes(clients_dir_name):
    terminated_count = 0
    
    py_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.Name -match "python" -and $_.CommandLine -like "*worker.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }'
    try:
        res = subprocess.run(["powershell", "-Command", py_cmd], capture_output=True, text=True, check=True)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            print(f"  [x] Terminated Python Worker Process (PID: {pid})")
            terminated_count += 1
    except Exception as e:
        print(f"Error querying/terminating Windows python workers: {e}")
        
    term_cmd = f'Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -like "terminal64.exe" -or $_.Name -like "terminal.exe") -and ($_.CommandLine -like "*{clients_dir_name}*" -or $_.CommandLine -like "*clone_*") }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }}'
    try:
        res = subprocess.run(["powershell", "-Command", term_cmd], capture_output=True, text=True, check=True)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            print(f"  [x] Terminated Cloned MT5 Terminal Process (PID: {pid})")
            terminated_count += 1
    except Exception as e:
        print(f"Error querying/terminating Windows MT5 terminal processes: {e}")
        
    return terminated_count

def kill_unix_processes(clients_dir_name):
    terminated_count = 0
    my_pid = os.getpid()
    
    try:
        res = subprocess.run(["pgrep", "-f", "worker.py"], capture_output=True, text=True)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            if int(pid) != my_pid:
                subprocess.run(["kill", "-9", pid])
                print(f"  [x] Terminated Python Worker Process (PID: {pid})")
                terminated_count += 1
    except Exception as e:
        print(f"Error querying/terminating Unix python workers: {e}")
        
    try:
        res = subprocess.run(["pgrep", "-f", "terminal"], capture_output=True, text=True)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            if int(pid) != my_pid:
                cmd_res = subprocess.run(["ps", "-p", pid, "-o", "args="], capture_output=True, text=True)
                cmdline = cmd_res.stdout.strip()
                if clients_dir_name in cmdline or "clone_" in cmdline:
                    subprocess.run(["kill", "-9", pid])
                    print(f"  [x] Terminated Cloned MT5 Process (Wine/Terminal PID: {pid})")
                    terminated_count += 1
    except Exception as e:
        print(f"Error querying/terminating Unix terminal processes: {e}")
        
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
    
    if os.name == "nt":
        count = kill_windows_processes(clients_dir_name)
    else:
        count = kill_unix_processes(clients_dir_name)
        
    if count > 0:
        print(f"\nSuccessfully terminated {count} process(es).")
    else:
        print("\nNo matching running processes were found.")

if __name__ == "__main__":
    main()
