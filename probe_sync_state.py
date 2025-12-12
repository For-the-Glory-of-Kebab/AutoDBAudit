import sqlite3
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("probe")

DB_PATH = Path("output/audit_history.db")


def probe():
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get Baseline (first audit)
    cursor.execute(
        "SELECT id, started_at FROM audit_runs WHERE run_type='audit' ORDER BY started_at ASC LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        print("❌ No baseline audit found.")
        return
    baseline_id = row["id"]
    print(f"✅ Baseline Run: {baseline_id} ({row['started_at']})")

    # Get Latest
    cursor.execute(
        "SELECT id, started_at, run_type FROM audit_runs ORDER BY started_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        print("❌ No runs found.")
        return
    latest_id = row["id"]
    print(
        f"✅ Latest Run:   {latest_id} ({row['started_at']}) - Type: {row['run_type']}"
    )

    if baseline_id == latest_id:
        print("⚠️  Only baseline exists. Sync hasn't created a new run yet?")
        return

    # Count Findings
    cursor.execute(
        "SELECT COUNT(*) FROM findings WHERE audit_run_id = ?", (baseline_id,)
    )
    count_base = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM findings WHERE audit_run_id = ?", (latest_id,))
    count_latest = cursor.fetchone()[0]

    print(f"\n📊 Findings Count:")
    print(f"   Baseline: {count_base}")
    print(f"   Latest:   {count_latest}")

    # Check for DELETED items (In Baseline, Missing in Latest)
    # Using entity_key
    print(f"\n🔍 Checking for Missing Items (Potential Fixes)...")

    cursor.execute(
        "SELECT entity_key, finding_type, entity_name, status FROM findings WHERE audit_run_id = ?",
        (baseline_id,),
    )
    baseline_items = {row["entity_key"]: dict(row) for row in cursor.fetchall()}

    cursor.execute(
        "SELECT entity_key FROM findings WHERE audit_run_id = ?", (latest_id,)
    )
    latest_keys = {row["entity_key"] for row in cursor.fetchall()}

    missing_count = 0
    for key, item in baseline_items.items():
        if key not in latest_keys:
            if item["status"] in ("FAIL", "WARN"):
                print(
                    f"   ❌ MISSING (Was {item['status']}): {item['finding_type']} - {item['entity_name']}"
                )
                missing_count += 1
            else:
                # Was PASS, now gone. Not a fix, just removal.
                pass

    print(f"   Total Missing 'Bad' Items: {missing_count}")

    if missing_count > 0:
        print("\n✅ Sync logic SHOULD detect these as Fixed.")
    else:
        print("\n⚠️  No 'Bad' items are missing. Tool sees everything as still present.")

    conn.close()


if __name__ == "__main__":
    probe()
