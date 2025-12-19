import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import unittest
from unittest.mock import MagicMock
from autodbaudit.application.annotation_sync import AnnotationSyncService


class TestMissingFindingLogic(unittest.TestCase):
    def test_missing_finding_does_not_trigger_exception_removed(self):
        """
        Verify that if a finding has a previous exception but is missing from the current scan (fixed/gone),
        it does NOT trigger an 'EXCEPTION_REMOVED' event.
        """
        service = AnnotationSyncService("mock_db.db")

        # Previous state: One finding with an active exception
        previous_annotations = {
            "ServerA|Check1": {
                "status": "Exception",
                "justification": "Allowed temporarily",
                "edited_by": "user",
                "edited_at": "2024-01-01",
            }
        }

        # Current state: Empty (finding is fixed/gone)
        current_findings = []

        # Action
        changes = service.detect_exception_changes(
            old_annotations=previous_annotations,
            new_annotations={},
            current_findings=current_findings,
        )

        # Assert
        # We expect 0 changes.
        # If it were treated as "Exception Removed", we'd see a change event.
        self.assertEqual(len(changes), 0, f"Expected 0 changes, but got: {changes}")


if __name__ == "__main__":
    unittest.main()
