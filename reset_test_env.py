import sqlite3
import shutil
import logging
from pathlib import Path

# Setup simple logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("reset")

OUTPUT_DIR = Path("output")
DB_PATH = OUTPUT_DIR / "audit_history.db"


def reset_files():
    print("\n🧹 Cleaning Artifacts...")

    # 1. Delete root Sync Folders (Legacy: Run_X_Sync)
    for p in OUTPUT_DIR.glob("Run_*_Sync"):
        if p.is_dir():
            try:
                shutil.rmtree(p)
                print(f"   🗑️  Deleted folder: {p.name}")
            except Exception as e:
                print(f"   ⚠️  Could not delete {p.name}: {e}")

    # 2. Delete root Sync Files (sql_audit_sync_*.xlsx)
    for p in OUTPUT_DIR.glob("sql_audit_sync_*.xlsx"):
        try:
            p.unlink()
            print(f"   🗑️  Deleted file: {p.name}")
        except Exception as e:
            print(f"   ⚠️  Could not delete {p.name}: {e}")

    # 3. Delete Audit_Latest.xlsx (Working Copy)
    latest = OUTPUT_DIR / "Audit_Latest.xlsx"
    if latest.exists():
        try:
            latest.unlink()
            print(f"   🗑️  Deleted file: {latest.name}")
        except Exception as e:
            print(f"   ⚠️  Could not delete {latest.name}: {e}")

    # 4. Delete nested Sync Folders (New Hierarchy: output/audit_*/runs/run_*_sync)
    # Search for audit folders
    for audit_dir in OUTPUT_DIR.glob("audit_*"):
        if audit_dir.is_dir():
            runs_dir = audit_dir / "runs"
            if runs_dir.exists():
                for run_dir in runs_dir.glob("run_*_sync"):
                    if run_dir.is_dir():
                        try:
                            shutil.rmtree(run_dir)
                            print(
                                f"   🗑️  Deleted nested sync folder: {audit_dir.name}/runs/{run_dir.name}"
                            )
                        except Exception as e:
                            print(f"   ⚠️  Could not delete {run_dir.name}: {e}")


def reset_db():
    print("\n🧹 Cleaning Database...")
    if not DB_PATH.exists():
        print("   ❌ Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find Baseline
    cursor.execute(
        "SELECT id, started_at FROM audit_runs WHERE run_type='audit' ORDER BY started_at ASC LIMIT 1"
    )
    row = cursor.fetchone()

    if not row:
        print("   ⚠️  No baseline audit found. Nothing to reset.")
        conn.close()
        return

    baseline_id = row[0]
    print(f"   ✅ Keeping Baseline Run: #{baseline_id} ({row[1]})")

    # Delete non-baseline runs
    cursor.execute("DELETE FROM audit_runs WHERE id != ?", (baseline_id,))
    del_runs = cursor.rowcount
    print(f"   🗑️  Deleted {del_runs} extra runs.")

    # Delete orphaned findings
    cursor.execute("DELETE FROM findings WHERE audit_run_id != ?", (baseline_id,))
    del_findings = cursor.rowcount
    print(f"   🗑️  Deleted {del_findings} extra findings.")

    # Clear Action Log
    cursor.execute("DELETE FROM action_log")
    print(f"   🗑️  Cleared Action Log.")

    # RESET AUTOINCREMENT SEQUENCES
    # This ensures the next run is Run #2 (MAX_ID + 1), not Run #11
    tables_to_reset = ["audit_runs", "findings", "action_log"]
    for table in tables_to_reset:
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
            print(f"   🔄 Reset sequence for table: {table}")
        except sqlite3.OperationalError:
            print(f"   ⚠️  Could not reset sequence for {table} (Table missing?)")

    conn.commit()
    conn.close()


def main():
    print("=" * 60)
    print("RESETTING TEST ENVIRONMENT")
    print("=" * 60)

    reset_files()
    reset_db()

    print("\n" + "=" * 60)
    print("✅ RESET COMPLETE")
    print("You are now ready to run: python main.py --sync")
    print("=" * 60)


if __name__ == "__main__":
    main()
