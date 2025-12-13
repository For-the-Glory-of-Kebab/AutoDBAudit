import argparse
import sys
import re
import pyodbc
import logging
from pathlib import Path

# Add src to path so imports work
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR / "src"))

from autodbaudit.infrastructure.config_loader import ConfigLoader

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("SimulationRunner")

# Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

APP_CONFIG_DIR = ROOT_DIR / "config"
TARGETS_FILE = APP_CONFIG_DIR / "sql_targets.json"

SIMULATION_DIR = ROOT_DIR / "simulate-discrepancies"
SCRIPT_APPLY = SIMULATION_DIR / "2019+.sql"
SCRIPT_REVERT = SIMULATION_DIR / "2019+_revert.sql"

def get_connection_string(target) -> str:
    """Build connection string from SqlTarget object."""
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise RuntimeError("No ODBC driver found!")
    
    # Prefer ODBC Driver 17/18/13
    driver = drivers[0]
    for d in drivers:
        if "ODBC Driver 17" in d or "ODBC Driver 18" in d:
            driver = d
            break
            
    # Use the property from SqlTarget which handles Port vs Instance format
    # Note: target.server_instance returns "Server,Port" or "Server\Instance"
    # But wait, does ConfigLoader's SqlTarget have server_instance? 
    # Yes, lines 69-75 in config_loader.py logic I viewed.
    try:
        server_str = target.server_instance
    except AttributeError:
        # Fallback if property missing (though it shouldn't be)
        if target.port:
            server_str = f"{target.server},{target.port}"
        else:
            server_str = target.server

    conn_str = f"DRIVER={{{driver}}};SERVER={server_str};"
    
    if target.auth == 'sql' and target.username:
        # Simple/Naive handling - assumes password loaded
        conn_str += f"UID={target.username};PWD={target.password};"
    else:
        conn_str += "Trusted_Connection=yes;"
        
    conn_str += "TrustServerCertificate=yes;"
    return conn_str

def execute_batches(conn, sql_content: str):
    """Split SQL by GO and execute batches."""
    # Regex to split on GO on its own line (case insensitive)
    # Handles: \nGO\n, GO -- comment, etc.
    batches = re.split(r'(?i)^\s*GO\b.*$', sql_content, flags=re.MULTILINE)
    
    cursor = conn.cursor()
    success_count = 0
    error_count = 0
    
    for i, batch in enumerate(batches):
        clean_batch = batch.strip()
        if not clean_batch:
            continue
            
        try:
            cursor.execute(clean_batch)
            success_count += 1
        except pyodbc.Error as e:
            error_count += 1
            print(f"{RED}  [batch {i+1}] ERROR: {e}{RESET}")
            # We continue on error (simulating SSMS behavior roughly)
            
    conn.commit()
    return success_count, error_count

def run(mode: str):
    script_path = SCRIPT_REVERT if mode == "revert" else SCRIPT_APPLY
    
    print(f"{CYAN}=== Simulation Runner: {mode.upper()} ==={RESET}")
    print(f"Script: {script_path}")
    print(f"Config dir: {APP_CONFIG_DIR}")
    
    if not script_path.exists():
        print(f"{RED}Error: Script file not found: {script_path}{RESET}")
        return

    try:
        # Initializing ConfigLoader with absolute path
        loader = ConfigLoader(config_dir=str(APP_CONFIG_DIR))
        targets = loader.load_sql_targets()
    except Exception as e:
        print(f"{RED}Error loading targets: {e}{RESET}")
        return

    if not targets:
        print(f"{YELLOW}No targets found in config.{RESET}")
        return

    print(f"{YELLOW}Targets loaded: {len(targets)}{RESET}")
    for t in targets:
        print(f" - {t.server} ({t.name or t.id})")
        
    confirm = input(f"\n{YELLOW}Are you sure you want to run '{mode}' on ALL targets? (y/n): {RESET}")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    # Read SQL
    with open(script_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print(f"\n{CYAN}Starting Execution...{RESET}")
    
    for target in targets:
        if not target.enabled:
            print(f"Skipping {target.server} (disabled)...")
            continue
            
        print(f"Connecting to {target.server}... ", end="", flush=True)
        try:
            conn_str = get_connection_string(target)
            
            with pyodbc.connect(conn_str, autocommit=True) as conn:
                print(f"{GREEN}Connected.{RESET}")
                
                s, errs = execute_batches(conn, sql_content)
                if errs > 0:
                    print(f"  Result: {GREEN}{s} passed{RESET}, {RED}{errs} failed{RESET}")
                else:
                    print(f"  Result: {GREEN}Success ({s} batches){RESET}")
                    
        except Exception as e:
            print(f"{RED}FAILED{RESET}")
            print(f"  {e}")

    print(f"\n{CYAN}Done.{RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run simulation scripts")
    parser.add_argument("--mode", choices=["apply", "revert"], required=True, help="Mode: 'apply' adds discrepancies, 'revert' cleans them")
    args = parser.parse_args()
    
    run(args.mode)
