import os
import psutil
import shutil
import time

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

def main():
    # Load env config to find CLIENTS_DIR
    script_dir = r"e:\Codes\MT5 Remote API"
    dotenv_path = os.path.join(script_dir, ".env")
    load_dotenv(dotenv_path)
    
    clients_dir = os.environ.get("CLIENTS_DIR")
    if not clients_dir:
        print("CLIENTS_DIR not found in .env, falling back to default relative path.")
        clients_dir = os.path.join(script_dir, "CLIENTS")
    
    print("Scanning for validation-related processes...")
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            pid = proc.info.get('pid')
            name = proc.info.get('name')
            exe = proc.info.get('exe')
            cmdline = proc.info.get('cmdline') or []
            
            is_validation_script = False
            for arg in cmdline:
                if 'validator_api.py' in arg or 'mt5_validator_task.py' in arg:
                    is_validation_script = True
                    break
            
            is_validation_terminal = False
            if exe:
                exe_lower = exe.lower()
                if 'terminal' in exe_lower or 'terminal64' in exe_lower:
                    if 'validate_' in exe_lower:
                        is_validation_terminal = True
            
            if is_validation_script or is_validation_terminal:
                print(f"Killing PID {pid}: {name}")
                if exe:
                    print(f"  Exe: {exe}")
                if cmdline:
                    print(f"  Cmd: {' '.join(cmdline)}")
                proc.kill()
                proc.wait(timeout=3)
                killed_count += 1
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass
            
    print(f"Process cleanup complete. Killed {killed_count} process(es).")
    
    # Clean up leftover validation directories
    print(f"Checking for leftover validation directories in {clients_dir}...")
    if os.path.exists(clients_dir):
        deleted_dirs_count = 0
        for item in os.listdir(clients_dir):
            if item.startswith("validate_"):
                dir_path = os.path.join(clients_dir, item)
                if os.path.isdir(dir_path):
                    print(f"Deleting leftover directory: {item}")
                    for _ in range(3):
                        try:
                            shutil.rmtree(dir_path)
                            deleted_dirs_count += 1
                            break
                        except Exception as e:
                            time.sleep(1)
        print(f"Directory cleanup complete. Deleted {deleted_dirs_count} directory(ies).")
    else:
        print("Clients directory does not exist or cannot be accessed.")

if __name__ == "__main__":
    main()

