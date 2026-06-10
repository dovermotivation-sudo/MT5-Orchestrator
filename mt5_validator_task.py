#!/usr/bin/env python3
import sys
import json
import os
import uuid
import shutil
import time
import psutil
import MetaTrader5 as mt5

def kill_processes_in_dir(target_dir):
    """Force kill any processes running from the target directory to allow clean deletion."""
    target_dir_abs = os.path.abspath(target_dir).lower()
    for proc in psutil.process_iter(['pid', 'exe']):
        try:
            exe = proc.info.get('exe')
            if exe and os.path.abspath(exe).lower().startswith(target_dir_abs):
                proc.kill()
                proc.wait(timeout=2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"valid": False, "error": "No input data provided"}))
            sys.exit(1)
            
        data = json.loads(input_data)
        login = data.get("login")
        password = data.get("password")
        server = data.get("server")
        master_dir = data.get("master_dir")
        clients_dir = data.get("clients_dir")
        
        if not all([login, password, server, master_dir, clients_dir]):
            print(json.dumps({"valid": False, "error": "Missing required fields in payload"}))
            sys.exit(1)
        
        temp_dir_path = data.get("temp_dir_path")
        if not temp_dir_path:
            temp_dir_name = f"validate_{login}_{uuid.uuid4().hex[:8]}"
            temp_dir_path = os.path.join(clients_dir, temp_dir_name)
        
        # 1. Clone master MT5
        try:
            try:
                shutil.copytree(master_dir, temp_dir_path, dirs_exist_ok=True)
            except TypeError:
                # Fallback for Python versions < 3.8
                for item in os.listdir(master_dir):
                    s = os.path.join(master_dir, item)
                    d = os.path.join(temp_dir_path, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
        except Exception as e:
            print(json.dumps({"valid": False, "error": f"Failed to create temporary clone: {e}"}))
            sys.exit(1)
            
        executable = None
        for name in ["terminal64.exe", "terminal.exe"]:
            p = os.path.join(temp_dir_path, name)
            if os.path.isfile(p):
                executable = p
                break
                
        if not executable:
            print(json.dumps({"valid": False, "error": "Terminal executable not found in clone"}))
            shutil.rmtree(temp_dir_path, ignore_errors=True)
            sys.exit(1)
            
        # 2. Validate credentials
        success = mt5.initialize(
            path=executable,
            login=login,
            password=password,
            server=server,
            portable=True
        )
        
        result = {"valid": False, "error": "Unknown initialization error"}
        
        if success:
            # Check connection state
            # MT5 might take a second to connect
            time.sleep(1)
            t_info = mt5.terminal_info()
            if t_info and t_info.connected:
                result = {"valid": True}
            else:
                result = {"valid": False, "error": "Invalid credentials or broker unreachable"}
        else:
            err = mt5.last_error()
            result = {"valid": False, "error": f"MT5 initialization failed: {err}"}
            
        # 3. Shutdown and cleanup
        mt5.shutdown()
        time.sleep(2)  # Give MT5 time to gracefully exit
        
        # Kill terminal to release file locks
        kill_processes_in_dir(temp_dir_path)
        
        # Delete clone (removes creds)
        time.sleep(1)
        shutil.rmtree(temp_dir_path, ignore_errors=True)
        
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({"valid": False, "error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
