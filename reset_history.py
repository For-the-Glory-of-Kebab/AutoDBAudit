import sqlite3
from pathlib import Path

DB_PATH = Path("output/audit_history.db")


def reset_db():
    if not DB_PATH.exists():
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find the Baseline ID
    cursor.execute(
        "SELECT id, started_at FROM audit_runs WHERE run_type='audit' ORDER BY started_at ASC LIMIT 1"
    )
    row = cursor.fetchone()

    if not row:
        print(
            "❌ No baseline audit found. Cannot reset safely (would wipe everything)."
        )
        return

    baseline_id = row[0]
    print(f"✅ Baseline Run ID: {baseline_id} ({row[1]}) - KEEPING")

    # Delete everything else
    cursor.execute("DELETE FROM audit_runs WHERE id != ?", (baseline_id,))
    deleted_runs = cursor.rowcount
    print(f"🗑️  Deleted {deleted_runs} subsequent audit/sync runs.")

    # Clean up orphaned findings (findings belonging to deleted runs)
    cursor.execute("DELETE FROM findings WHERE audit_run_id != ?", (baseline_id,))
    deleted_findings = cursor.rowcount
    print(f"🗑️  Deleted {deleted_findings} orphaned finding records.")

    # Delete all instances linked to deleted runs?
    # NO: run_instances table does not exist in V2 schema.
    # Instances are persistent entity records. We leave them.
    pass

    # TRUNCATE Action Log (Start fresh)
    cursor.execute("DELETE FROM action_log")
    print("🗑️  Cleared Action Log (0 entries).")

    conn.commit()
    conn.close()

    print("\n✨ History Reset Complete. Ready for a fresh Sync.")


if __name__ == "__main__":
    reset_db()
