import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("output/audit_history.db")


def inspect():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== Audit Runs ===")
    cursor.execute(
        "SELECT id, run_type, started_at, organization, status FROM audit_runs ORDER BY id"
    )
    runs = cursor.fetchall()
    for run in runs:
        print(
            f"Run #{run['id']}: {run['run_type'].upper()} | {run['started_at']} | Status: {run['status']}"
        )

        # Count findings for this run
        cursor.execute(
            "SELECT COUNT(*) FROM findings WHERE audit_run_id = ?", (run["id"],)
        )
        count = cursor.fetchone()[0]
        print(f"   -> {count} findings recorded.")

    print("\n=== Action Log ===")
    cursor.execute("SELECT COUNT(*) FROM action_log")
    count = cursor.fetchone()[0]
    print(f"Total entries: {count}")

    cursor.execute("SELECT action_type, COUNT(*) FROM action_log GROUP BY action_type")
    stats = cursor.fetchall()
    for stat in stats:
        print(f"   {stat[0]}: {stat[1]}")

    conn.close()


if __name__ == "__main__":
    inspect()
