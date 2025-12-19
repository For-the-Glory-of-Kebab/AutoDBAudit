"""
Comprehensive Multi-Sheet Multi-Sync Stability Tests.

Tests all the specific issues reported by user:
1. Exception count drops to 0 after multiple syncs
2. Action sheet stops logging after 1-2 syncs
3. Exceptions not logged for Backup sheet (and other sheets)
4. Exceptions mistaken for fixes
5. Active exceptions showing as 0

Run with: .\.scripts\pytest.ps1 tests/test_multi_sync_stability.py -v
"""

import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from autodbaudit.infrastructure.sqlite import HistoryStore, initialize_schema_v2
from autodbaudit.infrastructure.sqlite.schema import save_finding, build_entity_key
from autodbaudit.application.annotation_sync import AnnotationSyncService
from autodbaudit.application.stats_service import StatsService
from autodbaudit.domain.change_types import FindingStatus, ChangeType
from autodbaudit.domain.state_machine import is_exception_eligible
from autodbaudit.application.diff.findings_diff import get_exception_keys


class TestMultiSyncStability(unittest.TestCase):
    """Test multiple sync cycles maintain correct counts and logging."""

    def setUp(self):
        """Create temp DB with schema."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.store = HistoryStore(self.db_path)
        self.store.initialize_schema()
        conn = self.store._get_connection()
        initialize_schema_v2(conn)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self._create_server_instance()
        self.sync_service = AnnotationSyncService(self.db_path)

    def tearDown(self):
        self.conn.close()
        if self.store._connection:
            self.store._connection.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def _create_server_instance(self):
        """Create test server and instance."""
        cursor = self.conn.execute(
            "INSERT INTO servers (hostname, ip_address) VALUES (?, ?)",
            ("TESTSERVER", "127.0.0.1"),
        )
        self.conn.commit()
        self.server_id = cursor.lastrowid

        cursor = self.conn.execute(
            "INSERT INTO instances (server_id, instance_name, version, version_major) VALUES (?, ?, ?, ?)",
            (self.server_id, "DEFAULT", "15.0.4123.1", 15),
        )
        self.conn.commit()
        self.instance_id = cursor.lastrowid

    def _create_run(self, run_type="audit"):
        """Create audit run."""
        cursor = self.conn.execute(
            "INSERT INTO audit_runs (started_at, status, run_type) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), "running", run_type),
        )
        self.conn.commit()
        return cursor.lastrowid

    def _create_finding(self, run_id, entity_type, entity_name, status):
        """Create a finding for testing."""
        entity_key = build_entity_key("TESTSERVER", "DEFAULT", entity_name)
        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            entity_key,
            entity_type,
            entity_name,
            status,
            "high" if status == "FAIL" else None,
            f"Test finding for {entity_name}",
        )
        self.conn.commit()
        return entity_key

    # =========================================================================
    # Test: All Entity Types Work (Including Backup, DB Role, etc.)
    # =========================================================================
    def test_all_entity_types_exception_detection(self):
        """
        Verify exception detection works for ALL entity types.
        Specifically tests those that were missing from KNOWN_TYPES.
        """
        print("\n📌 Test: All entity types exception detection")

        run_id = self._create_run()

        # Create findings for each entity type that supports exceptions
        entity_types = [
            ("login", "test_login"),
            ("backup", "test_backup"),  # User reported this was broken
            ("db_role", "test_db_role"),  # Was missing from KNOWN_TYPES
            ("permission", "test_permission"),  # Was missing
            ("orphaned_user", "test_orphan"),  # Was missing
            ("server_role_member", "test_role_member"),
            ("config", "xp_cmdshell"),
            ("service", "SQL Agent"),
            ("database", "TestDB"),
            ("db_user", "test_user"),
            ("audit_settings", "login_auditing"),
            ("linked_server", "linked1"),
        ]

        entity_keys = {}
        for etype, ename in entity_types:
            key = self._create_finding(run_id, etype, ename, "FAIL")
            entity_keys[etype] = key

        findings = self.store.get_findings(run_id)

        # Create annotations with exceptions for all types
        annotations = {}
        for etype, key in entity_keys.items():
            full_key = f"{etype}|{key}"
            annotations[full_key] = {
                "justification": f"Exception for {etype}",
                "review_status": "✓ Exception",
            }

        # Get exception keys - this should find ALL of them
        exception_keys = get_exception_keys(findings, annotations)

        # Verify each entity type was properly detected
        for etype, key in entity_keys.items():
            self.assertIn(
                key,
                exception_keys,
                f"Entity type '{etype}' was not detected as exceptioned!",
            )

        print(
            f"   ✅ All {len(entity_types)} entity types correctly detected as exceptions"
        )

    # =========================================================================
    # Test: Exception Count Stability Over Multiple Syncs
    # =========================================================================
    def test_exception_count_stable_over_syncs(self):
        """
        Verify exception counts don't drop to 0 after multiple syncs.
        User reported: "after a few runs, the active exceptions kept showing as 0"
        """
        print("\n📌 Test: Exception count stability over 5 syncs")

        run_id = self._create_run()

        # Create 3 FAIL findings
        keys = []
        for i in range(3):
            key = self._create_finding(run_id, "login", f"fail_user_{i}", "FAIL")
            keys.append(key)

        findings = self.store.get_findings(run_id)

        # Add exceptions for 2 of them
        annotations = {
            f"login|{keys[0]}": {
                "justification": "Exception 1",
                "review_status": "✓ Exception",
            },
            f"login|{keys[1]}": {
                "justification": "Exception 2",
                "review_status": "✓ Exception",
            },
            # keys[2] has no exception
        }

        # Simulate 5 syncs with the SAME data
        for sync_num in range(1, 6):
            exception_keys = get_exception_keys(findings, annotations)
            exception_count = len(exception_keys)

            print(f"   Sync {sync_num}: {exception_count} exceptions detected")

            self.assertEqual(
                exception_count,
                2,
                f"Sync {sync_num}: Expected 2 exceptions, got {exception_count}",
            )

        print("   ✅ Exception count stable at 2 over 5 syncs")

    # =========================================================================
    # Test: No Duplicate Exception Logs
    # =========================================================================
    def test_no_duplicate_exception_logs_over_syncs(self):
        """
        Verify same exception isn't re-logged in subsequent syncs.
        User reported: "Action sheet stops logging after 1-2 syncs"
        """
        print("\n📌 Test: No duplicate exception logs over 3 syncs")

        run_id = self._create_run()
        key = self._create_finding(run_id, "login", "stable_login", "FAIL")
        findings = self.store.get_findings(run_id)

        full_key = f"login|{key}"

        # Sync 1: NEW exception
        old_annotations_1 = {}
        new_annotations_1 = {
            full_key: {
                "justification": "Approved exception",
                "review_status": "✓ Exception",
            }
        }

        changes_1 = self.sync_service.detect_exception_changes(
            old_annotations_1, new_annotations_1, findings
        )

        self.assertEqual(len(changes_1), 1, "Sync 1 should detect 1 new exception")
        self.assertEqual(changes_1[0]["change_type"], "added")
        print(f"   Sync 1: {len(changes_1)} change(s) - {changes_1[0]['change_type']}")

        # Sync 2: Same data - should be 0 changes
        old_annotations_2 = new_annotations_1.copy()
        new_annotations_2 = old_annotations_2.copy()

        changes_2 = self.sync_service.detect_exception_changes(
            old_annotations_2, new_annotations_2, findings
        )

        self.assertEqual(len(changes_2), 0, "Sync 2 should detect 0 changes")
        print(f"   Sync 2: {len(changes_2)} change(s) (correct: no duplicate)")

        # Sync 3: Still same data
        changes_3 = self.sync_service.detect_exception_changes(
            new_annotations_2, new_annotations_2.copy(), findings
        )

        self.assertEqual(len(changes_3), 0, "Sync 3 should detect 0 changes")
        print(f"   Sync 3: {len(changes_3)} change(s) (correct: stable)")

        print("   ✅ No duplicate logs over 3 syncs")

    # =========================================================================
    # Test: Exception Not Mistaken for Fix
    # =========================================================================
    def test_exception_not_mistaken_for_fix(self):
        """
        Verify adding exception doesn't get logged as "Fixed".
        User reported: "exception got mistaken for a fix"
        """
        print("\n📌 Test: Exception not mistaken for fix")

        from autodbaudit.domain.state_machine import classify_finding_transition

        # Scenario: FAIL stays FAIL but exception is added
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.FAIL,
            old_has_exception=False,
            new_has_exception=True,
            instance_was_scanned=True,
        )

        self.assertNotEqual(
            result.change_type,
            ChangeType.FIXED,
            "Adding exception should NOT be classified as FIXED!",
        )
        self.assertEqual(
            result.change_type,
            ChangeType.EXCEPTION_ADDED,
            "Adding exception should be EXCEPTION_ADDED",
        )

        print(f"   Result: {result.change_type.value}")
        print("   ✅ Exception correctly classified as EXCEPTION_ADDED, not FIXED")

    # =========================================================================
    # Test: Fix Only When Status Changes to PASS
    # =========================================================================
    def test_fix_only_when_pass(self):
        """
        Verify FIXED only when old_status was FAIL and new_status is PASS.
        """
        print("\n📌 Test: Fix only when status changes to PASS")

        from autodbaudit.domain.state_machine import classify_finding_transition

        test_cases = [
            # (old, new, old_exc, new_exc, expected)
            (FindingStatus.FAIL, FindingStatus.PASS, False, False, ChangeType.FIXED),
            (FindingStatus.FAIL, FindingStatus.PASS, True, False, ChangeType.FIXED),
            (
                FindingStatus.FAIL,
                FindingStatus.FAIL,
                False,
                True,
                ChangeType.EXCEPTION_ADDED,
            ),
            (
                FindingStatus.FAIL,
                FindingStatus.FAIL,
                True,
                True,
                ChangeType.STILL_FAILING,
            ),
            (
                FindingStatus.PASS,
                FindingStatus.FAIL,
                False,
                False,
                ChangeType.REGRESSION,
            ),
        ]

        for old, new, old_exc, new_exc, expected in test_cases:
            result = classify_finding_transition(
                old_status=old,
                new_status=new,
                old_has_exception=old_exc,
                new_has_exception=new_exc,
            )
            self.assertEqual(
                result.change_type,
                expected,
                f"Failed for {old}->{new}, exc:{old_exc}->{new_exc}",
            )
            print(
                f"   {old.value}→{new.value} (exc:{old_exc}→{new_exc}) = {result.change_type.value} ✓"
            )

        print("   ✅ All transition classifications correct")


class TestStatsServiceIntegration(unittest.TestCase):
    """Integration tests for StatsService with real annotations."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()

        self.store = HistoryStore(self.db_path)
        self.store.initialize_schema()
        conn = self.store._get_connection()
        initialize_schema_v2(conn)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_server_instance()

    def tearDown(self):
        self.conn.close()
        if self.store._connection:
            self.store._connection.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def _create_server_instance(self):
        cursor = self.conn.execute(
            "INSERT INTO servers (hostname, ip_address) VALUES (?, ?)",
            ("TESTSERVER", "127.0.0.1"),
        )
        self.conn.commit()
        self.server_id = cursor.lastrowid

        cursor = self.conn.execute(
            "INSERT INTO instances (server_id, instance_name, version, version_major) VALUES (?, ?, ?, ?)",
            (self.server_id, "DEFAULT", "15.0.4123.1", 15),
        )
        self.conn.commit()
        self.instance_id = cursor.lastrowid

    def _create_run(self, run_type="audit"):
        cursor = self.conn.execute(
            "INSERT INTO audit_runs (started_at, status, run_type) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), "running", run_type),
        )
        self.conn.commit()
        return cursor.lastrowid

    def _create_finding(self, run_id, entity_type, entity_name, status):
        entity_key = build_entity_key("TESTSERVER", "DEFAULT", entity_name)
        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            entity_key,
            entity_type,
            entity_name,
            status,
        )
        self.conn.commit()
        return entity_key

    def test_stats_service_counts_exceptions_correctly(self):
        """
        Verify StatsService correctly counts active issues vs exceptions.
        """
        print("\n📌 Test: StatsService counts")

        run_id = self._create_run()

        # Create findings: 3 FAIL, 2 PASS
        fail_keys = [
            self._create_finding(run_id, "login", f"fail_{i}", "FAIL") for i in range(3)
        ]
        pass_keys = [
            self._create_finding(run_id, "login", f"pass_{i}", "PASS") for i in range(2)
        ]

        # Add exceptions for 2 FAIL items via annotations table
        from autodbaudit.infrastructure.sqlite.schema import upsert_annotation

        for i in range(2):
            key = fail_keys[i]
            upsert_annotation(
                self.conn,
                entity_type="login",
                entity_key=key,
                field_name="justification",
                field_value=f"Exception {i}",
            )
            upsert_annotation(
                self.conn,
                entity_type="login",
                entity_key=key,
                field_name="review_status",
                field_value="✓ Exception",
            )
        self.conn.commit()

        # Create StatsService
        annot_sync = AnnotationSyncService(self.db_path)
        stats_service = StatsService(
            findings_provider=self.store,
            annotations_provider=annot_sync,
        )

        stats = stats_service.calculate(
            baseline_run_id=run_id,
            current_run_id=run_id,
        )

        print(f"   Total findings: {stats.total_findings}")
        print(f"   Compliant: {stats.compliant_items}")
        print(f"   Active issues: {stats.active_issues}")
        print(f"   Exceptions: {stats.documented_exceptions}")

        # Verify counts
        self.assertEqual(stats.total_findings, 5, "Should have 5 total findings")
        self.assertEqual(stats.compliant_items, 2, "Should have 2 PASS items")
        self.assertEqual(
            stats.active_issues, 1, "Should have 1 active issue (3 FAIL - 2 exceptions)"
        )
        self.assertEqual(stats.documented_exceptions, 2, "Should have 2 exceptions")

        print("   ✅ StatsService counts correct")


if __name__ == "__main__":
    unittest.main(verbosity=2)
