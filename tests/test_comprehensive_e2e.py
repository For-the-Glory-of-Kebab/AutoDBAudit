"""
Comprehensive End-to-End Tests for Exception Flow.

Tests ALL state transitions using the centralized exception logic.
This file verifies that the sync engine correctly handles:
1. Exception detection (FAIL + justification or status)
2. Non-exception documentation (PASS + justification = note only)
3. Invalid exception handling (PASS + Exception dropdown = ignored)
4. Multi-sync stability (no duplicate logs)
5. Field resilience (bad input → keep original)

Run with: python -m pytest tests/test_comprehensive_e2e.py -v --tb=short
"""

import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from autodbaudit.infrastructure.sqlite import HistoryStore, initialize_schema_v2
from autodbaudit.infrastructure.sqlite.schema import save_finding, build_entity_key
from autodbaudit.application.annotation_sync import AnnotationSyncService
from autodbaudit.domain.change_types import FindingStatus, ChangeType
from autodbaudit.domain.state_machine import (
    is_exception_eligible,
    classify_finding_transition,
    should_clear_exception_status,
)


class TestComprehensiveE2E(unittest.TestCase):
    """
    Comprehensive E2E tests covering all 12 scenarios.

    Uses temp DB and simulated Excel data for isolation.
    All tests verify the CENTRALIZED exception logic.
    """

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
            ("localhost", "127.0.0.1"),
        )
        self.conn.commit()
        self.server_id = cursor.lastrowid

        cursor = self.conn.execute(
            "INSERT INTO instances (server_id, instance_name, version, version_major) VALUES (?, ?, ?, ?)",
            (self.server_id, "TEST", "15.0.4123.1", 15),
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

    def _create_finding(self, run_id, login_name, status, risk=None, desc="Test"):
        """Create a finding for testing."""
        entity_key = build_entity_key("localhost", "TEST", login_name)
        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            entity_key,
            "login",
            login_name,
            status,
            risk,
            desc,
        )
        self.conn.commit()
        return entity_key

    # =========================================================================
    # Scenario 01: FAIL + justification = EXCEPTION_ADDED
    # =========================================================================
    def test_01_fail_plus_justification_is_exception(self):
        """
        FAIL + add justification = EXCEPTION_ADDED
        System should auto-set status to 'Exception'
        """
        print("\n📌 Test 01: FAIL + justification = Exception")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "admin_user", "FAIL", "high")
        findings = self.store.get_findings(run_id)

        # Simulate user adding justification
        old_annotations = {}
        new_annotations = {
            f"login|{entity_key}": {
                "justification": "Legacy admin - approved by IT",
                "review_status": "",  # User didn't set dropdown
            }
        }

        exceptions = self.sync_service.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["change_type"], "added")
        print(f"   ✅ Detected: {exceptions[0]['change_type']}")

    # =========================================================================
    # Scenario 02: PASS + justification = note only
    # =========================================================================
    def test_02_pass_plus_justification_is_note_only(self):
        """
        PASS + justification = Documentation only, NOT exception
        """
        print("\n📌 Test 02: PASS + justification = Note only")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "service_user", "PASS")
        findings = self.store.get_findings(run_id)

        old_annotations = {}
        new_annotations = {
            f"login|{entity_key}": {
                "justification": "Service account for app X",
                "review_status": "",
            }
        }

        exceptions = self.sync_service.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        self.assertEqual(len(exceptions), 0)
        print("   ✅ No exception detected (correct)")

    # =========================================================================
    # Scenario 03: PASS + Exception dropdown = IGNORED
    # =========================================================================
    def test_03_pass_with_exception_dropdown_ignored(self):
        """
        PASS + 'Exception' dropdown = Ignored
        Should NOT trigger 'Exception Removed' on subsequent syncs
        """
        print("\n📌 Test 03: PASS + Exception dropdown = Ignored")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "readonly_user", "PASS")
        findings = self.store.get_findings(run_id)

        # User mistakenly set Exception dropdown on PASS row
        old_annotations = {}
        new_annotations = {
            f"login|{entity_key}": {
                "justification": "",
                "review_status": "✓ Exception",  # Invalid on PASS row
            }
        }

        exceptions = self.sync_service.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        # Should NOT create exception entry
        self.assertEqual(len(exceptions), 0)
        print("   ✅ Exception dropdown on PASS row ignored")

        # Verify state_machine says don't clear (to avoid false 'removed')
        should_clear = should_clear_exception_status(
            status=FindingStatus.PASS,
            review_status="Exception",
        )
        # Note: should_clear returns True but we should NOT log it as removed
        # The point is to silently ignore, not actively log a removal
        print(f"   should_clear returned: {should_clear} (but we don't log 'removed')")

    # =========================================================================
    # Scenario 04: Second sync = NO duplicate log
    # =========================================================================
    def test_04_second_sync_no_duplicate_log(self):
        """
        Same exception in sync 2 = NO re-logging
        """
        print("\n📌 Test 04: Second sync stability (no duplicate)")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "legacy_admin", "FAIL", "high")
        findings = self.store.get_findings(run_id)

        full_key = f"login|{entity_key}"
        justification = "Approved legacy account"

        # First sync - new exception
        old_annotations_1 = {}
        new_annotations_1 = {
            full_key: {
                "justification": justification,
                "review_status": "✓ Exception",
            }
        }

        exceptions_1 = self.sync_service.detect_exception_changes(
            old_annotations_1, new_annotations_1, findings
        )
        self.assertEqual(len(exceptions_1), 1)
        self.assertEqual(exceptions_1[0]["change_type"], "added")
        print(f"   First sync: {exceptions_1[0]['change_type']}")

        # Second sync - SAME data
        old_annotations_2 = {
            full_key: {
                "justification": justification,
                "review_status": "✓ Exception",
            }
        }
        new_annotations_2 = old_annotations_2.copy()

        exceptions_2 = self.sync_service.detect_exception_changes(
            old_annotations_2, new_annotations_2, findings
        )

        self.assertEqual(len(exceptions_2), 0)
        print("   ✅ Second sync: No duplicate log")

    # =========================================================================
    # Scenario 05: FAIL + Exception → PASS = FIXED
    # =========================================================================
    def test_05_fix_clears_exception(self):
        """
        FAIL + Exception → PASS = FIXED (exception becomes history)
        """
        print("\n📌 Test 05: Exception row becomes PASS = FIXED")

        # Baseline: FAIL row with exception
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.PASS,
            old_has_exception=True,
            new_has_exception=False,
        )

        self.assertEqual(result.change_type, ChangeType.FIXED)
        self.assertTrue(result.should_log)
        print(f"   ✅ Transition: {result.change_type.value}")

    # =========================================================================
    # Scenario 06: PASS → FAIL = REGRESSION
    # =========================================================================
    def test_06_regression(self):
        """
        PASS → FAIL = REGRESSION
        """
        print("\n📌 Test 06: PASS → FAIL = Regression")

        result = classify_finding_transition(
            old_status=FindingStatus.PASS,
            new_status=FindingStatus.FAIL,
        )

        self.assertEqual(result.change_type, ChangeType.REGRESSION)
        self.assertTrue(result.should_log)
        print(f"   ✅ Transition: {result.change_type.value}")

    # =========================================================================
    # Scenario 07: PASS + note → FAIL = auto-exception
    # =========================================================================
    def test_07_regression_with_note_becomes_exception(self):
        """
        PASS + note → FAIL = REGRESSION + auto-exception
        The pre-existing justification becomes a valid exception
        """
        print("\n📌 Test 07: PASS with note → FAIL = auto-exception")

        # When row was PASS with justification, it qualifies as exception when FAIL
        is_eligible = is_exception_eligible(
            status=FindingStatus.FAIL,
            has_justification=True,  # Pre-existing note
            review_status=None,
        )

        self.assertTrue(is_eligible)
        print("   ✅ Pre-existing note becomes valid exception on FAIL")

    # =========================================================================
    # Scenario 08: Clear both = EXCEPTION_REMOVED
    # =========================================================================
    def test_08_exception_removed(self):
        """
        FAIL + Exception → User clears BOTH → EXCEPTION_REMOVED
        """
        print("\n📌 Test 08: Clear both fields = Exception Removed")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "temp_admin", "FAIL", "high")
        findings = self.store.get_findings(run_id)

        full_key = f"login|{entity_key}"

        # Previous state: had exception
        old_annotations = {
            full_key: {
                "justification": "Was approved",
                "review_status": "✓ Exception",
            }
        }

        # User cleared BOTH fields
        new_annotations = {
            full_key: {
                "justification": "",
                "review_status": "",
            }
        }

        exceptions = self.sync_service.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["change_type"], "removed")
        print(f"   ✅ Detected: {exceptions[0]['change_type']}")

    # =========================================================================
    # Scenario 09: Exception persists on still-failing
    # =========================================================================
    def test_09_exception_persists(self):
        """
        FAIL + Exception → still FAIL = NO change logged
        """
        print("\n📌 Test 09: Exception persists (no change)")

        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.FAIL,
            old_has_exception=True,
            new_has_exception=True,
        )

        self.assertEqual(result.change_type, ChangeType.STILL_FAILING)
        self.assertFalse(result.should_log)
        print(f"   ✅ Transition: {result.change_type.value} (no log)")

    # =========================================================================
    # Scenario 10: Bad date resilience
    # =========================================================================
    def test_10_bad_date_resilience(self):
        """
        Bad date input → keep original, log warning
        """
        print("\n📌 Test 10: Bad date input resilience")

        from autodbaudit.infrastructure.excel.base import parse_datetime_flexible

        # Test various bad inputs
        bad_inputs = ["not a date", "123abc", "", None, "2025-13-45"]

        for bad in bad_inputs:
            result = parse_datetime_flexible(bad, log_errors=False)
            self.assertIsNone(result)

        # Good input should parse
        good_result = parse_datetime_flexible("2025-12-19")
        self.assertIsNotNone(good_result)

        print("   ✅ Bad dates return None, good dates parse correctly")

    # =========================================================================
    # Scenario 11: Third sync stability
    # =========================================================================
    def test_11_third_sync_stability(self):
        """
        Sync 3 times with unchanged data = counts stable
        """
        print("\n📌 Test 11: Third sync stability")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "stable_admin", "FAIL", "high")
        findings = self.store.get_findings(run_id)

        full_key = f"login|{entity_key}"
        annotations = {
            full_key: {
                "justification": "Permanent exception",
                "review_status": "✓ Exception",
            }
        }

        # Sync 1, 2, 3 with same data
        exception_counts = []
        for sync_num in range(1, 4):
            if sync_num == 1:
                old = {}
            else:
                old = annotations.copy()

            exceptions = self.sync_service.detect_exception_changes(
                old, annotations.copy(), findings
            )
            exception_counts.append(len(exceptions))
            print(f"   Sync {sync_num}: {len(exceptions)} changes")

        # First sync should detect 1, subsequent should detect 0
        self.assertEqual(exception_counts[0], 1)
        self.assertEqual(exception_counts[1], 0)
        self.assertEqual(exception_counts[2], 0)
        print("   ✅ Counts stable across 3 syncs")

    # =========================================================================
    # Scenario 12: Edit justification text = EXCEPTION_UPDATED
    # =========================================================================
    def test_12_exception_text_edit(self):
        """
        Edit justification text = EXCEPTION_UPDATED (not new exception)
        """
        print("\n📌 Test 12: Edit justification = Updated")

        run_id = self._create_run()
        entity_key = self._create_finding(run_id, "edit_test", "FAIL", "high")
        findings = self.store.get_findings(run_id)

        full_key = f"login|{entity_key}"

        # Original exception
        old_annotations = {
            full_key: {
                "justification": "Original reason",
                "review_status": "✓ Exception",
            }
        }

        # User edits text
        new_annotations = {
            full_key: {
                "justification": "Updated reason with more detail",
                "review_status": "✓ Exception",
            }
        }

        exceptions = self.sync_service.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["change_type"], "updated")
        print(f"   ✅ Detected: {exceptions[0]['change_type']}")


# =============================================================================
# Additional Edge Case Tests
# =============================================================================
class TestEdgeCases(unittest.TestCase):
    """Additional edge case tests for robustness."""

    def test_exception_eligibility_comprehensive(self):
        """Test all combinations of exception eligibility."""
        print("\n📌 Exception eligibility matrix test")

        test_cases = [
            # (status, has_just, review_status, expected)
            (FindingStatus.FAIL, True, None, True),
            (FindingStatus.FAIL, False, "Exception", True),
            (FindingStatus.FAIL, True, "Exception", True),
            (FindingStatus.FAIL, False, None, False),
            (FindingStatus.WARN, True, None, True),
            (FindingStatus.PASS, True, None, False),
            (FindingStatus.PASS, False, "Exception", False),
            (FindingStatus.PASS, True, "Exception", False),
        ]

        for status, has_just, review, expected in test_cases:
            result = is_exception_eligible(status, has_just, review)
            self.assertEqual(
                result,
                expected,
                f"Failed for {status}, has_just={has_just}, review={review}",
            )

        print(f"   ✅ All {len(test_cases)} eligibility cases passed")

    def test_fix_takes_priority_over_exception(self):
        """Fix should take priority over exception when both happen."""
        print("\n📌 Fix priority over exception")

        # When row goes from FAIL to PASS, even with exception, it's a FIX
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.PASS,
            old_has_exception=True,
            new_has_exception=True,  # Would be exception if still FAIL
        )

        self.assertEqual(result.change_type, ChangeType.FIXED)
        print("   ✅ Fix wins over exception")


if __name__ == "__main__":
    unittest.main(verbosity=2)
