#!/usr/bin/env python3
import os
import sys
import json
import time
import signal
import argparse
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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


def fetch_active_subscriptions(base_url, api_key, page=1, limit=100):
    url = f"{base_url.rstrip('/')}/api/bot/active-subscriptions?includeCredentials=true&page={page}&limit={limit}"
    req = Request(url)
    req.add_header("x-bot-api-key", api_key)
    req.add_header("Accept", "application/json")
    
    try:
        with urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"success": False, "message": body}
    except URLError as e:
        return {"success": False, "message": str(e.reason)}
    except Exception as e:
        return {"success": False, "message": str(e)}



def kill_windows_processes_for_login(login_id, clients_dir_name):
    terminated_count = 0
    login_id = str(login_id)
    
    py_cmd = f'Get-CimInstance Win32_Process | Where-Object {{ $_.Name -match "python" -and $_.CommandLine -like "*worker.py*" -and $_.CommandLine -like "*--login {login_id}*" }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }}'
    try:
        res = subprocess.run(["powershell", "-Command", py_cmd], capture_output=True, text=True, check=False)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            print(f"  [x] Terminated Python Worker Process (PID: {pid}) for Login: {login_id}")
            terminated_count += 1
    except Exception as e:
        print(f"Error terminating Windows python worker for login {login_id}: {e}")
        
    term_cmd = f'Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -like "terminal64.exe" -or $_.Name -like "terminal.exe") -and ($_.CommandLine -like "*{clients_dir_name}*" -and $_.CommandLine -like "*clone_{login_id}*") }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }}'
    try:
        res = subprocess.run(["powershell", "-Command", term_cmd], capture_output=True, text=True, check=False)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            print(f"  [x] Terminated Cloned MT5 Terminal (PID: {pid}) for Login: {login_id}")
            terminated_count += 1
    except Exception as e:
        print(f"Error terminating Windows MT5 terminal for login {login_id}: {e}")
        
    return terminated_count


def kill_unix_processes_for_login(login_id, clients_dir_name):
    terminated_count = 0
    login_id = str(login_id)
    my_pid = os.getpid()
    
    try:
        res = subprocess.run(["pgrep", "-f", f"worker.py.*--login {login_id}"], capture_output=True, text=True)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            if int(pid) != my_pid:
                subprocess.run(["kill", "-9", pid])
                print(f"  [x] Terminated Python Worker Process (PID: {pid}) for Login: {login_id}")
                terminated_count += 1
    except Exception as e:
        print(f"Error terminating Unix python worker for login {login_id}: {e}")
        
    try:
        res = subprocess.run(["pgrep", "-f", f"clone_{login_id}"], capture_output=True, text=True)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for pid in pids:
            if int(pid) != my_pid:
                cmd_res = subprocess.run(["ps", "-p", pid, "-o", "args="], capture_output=True, text=True)
                cmdline = cmd_res.stdout.strip()
                if clients_dir_name in cmdline:
                    subprocess.run(["kill", "-9", pid])
                    print(f"  [x] Terminated Cloned MT5 Process (PID: {pid}) for Login: {login_id}")
                    terminated_count += 1
    except Exception as e:
        print(f"Error terminating Unix MT5 terminal for login {login_id}: {e}")
        
    return terminated_count

def kill_processes_for_login(login_id, clients_dir_name):
    if os.name == "nt":
        return kill_windows_processes_for_login(login_id, clients_dir_name)
    else:
        return kill_unix_processes_for_login(login_id, clients_dir_name)

def global_cleanup(clients_dir_name):
    print("\nExecuting global startup cleanup of existing workers and terminals...")
    terminated_count = 0
    
    if os.name == "nt":
        py_cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.Name -match "python" -and $_.CommandLine -like "*worker.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }'
        try:
            res = subprocess.run(["powershell", "-Command", py_cmd], capture_output=True, text=True, check=False)
            pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            terminated_count += len(pids)
        except Exception:
            pass
            
        term_cmd = f'Get-CimInstance Win32_Process | Where-Object {{ ($_.Name -like "terminal64.exe" -or $_.Name -like "terminal.exe") -and ($_.CommandLine -like "*{clients_dir_name}*" -or $_.CommandLine -like "*clone_*") }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }}'
        try:
            res = subprocess.run(["powershell", "-Command", term_cmd], capture_output=True, text=True, check=False)
            pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            terminated_count += len(pids)
        except Exception:
            pass
    else:
        my_pid = os.getpid()
        try:
            res = subprocess.run(["pgrep", "-f", "worker.py"], capture_output=True, text=True)
            pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            for pid in pids:
                if int(pid) != my_pid:
                    subprocess.run(["kill", "-9", pid])
                    terminated_count += 1
        except Exception:
            pass
            
        try:
            res = subprocess.run(["pgrep", "-f", "terminal"], capture_output=True, text=True)
            pids = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            for pid in pids:
                if int(pid) != my_pid:
                    cmd_res = subprocess.run(["ps", "-p", pid, "-o", "args="], capture_output=True, text=True)
                    cmdline = cmd_res.stdout.strip()
                    if clients_dir_name in cmdline or "clone_" in cmdline:
                        subprocess.run(["kill", "-9", pid])
                        terminated_count += 1
        except Exception:
            pass
            
    if terminated_count > 0:
        print(f"Cleaned up {terminated_count} existing process(es).")
    else:
        print("No existing worker or terminal processes found.")

running_workers = {}
is_running = True

def handle_shutdown(signum, frame):
    global is_running
    print(f"\nReceived shutdown signal ({signum}). Stopping all workers...")
    is_running = False

def main():
    global is_running
    
    parser = argparse.ArgumentParser(description="Bhionex MT5 Worker Orchestrator Daemon")
    parser.add_argument("--interval", type=int, help="Override polling interval in seconds")
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    dotenv_path = os.path.join(script_dir, ".env")
    if load_dotenv(dotenv_path):
        print("Loaded environment configuration from .env")
    else:
        print("Warning: .env file not found. Will fall back to OS environment variables.")
            
    api_base = os.environ.get("API_BASE_URL", "https://api.bhionex.com")
    api_key = os.environ.get("BOT_API_KEY")
    master_mt5 = os.environ.get("MASTER_MT5_DIR")
    clients_dir = os.environ.get("CLIENTS_DIR")
    
    env_interval = os.environ.get("ORCHESTRATOR_INTERVAL")
    interval = args.interval if args.interval is not None else (int(env_interval) if env_interval else 60)
    
    if not api_key:
        print("Error: BOT_API_KEY is not defined in .env or system environment.")
        sys.exit(1)
    if not master_mt5:
        print("Error: MASTER_MT5_DIR is not defined in .env or system environment.")
        sys.exit(1)
    if not clients_dir:
        print("Error: CLIENTS_DIR is not defined in .env or system environment.")
        sys.exit(1)
            
    master_mt5 = os.path.normpath(master_mt5)
    clients_dir = os.path.normpath(clients_dir)
    clients_dir_name = os.path.basename(clients_dir)
    template_path = os.path.normpath(os.path.join(script_dir, "example.ini"))
    
    print(f"Orchestrator settings:")
    print(f"  API Base URL:      {api_base}")
    print(f"  Master MT5 Dir:    {master_mt5}")
    print(f"  Clients Dir:       {clients_dir}")
    print(f"  Sync Interval:     {interval} seconds\n")
    
    global_cleanup(clients_dir_name)
    
    print("\nOrchestrator successfully started. Entering main loop...")
    
    while is_running:
        all_users = []
        
        page = 1
        fetch_failed = False
        while True:
            res = fetch_active_subscriptions(api_base, api_key, page=page)
            if not res.get("success"):
                print(f"Error fetching active subscriptions: {res.get('message', 'Unknown API failure')}")
                fetch_failed = True
                break
            
            users = res.get("users", [])
            all_users.extend(users)
            
            pagination = res.get("pagination", {})
            total_pages = pagination.get("pages", 1)
            current_page = pagination.get("page", 1)
            
            if current_page >= total_pages or not users:
                break
            page += 1
            
        if fetch_failed:
            print("Skipping orchestration iteration due to API fetch failure.")
            time.sleep(interval)
            continue
                
        active_map = {}
        for user in all_users:
            account = user.get("mt5Account")
            if not account:
                continue
                
            login_id = str(account.get("loginId"))
            password = account.get("password")
            server = account.get("server")
            uid = user.get("userId")
            script_code = user.get("scriptCode", "SCRIPT_1")
            
            if not login_id or not password or not server or not uid:
                continue
                
            active_map[login_id] = {
                "userId": uid,
                "email": user.get("userEmail", "Unknown Email"),
                "password": password,
                "server": server,
                "scriptCode": script_code
            }
            
        for login_id, config in active_map.items():
            user_client_dir = os.path.join(clients_dir, f"clone_{login_id}")
            
            def spawn_worker(login, creds):
                abs_worker_path = os.path.abspath(os.path.join(script_dir, "worker.py"))
                abs_terminal_path = os.path.abspath(os.path.join(master_mt5, "terminal64.exe"))
                abs_client_dir = os.path.abspath(user_client_dir)
                abs_config_template = os.path.abspath(template_path)
                
                worker_cmd = [
                    sys.executable,
                    abs_worker_path,
                    "--login", str(login),
                    "--password", str(creds["password"]),
                    "--server", str(creds["server"]),
                    "--terminal-path", abs_terminal_path,
                    "--clone-dir", abs_client_dir,
                    "--api-base", api_base,
                    "--api-key", api_key,
                    "--user-id", creds["userId"],
                    "--script-code", creds["scriptCode"],
                    "--config-template", abs_config_template,
                    "--interval", "30"
                ]
                
                if os.environ.get("WORKER_EXPERT"):
                    worker_cmd.extend(["--expert", os.environ.get("WORKER_EXPERT")])
                if os.environ.get("WORKER_SYMBOL"):
                    worker_cmd.extend(["--symbol", os.environ.get("WORKER_SYMBOL")])
                if os.environ.get("WORKER_TIMEFRAME"):
                    worker_cmd.extend(["--timeframe", os.environ.get("WORKER_TIMEFRAME")])
                
                child_env = os.environ.copy()
                    
                print(f"  [+] Spawning worker for {creds['email']} (Login: {login})...")
                p = subprocess.Popen(
                    worker_cmd,
                    env=child_env,
                    cwd=script_dir,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0
                )
                return p
                
            if login_id not in running_workers:
                proc = spawn_worker(login_id, config)
                running_workers[login_id] = {
                    "process": proc,
                    "config": config
                }
            else:
                tracked = running_workers[login_id]
                proc = tracked["process"]
                tracked_config = tracked["config"]
                
                config_changed = (
                    config["password"] != tracked_config["password"] or
                    config["server"] != tracked_config["server"] or
                    config["scriptCode"] != tracked_config["scriptCode"] or
                    config["userId"] != tracked_config["userId"]
                )
                
                if config_changed:
                    print(f"  [*] Configuration changed for {config['email']} (Login: {login_id}). Restarting worker...")
                    kill_processes_for_login(login_id, clients_dir_name)
                    new_proc = spawn_worker(login_id, config)
                    running_workers[login_id] = {
                        "process": new_proc,
                        "config": config
                    }
                else:
                    if proc.poll() is not None:
                        print(f"  [!] Worker for {config['email']} (Login: {login_id}) died unexpectedly (Exit Code: {proc.returncode}). Restarting...")
                        kill_processes_for_login(login_id, clients_dir_name)
                        new_proc = spawn_worker(login_id, config)
                        running_workers[login_id]["process"] = new_proc
                        
        orphans = []
        for login_id in list(running_workers.keys()):
            if login_id not in active_map:
                orphans.append(login_id)
                
        for login_id in orphans:
            tracked = running_workers[login_id]
            email = tracked["config"]["email"]
            print(f"  [-] Subscription inactive/removed for {email} (Login: {login_id}). Stopping worker...")
            kill_processes_for_login(login_id, clients_dir_name)
            del running_workers[login_id]
            
        for _ in range(interval):
            if not is_running:
                break
            time.sleep(1)
            
    print("\nShutting down all remaining workers...")
    for login_id in list(running_workers.keys()):
        kill_processes_for_login(login_id, clients_dir_name)
        del running_workers[login_id]
        
    print("Orchestrator shutdown complete. Exiting.")

if __name__ == "__main__":
    main()
