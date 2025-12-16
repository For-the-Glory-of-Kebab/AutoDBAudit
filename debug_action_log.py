import sqlite3
from pathlib import Path
import sys

# Add src to path
sys.path.append("src")
from autodbaudit.infrastructure.sqlite.store import HistoryStore


def debug_db():
    db_path = "output/audit_history.db"
    if not Path(db_path).exists():
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n=== Audit Runs ===")
    runs = cursor.execute("SELECT id, run_type, started_at FROM audit_runs").fetchall()
    for r in runs:
        print(f"Run {r['id']}: Type={r['run_type']}, Started={r['started_at']}")

    print("\n=== Action Log (All) ===")
    actions = cursor.execute("SELECT * FROM action_log").fetchall()
    if not actions:
        print("No actions found in DB!")
    else:
        for a in actions:
            print(
                f"Action {a['id']}: RunID={a['initial_run_id']}, Key={a['entity_key']}, Type={a['action_type']}, Desc={a['description'][:50]}"
            )

    conn.close()


if __name__ == "__main__":
    debug_db()
