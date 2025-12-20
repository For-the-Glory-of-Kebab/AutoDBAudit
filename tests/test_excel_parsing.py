import pytest
import os
from pathlib import Path
from openpyxl import Workbook
from autodbaudit.application.annotation_sync import AnnotationSyncService
from autodbaudit.infrastructure.excel.base import ACTION_COLUMN


def test_excel_header_parsing(tmp_path):
    """
    Verify that AnnotationSyncService correctly parses headers,
    especially the Action (⏳) column and Status column, for Triggers.
    """
    excel_path = tmp_path / "test_parsing.xlsx"
    wb = Workbook()

    # 1. Setup Triggers Sheet
    ws = wb.active
    ws.title = "Triggers"

    # Define headers exactly as they should appear
    # Column A: ⏳ (Action)
    # Column B: Server
    # ...
    # Column X: Status (or similar)
    headers = [
        "⏳",
        "Server",
        "Instance",
        "Scope",
        "Database",
        "Trigger Name",
        "Event",
        "Status",
        "Review Status",
        "Justification",
        "Last Reviewed",
        "Notes",
    ]
    ws.append(headers)

    # Add a row that needs action
    # Action=⏳, Status=FAIL, Review Status=""
    ws.append(
        ["⏳", "Srv1", "Inst1", "SERVER", "", "Trig1", "LOGON", "FAIL", "", "", "", ""]
    )

    # Add a row that is documented
    # Action=✓, Status=FAIL, Review Status=Exception
    ws.append(
        [
            "✅",
            "Srv1",
            "Inst1",
            "SERVER",
            "",
            "Trig2",
            "LOGON",
            "FAIL",
            "✓ Exception",
            "Accepted",
            "2024-01-01",
            "",
        ]
    )

    wb.save(excel_path)

    # 2. Run Read
    sync = AnnotationSyncService("dummy.db")
    annotations = sync.read_all_from_excel(str(excel_path))

    # 3. Verify
    print("\nAnnotations Found:", annotations)

    # Key: trigger|srv1|inst1|server||trig1|logon  (Note: empty database part for SERVER scope)
    key1 = "trigger|srv1|inst1|server||trig1|logon"
    assert key1 in annotations, f"Key {key1} not found in annotations"

    # Check Action Needed flag
    # Logic in annotation_sync.py:
    # if "⏳" in action_val: fields["action_needed"] = True
    assert (
        annotations[key1].get("action_needed") is True
    ), "Action Needed not detected for Row 2"

    # Check Status parsing
    assert annotations[key1].get("status") == "FAIL", "Status not parsed correctly"


if __name__ == "__main__":
    pytest.main([__file__])
