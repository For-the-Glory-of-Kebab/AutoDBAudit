# Diagnostic: Check ALL actions in database + raw SQL
import sys

sys.path.insert(0, "src")
from pathlib import Path
import sqlite3

db_paths = [Path("output/audit_001/audit_history.db"), Path("output/audit_history.db")]
db_path = next((p for p in db_paths if p.exists()), None)

if not db_path:
    print("No database found")
    exit(1)

print(f"DB: {db_path}")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Check all runs
runs = conn.execute("SELECT id, status FROM audit_runs ORDER BY id").fetchall()
print(f"\n=== AUDIT RUNS ===")
for r in runs:
    print(f"  Run {r['id']}: status={r['status']}")

# Check all actions (raw)
actions = conn.execute(
    """
    SELECT id, initial_run_id, sync_run_id, action_type, entity_key 
    FROM action_log
    ORDER BY id
"""
).fetchall()

print(f"\n=== ALL ACTIONS ({len(actions)}) ===")
for a in actions:
    print(
        f"  id={a['id']} init={a['initial_run_id']} sync={a['sync_run_id']} type={a['action_type']} key={a['entity_key'][:40]}"
    )

conn.close()
