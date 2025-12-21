# Clean duplicate actions from database
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

# Count before
before = conn.execute("SELECT COUNT(*) FROM action_log").fetchone()[0]
print(f"Actions before cleanup: {before}")

# Delete all actions to start fresh (we'll regenerate on next sync)
conn.execute("DELETE FROM action_log")
conn.commit()

# Count after
after = conn.execute("SELECT COUNT(*) FROM action_log").fetchone()[0]
print(f"Actions after cleanup: {after}")

conn.close()
print("Done - action_log cleaned. Run --sync to regenerate actions.")
