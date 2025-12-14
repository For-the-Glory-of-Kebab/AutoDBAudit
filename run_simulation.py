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
SCRIPT_2019_APPLY = SIMULATION_DIR / "2019+.sql"
SCRIPT_2019_REVERT = SIMULATION_DIR / "2019+_revert.sql"
SCRIPT_2008_APPLY = SIMULATION_DIR / "2008.sql"
SCRIPT_2008_REVERT = SIMULATION_DIR / "2008_revert.sql"

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
        conn_str += f"UID={target.username};PWD={target.password};"
    else:
        conn_str += "Trusted_Connection=yes;"
        
    conn_str += "TrustServerCertificate=yes;"
    return conn_str

def execute_batches(conn, sql_content: str):
    """Split SQL by GO and execute batches."""
    # Regex to split on GO on its own line (case insensitive)
    # Handles: \nGO\n, GO -- comment, etc.
    # If no GO, it returns the whole string as one item
    batches = re.split(r'(?i)^\s*GO\b.*$', sql_content, flags=re.MULTILINE)
    
    cursor = conn.cursor()
    success_count = 0
    error_count = 0
    
    for i, batch in enumerate(batches):
        clean_batch = batch.strip()
        if not clean_batch:
            continue
            
        try:
            # explicit NOCOUNT + NEWLINE to ensure clean execution context
            # pyodbc sometimes struggles if the batch starts with comments
            cursor.execute(clean_batch)
            
            # Consume all results to ensure the batch is fully processed
            # This is critical for scripts with multiple PRINT statements or Result Sets
            while cursor.nextset(): 
                pass
                
            success_count += 1
        except pyodbc.Error as e:
            error_count += 1
            print(f"{RED}  [batch {i+1}] ERROR: {e}{RESET}")
            
    # Autocommit is on, no need to commit
    return success_count, error_count

def detect_version_and_get_script(conn, mode: str) -> Path:
    """Detect SQL version and return appropriate script path."""
    cursor = conn.cursor()
    cursor.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50))")
    version_str = cursor.fetchone()[0]
    
    # Format: 10.50.4000 (2008 R2), 15.0.2000 (2019)
    major_version = int(version_str.split('.')[0])
    
    print(f"  Detected SQL Version: {version_str} (Major: {major_version})")
    
    # Threshold: SQL 2012 (11.0) is the cut-off. 
    # Use 2008 scripts for < 11. Use 2019+ for >= 11.
    if major_version < 11:
        script = SCRIPT_2008_REVERT if mode == "revert" else SCRIPT_2008_APPLY
        print(f"  Using 2008 script: {script.name}")
    else:
        script = SCRIPT_2019_REVERT if mode == "revert" else SCRIPT_2019_APPLY
        print(f"  Using 2019+ script: {script.name}")
        
    return script

def run(mode: str, limit_targets: list[str] = None, run_all: bool = False):
    print(f"{CYAN}=== Simulation Runner: {mode.upper()} ==={RESET}")
    
    try:
        loader = ConfigLoader(config_dir=str(APP_CONFIG_DIR))
        targets = loader.load_sql_targets()
    except Exception as e:
        print(f"{RED}Error loading targets: {e}{RESET}")
        return

    if not targets:
        print(f"{YELLOW}No targets found in config.{RESET}")
        return

    selected_targets = []

    # If no selection made via args, enter interactive mode
    if not limit_targets and not run_all:
        # display targets with indices ONLY in interactive mode
        print(f"\n{CYAN}{'#':<4} | {'SERVER':<30} | {'NAME / ID':<20}{RESET}")
        print(f"{CYAN}{'-'*60}{RESET}")
        for i, t in enumerate(targets):
            label = t.name or t.id or ""
            print(f" {i+1:<3} | {t.server:<30} | {label:<20}")

        try:
            print(f"\n{YELLOW}Select targets (e.g. '1 2'), 'all', or 'q' to quit.{RESET}")
            selected_indices = input(f"{YELLOW}> {RESET}").strip()
        except KeyboardInterrupt:
            print("\nCancelled.")
            return

        if selected_indices.lower() in ('q', 'quit', 'exit'):
            print("Cancelled.")
            return
            
        if selected_indices.lower() == 'all':
            run_all = True
            selected_targets = targets
        elif not selected_indices:
            print("Cancelled.")
            return
        else:
            limit_targets = selected_indices.split()

    if run_all:
        if not selected_targets: # if not set above by interactive mode
            selected_targets = targets
        print(f"{YELLOW}selected: ALL ({len(targets)}){RESET}")
    elif limit_targets:
        for val in limit_targets:
            # Check for 1-based index
            if val.isdigit():
                idx = int(val) - 1
                if 0 <= idx < len(targets):
                    if targets[idx] not in selected_targets:
                        selected_targets.append(targets[idx])
                    continue
            
            # Fuzzy string match
            val_lower = val.lower()
            matched_any = False
            for t in targets:
                if (val_lower in t.server.lower() or 
                    val_lower == str(t.name).lower() or 
                    val_lower == str(t.id).lower()):
                    if t not in selected_targets:
                        selected_targets.append(t)
                    matched_any = True
            
            if not matched_any and not val.isdigit():
                print(f"{RED}Warning: No match for '{val}'{RESET}")

    if not selected_targets:
        print(f"\n{RED}Error: No targets selected.{RESET}")
        return

    print(f"\n{YELLOW}Targets to run: {len(selected_targets)}{RESET}")
    for t in selected_targets:
        print(f" - {t.server} ({t.name or t.id})")
        
    confirm = input(f"\n{YELLOW}Are you sure you want to run '{mode}' on these {len(selected_targets)} targets? (y/n): {RESET}")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    print(f"\n{CYAN}Starting Execution...{RESET}")
    
    for target in selected_targets:
        if not target.enabled:
            print(f"Skipping {target.server} (disabled)...")
            continue
            
        print(f"Connecting to {target.server}... ", end="", flush=True)
        try:
            conn_str = get_connection_string(target)
            
            with pyodbc.connect(conn_str, autocommit=True) as conn:
                print(f"{GREEN}Connected.{RESET}")
                
                # Dynamic Logic
                script_path = detect_version_and_get_script(conn, mode)
                
                if not script_path.exists():
                     print(f"{RED}  Error: Script not found: {script_path}{RESET}")
                     continue
                     
                with open(script_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()

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
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--targets", nargs='+', help="List of target indices (1 2) or names to run against")
    group.add_argument("--all", action="store_true", help="Run on ALL targets")
    
    args = parser.parse_args()
    
    run(args.mode, args.targets, args.all)
