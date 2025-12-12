"""
Simulation tool for E2E testing.
Downgrades instance versions in the SQLite history database to simulate an "old" state.
When the audit is run again, it will detect the real (newer) version, simulating an upgrade.
"""

import sqlite3
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Simulate an older version of SQL Server in the history DB."
    )
    parser.add_argument(
        "--db-path",
        default="output/audit_history.db",
        help="Path to SQLite DB (default: output/audit_history.db)",
    )
    parser.add_argument(
        "--downgrade",
        action="store_true",
        help="Apply downgrade changes (dry-run by default)",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Run an audit first: python main.py --audit")
        return

    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='instances'"
        )
        if not cursor.fetchone():
            print("Error: 'instances' table not found in database.")
            return

        print("\nChecking instances...")
        cursor.execute(
            "SELECT id, instance_name, version, product_level, edition FROM instances"
        )
        rows = cursor.fetchall()

        updates = []
        for row in rows:
            inst_id = row["id"]
            name = row["instance_name"] or "(Default)"
            ver = row["version"]
            level = row["product_level"]
            edition = row["edition"] or ""

            # Skip if version is empty
            if not ver:
                continue

            # Exclusion logic: Don't touch 2008
            if "2008" in str(edition) or ver.startswith("10.") or "BigBad2008" in name:
                print(f"  Existing: {name} (v{ver}) - Skipped (SQL 2008/Legacy)")
                continue

            # Simulate Downgrade
            # If it's already the "fake" version, maybe skip? No, enforce it.

            # FAKE STATE: SQL Server 2017 RTM
            fake_ver = "14.0.1000.169"
            fake_level = "RTM"
            fake_major = 14

            # If current version is already older than that, don't upgrade it!
            # Just blindly set it for the test if it's not 2008.

            msg = f"  Target:   {name} (v{ver} {level}) -> v{fake_ver} ({fake_level})"
            print(msg)
            updates.append((fake_ver, fake_level, fake_major, inst_id))

        if not updates:
            print("\nNo suitable instances found to downgrade.")
        else:
            print(f"\nFound {len(updates)} instances to downgrade.")

            if args.downgrade:
                cursor.executemany(
                    "UPDATE instances SET version=?, product_level=?, version_major=? WHERE id=?",
                    updates,
                )
                conn.commit()
                print(f"✅ Successfully downgraded {len(updates)} instances.")
                print(
                    "   Run 'python main.py --sync' now to simulate an upgrade detection!"
                )
            else:
                print("   [DRY RUN] No changes applied.")
                print("   Run with --downgrade to apply these changes.")

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
