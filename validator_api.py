#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import uuid
import shutil
import time
import psutil
from flask import Flask, request, jsonify
from flask_cors import CORS
#cors added
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

script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, ".env")
load_dotenv(dotenv_path)

app = Flask(__name__)
CORS(app)

MASTER_MT5_DIR = os.environ.get("MASTER_MT5_DIR")
CLIENTS_DIR = os.environ.get("CLIENTS_DIR")
VALIDATION_TIMEOUT = int(os.environ.get("VALIDATION_TIMEOUT", 30))

def kill_processes_in_dir(target_dir):
    """Force kill any processes running from the target directory to allow clean deletion."""
    target_dir_abs = os.path.abspath(target_dir).lower()
    for proc in psutil.process_iter():
        try:
            exe = proc.exe()
            if exe and os.path.abspath(exe).lower().startswith(target_dir_abs):
                proc.kill()
                proc.wait(timeout=2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired, OSError, Exception):
            pass

def cleanup_temp_dir(temp_dir_path):
    """Clean up the temporary clone directory and all active processes running from it."""
    if not temp_dir_path or not os.path.exists(temp_dir_path):
        return
    kill_processes_in_dir(temp_dir_path)
    for _ in range(3):
        try:
            if os.path.exists(temp_dir_path):
                shutil.rmtree(temp_dir_path)
            break
        except Exception:
            time.sleep(1)
            kill_processes_in_dir(temp_dir_path)

@app.route('/', methods=['POST'])
def validate():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"valid": False, "error": "Invalid or missing JSON payload"}), 400
        
    login = data.get("loginId")
    password = data.get("password")
    server = data.get("server")
    
    if not login or not password or not server:
        return jsonify({"valid": False, "error": "Missing login, password, or server"}), 400
        
    try:
        login = int(login)
    except ValueError:
        return jsonify({"valid": False, "error": "Login must be an integer"}), 400

    if not MASTER_MT5_DIR or not CLIENTS_DIR:
        return jsonify({"valid": False, "error": "Server configuration error: MASTER_MT5_DIR or CLIENTS_DIR not set"}), 500

    validator_script = os.path.join(script_dir, "mt5_validator_task.py")
    if not os.path.exists(validator_script):
        return jsonify({"valid": False, "error": "Validator task script missing"}), 500
    
    # Generate temp clone path in API to control/cleanup if timeout or error happens
    temp_dir_name = f"validate_{login}_{uuid.uuid4().hex[:8]}"
    temp_dir_path = os.path.normpath(os.path.join(CLIENTS_DIR, temp_dir_name))
    
    p = None
    try:
        p = subprocess.Popen(
            [sys.executable, validator_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        payload = json.dumps({
            "login": login,
            "password": password,
            "server": server,
            "master_dir": MASTER_MT5_DIR,
            "clients_dir": CLIENTS_DIR,
            "temp_dir_path": temp_dir_path
        })
        
        stdout, stderr = p.communicate(input=payload, timeout=VALIDATION_TIMEOUT)
        
        if p.returncode != 0:
            return jsonify({"valid": False, "error": "Validation process failed", "details": stderr.strip()}), 500
            
        try:
            result = json.loads(stdout.strip())
            return jsonify(result)
        except json.JSONDecodeError:
            return jsonify({"valid": False, "error": "Invalid response from validator task", "details": stdout.strip()}), 500
            
    except subprocess.TimeoutExpired:
        if p:
            p.kill()
            p.wait()
        return jsonify({"valid": False, "error": "Validation timed out"}), 504
    except Exception as e:
        if p:
            p.kill()
            p.wait()
        return jsonify({"valid": False, "error": str(e)}), 500
    finally:
        cleanup_temp_dir(temp_dir_path)

if __name__ == "__main__":
    port = int(os.environ.get("VALIDATOR_PORT", 5001))
    threads = int(os.environ.get("VALIDATOR_THREADS", 4))
    
    try:
        from waitress import serve
        print(f"Starting Validator API on port {port} (Production WSGI: Waitress, Threads: {threads})...")
        serve(app, host="0.0.0.0", port=port, threads=threads)
    except ImportError:
        print(f"Waitress not installed. Starting Validator API on port {port} (Flask Dev Server)...")
        app.run(host="0.0.0.0", port=port)

