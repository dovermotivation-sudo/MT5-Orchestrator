#!/usr/bin/env python3
import os
import sys
import shutil

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")
    
    if load_dotenv(dotenv_path):
        print("Loaded environment configuration from .env")
    else:
        print("Warning: .env file not found. Will fall back to OS environment variables.")
        
    clients_dir = os.environ.get("CLIENTS_DIR")
    if not clients_dir:
        print("Error: CLIENTS_DIR is not defined in .env or system environment.")
        sys.exit(1)
        
    clients_dir = os.path.normpath(clients_dir)
    if not os.path.isdir(clients_dir):
        print(f"Error: Clients directory '{clients_dir}' does not exist.")
        sys.exit(1)
        
    targets = []
    for item in os.listdir(clients_dir):
        clone_path = os.path.join(clients_dir, item)
        if os.path.isdir(clone_path) and item.startswith("clone_"):
            targets.append((item, clone_path))
            
    if not targets:
        print(f"No clone directories starting with 'clone_' found in '{clients_dir}'.")
        return
        
    print(f"\nFound {len(targets)} clone directory(ies) to purge in '{clients_dir}':")
    for name, path in targets:
        print(f"  - {name} ({path})")
    print("\nWARNING: This will permanently delete all the listed folders above!")
    try:
        response = input("Are you sure you want to purge these directories? (type 'yes' to confirm): ").strip().lower()
    except KeyboardInterrupt:
        print("\nOperation aborted by user.")
        sys.exit(1)
        
    if response in ("yes", "y"):
        print("\nPurging directories...")
        deleted_count = 0
        for name, path in targets:
            try:
                shutil.rmtree(path)
                print(f"  [x] Deleted: {name}")
                deleted_count += 1
            except Exception as e:
                print(f"  [!] Failed to delete {name}: {e}")
                
        print(f"\nPurge complete. Successfully deleted {deleted_count} directory(ies).")
    else:
        print("\nOperation cancelled. No folders were deleted.")

if __name__ == "__main__":
    main()
