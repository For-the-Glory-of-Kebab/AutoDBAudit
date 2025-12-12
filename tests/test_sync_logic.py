"""
Test SyncService logic using a temporary SQLite database.
"""

import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from autodbaudit.infrastructure.history_store import HistoryStore
from autodbaudit.application.sync_service import SyncService
from autodbaudit.infrastructure.sqlite.schema import initialize_schema_v2, save_finding


class TestSyncService(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # Initialize schema
        conn = sqlite3.connect(self.db_path)
        initialize_schema_v2(conn)
        conn.close()

        self.service = SyncService(db_path=self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def create_run(self, run_type="audit"):
        """Helper to create a run."""
        cursor = self.conn.execute(
            "INSERT INTO audit_runs (started_at, status, run_type, config_checksum) VALUES (?, ?, ?, ?)",
            (datetime.now(), "completed", run_type, "abc"),
        )
        self.conn.commit()
        return cursor.lastrowid

    def test_sync_logic(self):
        print("\nTesting SyncService Logic...")

        # 1. Create Baseline Run (Run 1)
        run1_id = self.create_run("audit")
        print(f"  Created Baseline Run #{run1_id}")

        # Add findings to Run 1
        # Finding A: Config - FAIL
        save_finding(
            self.conn,
            run1_id,
            "SRV1",
            "INST1",
            "Config",
            "xp_cmdshell",
            "FAIL",
            "Enabled",
            "Should be disabled",
        )
        # Finding B: Login - FAIL
        save_finding(
            self.conn,
            run1_id,
            "SRV1",
            "INST1",
            "Login",
            "sa_check",
            "FAIL",
            "Enabled",
            "Should be disabled",
        )
        self.conn.commit()

        # 2. Create Current Run (Run 2) - representing a re-audit
        run2_id = self.create_run("sync")
        print(f"  Created Sync Run #{run2_id}")

        # Add findings to Run 2
        # Finding A: Config - PASS (FIXED)
        save_finding(
            self.conn,
            run2_id,
            "SRV1",
            "INST1",
            "Config",
            "xp_cmdshell",
            "PASS",
            "Disabled",
            "OK",
        )
        # Finding B: Login - FAIL (STILL FAILING)
        save_finding(
            self.conn,
            run2_id,
            "SRV1",
            "INST1",
            "Login",
            "sa_check",
            "FAIL",
            "Enabled",
            "Should be disabled",
        )
        # Finding C: Backup - FAIL (NEW)
        save_finding(
            self.conn,
            run2_id,
            "SRV1",
            "INST1",
            "Backup",
            "NoBackup",
            "FAIL",
            "Never",
            "Backup required",
        )
        self.conn.commit()

        # 3. Run Sync Logic
        # We manually call _update_action_log since we mocked the runs
        print("  Running update_action_log...")
        counts = self.service._update_action_log(self.conn, run1_id, run2_id)

        print(f"  Counts: {counts}")

        # 4. Verify Counts
        self.assertEqual(counts["fixed"], 1, "Should have 1 fixed")
        self.assertEqual(counts["still_failing"], 1, "Should have 1 still failing")
        self.assertEqual(counts["new"], 1, "Should have 1 new")

        # 5. Verify DB Records
        actions = self.conn.execute("SELECT * FROM action_log").fetchall()
        for a in actions:
            print(f"  Log: {a['finding_type']} -> {a['action_type']}")

        # Verify specific entries
        fixed = next(a for a in actions if a["finding_type"] == "Config")
        self.assertEqual(fixed["action_type"], "fixed")

        still = next(a for a in actions if a["finding_type"] == "Login")
        self.assertEqual(still["action_type"], "still_failing")

        new_item = next(a for a in actions if a["finding_type"] == "Backup")
        self.assertEqual(new_item["action_type"], "new")

        print("✅ Sync logic verified successfully")


if __name__ == "__main__":
    unittest.main()
