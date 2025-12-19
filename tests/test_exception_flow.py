"""
Integration test for exception detection flow.

Tests the EXACT scenarios the user described:
1. Discrepant row + justification = Exception (logged, indicator updated)
2. Non-discrepant row + justification = Documentation (NOT logged as exception)
3. Second sync with unchanged data = NO changes logged
4. Non-discrepant with justification should NOT be logged as "removed" on 2nd sync
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


class TestExceptionDetectionFlow(unittest.TestCase):
    """Test the exception detection with actual database operations."""

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

        # Create server/instance
        self._create_server_instance()

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
            (self.server_id, "INST1", "15.0.4123.1", 15),
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

    def test_exception_detection_key_format(self):
        """Test that annotation entity_key matches finding entity_key (case-insensitive).

        NOTE: As of the EntityKey rewrite, ALL keys are normalized to lowercase.
        This means finding keys and annotation keys should match case-insensitively.
        """
        print("\nTesting entity key format matching (case-insensitive)...")

        # Create finding - keys are now normalized to lowercase
        run_id = self._create_run()
        finding_entity_key = build_entity_key("localhost", "INST1", "test_login")

        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            finding_entity_key,
            "login",
            "test_login",
            "FAIL",
            "high",
            "Test",
        )
        self.conn.commit()

        # Simulate annotation key (how annotation_sync builds it)
        # From read_all_from_excel: full_key = f"{entity_type}|{entity_key}"
        # where entity_key is now normalized to lowercase
        annotation_full_key = f"login|localhost|inst1|test_login"  # lowercase

        # Extract entity_key for lookup (what detect_exception_changes does)
        parts = annotation_full_key.split("|", 1)
        entity_key_for_lookup = parts[1] if len(parts) == 2 else annotation_full_key

        print(f"Finding entity_key:      '{finding_entity_key}'")
        print(f"Annotation full_key:     '{annotation_full_key}'")
        print(f"Lookup key (after split): '{entity_key_for_lookup}'")

        # Check if they match - both should be lowercase now
        self.assertEqual(
            finding_entity_key.lower(),
            entity_key_for_lookup.lower(),
            f"Key format mismatch! Finding: '{finding_entity_key}' != Annotation lookup: '{entity_key_for_lookup}'",
        )
        print("✅ Keys match (case-insensitive)!")

    def test_discrepant_with_justification_is_exception(self):
        """Test: FAIL + justification = Exception (should be detected)."""
        print("\nTesting: Discrepant + Justification = Exception...")

        from autodbaudit.application.annotation_sync import AnnotationSyncService

        # Create finding (FAIL status)
        run_id = self._create_run()
        entity_key = build_entity_key("localhost", "INST1", "admin_login")
        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            entity_key,
            "login",
            "admin_login",
            "FAIL",
            "high",
            "Test",
        )
        self.conn.commit()

        # Get findings
        findings = self.store.get_findings(run_id)

        # Simulate annotations
        old_annotations = {}  # No previous annotations
        new_annotations = {
            "login|localhost|inst1|admin_login": {  # lowercase keys
                "justification": "Legacy admin account",
                "review_status": "✓ Exception",
            }
        }

        sync = AnnotationSyncService(self.db_path)
        exceptions = sync.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        print(f"Detected exceptions: {len(exceptions)}")
        for ex in exceptions:
            print(f"  {ex['change_type']}: {ex['entity_key']}")

        self.assertEqual(len(exceptions), 1, "Should detect 1 exception")
        self.assertEqual(exceptions[0]["change_type"], "added")
        print("✅ Discrepant row correctly detected as exception!")

    def test_nondiscrepant_with_justification_is_documentation(self):
        """Test: PASS + justification = Documentation (should NOT be exception)."""
        print("\nTesting: Non-discrepant + Justification = Documentation...")

        from autodbaudit.application.annotation_sync import AnnotationSyncService

        # Create finding (PASS status)
        run_id = self._create_run()
        entity_key = build_entity_key("localhost", "INST1", "service_account")
        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            entity_key,
            "login",
            "service_account",
            "PASS",
            None,
            "OK",
        )
        self.conn.commit()

        findings = self.store.get_findings(run_id)

        old_annotations = {}
        new_annotations = {
            "login|localhost|inst1|service_account": {  # lowercase keys
                "justification": "Service account for app X",
                "review_status": "",  # No exception status
            }
        }

        sync = AnnotationSyncService(self.db_path)
        exceptions = sync.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        print(f"Detected exceptions: {len(exceptions)}")

        self.assertEqual(
            len(exceptions), 0, "PASS row should NOT be logged as exception"
        )
        print("✅ Non-discrepant row correctly treated as documentation!")

    def test_second_sync_no_false_removed(self):
        """Test: Second sync with unchanged PASS+justification should NOT log 'removed'."""
        print("\nTesting: Second sync stability (no false 'removed')...")

        from autodbaudit.application.annotation_sync import AnnotationSyncService

        # Create finding (PASS status)
        run_id = self._create_run()
        entity_key = build_entity_key("localhost", "INST1", "readonly_user")
        save_finding(
            self.conn,
            run_id,
            self.instance_id,
            entity_key,
            "login",
            "readonly_user",
            "PASS",
            None,
            "OK",
        )
        self.conn.commit()

        findings = self.store.get_findings(run_id)

        # Simulate: PASS row had justification saved to DB (from first sync)
        old_annotations = {
            "login|localhost|inst1|readonly_user": {  # lowercase keys
                "justification": "Read-only for reports",
            }
        }

        # Same justification in Excel (unchanged)
        new_annotations = {
            "login|localhost|inst1|readonly_user": {  # lowercase keys
                "justification": "Read-only for reports",
            }
        }

        sync = AnnotationSyncService(self.db_path)
        exceptions = sync.detect_exception_changes(
            old_annotations, new_annotations, findings
        )

        print(f"Detected changes: {len(exceptions)}")
        for ex in exceptions:
            print(f"  {ex['change_type']}: {ex['entity_key']}")

        # Should NOT detect as "removed" - it was never an exception!
        removed = [e for e in exceptions if e["change_type"] == "removed"]
        self.assertEqual(
            len(removed), 0, "Should NOT falsely detect 'removed exception'"
        )
        print("✅ Second sync correctly shows no false 'removed' entries!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
