"""
Test SyncService diff and action logic using a temporary SQLite database.

Tests the modular sync architecture:
- diff/findings_diff.py - Compares findings
- actions/action_detector.py - Detects changes
- actions/action_recorder.py - Records with deduplication
"""

import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from autodbaudit.infrastructure.sqlite import HistoryStore, initialize_schema_v2
from autodbaudit.infrastructure.sqlite.schema import save_finding, build_entity_key
from autodbaudit.application.diff.findings_diff import diff_findings, get_exception_keys
from autodbaudit.application.actions.action_detector import (
    detect_all_actions,
    consolidate_actions,
)
from autodbaudit.application.actions.action_recorder import ActionRecorder
from autodbaudit.domain.change_types import ChangeType, RiskLevel, DetectedChange


class TestSyncLogic(unittest.TestCase):
    """Test the modular sync logic components."""

    def setUp(self):
        # Create temp DB
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        # Initialize store (creates base tables)
        self.store = HistoryStore(self.db_path)
        self.store.initialize_schema()

        # Also add V2 tables (findings, etc.)
        conn = self.store._get_connection()
        initialize_schema_v2(conn)

        # Get connection for test operations
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        if self.store._connection:
            self.store._connection.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def _create_run(self, run_type="audit"):
        """Helper to create a run."""
        cursor = self.conn.execute(
            "INSERT INTO audit_runs (started_at, status, run_type, config_hash) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), "completed", run_type, "abc"),
        )
        self.conn.commit()
        return cursor.lastrowid

    def _create_server_instance(self, hostname="SRV1", instance_name="INST1"):
        """Helper to create server and instance records."""
        # Create server
        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO servers (hostname, ip_address) VALUES (?, ?)",
            (hostname, "192.168.1.1"),
        )
        self.conn.commit()
        server_id = (
            cursor.lastrowid
            or self.conn.execute(
                "SELECT id FROM servers WHERE hostname = ?", (hostname,)
            ).fetchone()[0]
        )

        # Create instance
        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO instances (server_id, instance_name, version, version_major) VALUES (?, ?, ?, ?)",
            (server_id, instance_name, "15.0.4123.1", 15),
        )
        self.conn.commit()
        instance_id = (
            cursor.lastrowid
            or self.conn.execute(
                "SELECT id FROM instances WHERE server_id = ? AND instance_name = ?",
                (server_id, instance_name),
            ).fetchone()[0]
        )

        return server_id, instance_id

    def test_findings_diff_basic(self):
        """Test basic findings diff: fixed, still_failing, new."""
        print("\nTesting Findings Diff...")

        # Setup server/instance
        _, instance_id = self._create_server_instance()

        # 1. Create Baseline Run (Run 1)
        run1_id = self._create_run("audit")
        print(f"  Created Baseline Run #{run1_id}")

        # Add findings to Run 1
        save_finding(
            self.conn,
            run1_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "xp_cmdshell"),
            "Config",
            "xp_cmdshell",
            "FAIL",
            "high",
            "Should be disabled",
        )
        save_finding(
            self.conn,
            run1_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "sa_check"),
            "Login",
            "sa_check",
            "FAIL",
            "critical",
            "SA should be disabled",
        )
        self.conn.commit()

        # 2. Create Sync Run (Run 2)
        run2_id = self._create_run("sync")
        print(f"  Created Sync Run #{run2_id}")

        # Finding A: Config - PASS (FIXED)
        save_finding(
            self.conn,
            run2_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "xp_cmdshell"),
            "Config",
            "xp_cmdshell",
            "PASS",
            None,
            "Disabled",
        )
        # Finding B: Login - FAIL (STILL FAILING)
        save_finding(
            self.conn,
            run2_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "sa_check"),
            "Login",
            "sa_check",
            "FAIL",
            "critical",
            "SA still enabled",
        )
        # Finding C: Backup - FAIL (NEW)
        save_finding(
            self.conn,
            run2_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "backup_missing"),
            "Backup",
            "backup_missing",
            "FAIL",
            "high",
            "No backup found",
        )
        self.conn.commit()

        # 3. Get findings from store
        old_findings = self.store.get_findings(run1_id)
        new_findings = self.store.get_findings(run2_id)

        # All instances are valid
        valid_instances = {"srv1|inst1"}

        # 4. Run diff
        diff_result = diff_findings(
            old_findings=old_findings,
            new_findings=new_findings,
            old_exceptions=set(),
            new_exceptions=set(),
            valid_instance_keys=valid_instances,
        )

        print(
            f"  Diff: fixed={len(diff_result.fixed)}, new={len(diff_result.new_issues)}, still_failing={diff_result.still_failing_count}"
        )

        # 5. Verify
        self.assertEqual(len(diff_result.fixed), 1, "Should have 1 fixed")
        self.assertEqual(
            diff_result.still_failing_count, 1, "Should have 1 still failing"
        )
        self.assertEqual(len(diff_result.new_issues), 1, "Should have 1 new")

        print("✅ Findings diff verified")

    def test_action_recorder_deduplication(self):
        """Test that actions are not duplicated on repeated syncs."""
        print("\nTesting Action Recorder Deduplication...")

        run1_id = self._create_run("audit")
        run2_id = self._create_run("sync")

        from autodbaudit.domain.change_types import EntityType

        action = DetectedChange(
            entity_type=EntityType.CONFIGURATION,
            entity_key="Config|SRV1|INST1|xp_cmdshell",
            change_type=ChangeType.FIXED,
            description="xp_cmdshell disabled",
            risk_level=RiskLevel.MEDIUM,
        )

        recorder = ActionRecorder(self.store)

        # Record first time
        count1 = recorder.record_actions([action], run1_id, run2_id)
        print(f"  First record: {count1} actions")

        # Record same action again (same sync_run_id)
        count2 = recorder.record_actions([action], run1_id, run2_id)
        print(f"  Second record (same sync): {count2} actions")

        # Verify only one action in DB
        actions = self.conn.execute("SELECT * FROM action_log").fetchall()
        self.assertEqual(len(actions), 1, "Should have exactly 1 action")

        print("✅ Deduplication verified")

    def test_multi_sync_stability(self):
        """Test that running sync multiple times keeps counts stable."""
        print("\nTesting Multi-Sync Stability...")

        _, instance_id = self._create_server_instance()

        # Baseline
        run1_id = self._create_run("audit")
        save_finding(
            self.conn,
            run1_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "test"),
            "Config",
            "test",
            "FAIL",
            "high",
            "Test fail",
        )
        self.conn.commit()

        # Sync 1
        run2_id = self._create_run("sync")
        save_finding(
            self.conn,
            run2_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "test"),
            "Config",
            "test",
            "FAIL",
            "high",
            "Test fail",
        )
        self.conn.commit()

        # Sync 2 - same state
        run3_id = self._create_run("sync")
        save_finding(
            self.conn,
            run3_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "test"),
            "Config",
            "test",
            "FAIL",
            "high",
            "Test fail",
        )
        self.conn.commit()

        # All syncs should show same item as still_failing, no duplicates
        valid = {"srv1|inst1"}

        diff1 = diff_findings(
            self.store.get_findings(run1_id),
            self.store.get_findings(run2_id),
            set(),
            set(),
            valid,
        )
        diff2 = diff_findings(
            self.store.get_findings(run1_id),
            self.store.get_findings(run3_id),
            set(),
            set(),
            valid,
        )

        self.assertEqual(diff1.still_failing_count, 1)
        self.assertEqual(diff2.still_failing_count, 1)
        self.assertEqual(len(diff1.fixed), 0)
        self.assertEqual(len(diff2.fixed), 0)

        print("✅ Multi-sync stability verified")

    def test_instance_unavailable_no_false_fix(self):
        """Test that items are NOT marked Fixed when instance wasn't scanned."""
        print("\nTesting Instance Unavailable Edge Case...")

        _, instance_id = self._create_server_instance()

        # Baseline with FAIL
        run1_id = self._create_run("audit")
        save_finding(
            self.conn,
            run1_id,
            instance_id,
            build_entity_key("SRV1", "INST1", "test_issue"),
            "Config",
            "test_issue",
            "FAIL",
            "high",
            "Test fail",
        )
        self.conn.commit()

        # Sync run - item GONE (instance not reachable)
        run2_id = self._create_run("sync")
        # No findings added for INST1 - simulates instance unavailable
        self.conn.commit()

        # Get findings
        old_findings = self.store.get_findings(run1_id)
        new_findings = self.store.get_findings(run2_id)

        # CRITICAL: Provide a DIFFERENT instance as valid (simulates SRV1|INST1 not reachable)
        # This means we scanned OTHER-SRV but not SRV1
        valid_instances = {"other-srv|other-inst"}

        diff = diff_findings(old_findings, new_findings, set(), set(), valid_instances)

        # Should NOT be marked as fixed (item disappeared but we didn't scan that instance)
        self.assertEqual(len(diff.fixed), 0, "Should NOT falsely mark as fixed")
        print("✅ Instance unavailable edge case verified")

    def test_fix_wins_over_exception(self):
        """Test that Fix takes priority when both Fix and Exception occur."""
        print("\nTesting Fix + Exception Priority...")

        _, instance_id = self._create_server_instance()

        # Baseline: FAIL without exception
        run1_id = self._create_run("audit")
        entity_key = build_entity_key("SRV1", "INST1", "priority_test")
        save_finding(
            self.conn,
            run1_id,
            instance_id,
            entity_key,
            "Config",
            "priority_test",
            "FAIL",
            "high",
            "Test",
        )
        self.conn.commit()

        # Sync: PASS (fixed) + exception added simultaneously
        run2_id = self._create_run("sync")
        save_finding(
            self.conn,
            run2_id,
            instance_id,
            entity_key,
            "Config",
            "priority_test",
            "PASS",
            None,
            "Fixed",
        )
        self.conn.commit()

        old_findings = self.store.get_findings(run1_id)
        new_findings = self.store.get_findings(run2_id)

        # User added exception in Excel (but it's now PASS)
        old_exceptions = set()
        new_exceptions = {entity_key}  # User added exception

        valid = {"srv1|inst1"}
        diff = diff_findings(
            old_findings, new_findings, old_exceptions, new_exceptions, valid
        )

        # Fix should win - item is now PASS so it's Fixed, not Exception Added
        self.assertEqual(len(diff.fixed), 1, "Fix should be detected")
        self.assertEqual(
            diff.exception_added_count, 0, "Exception should NOT count (item is PASS)"
        )

        print("✅ Fix wins over exception verified")


if __name__ == "__main__":
    unittest.main()
