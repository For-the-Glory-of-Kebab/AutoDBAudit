"""
Linked Servers Column Matching Test

Validates that the Linked Servers sheet correctly identifies columns
without substring collision (e.g., "Server" vs "Linked Server").
"""

import pytest
from pathlib import Path
from openpyxl import Workbook, load_workbook

from autodbaudit.application.annotation_sync import (
    AnnotationSyncService,
    SHEET_ANNOTATION_CONFIG,
)
from autodbaudit.infrastructure.sqlite.store import HistoryStore


class TestLinkedServersColumnMatching:
    """Test Linked Servers sheet column matching specifically."""

    @pytest.fixture
    def setup_linked_servers_excel(self, tmp_path):
        """Create an Excel file with Linked Servers data."""
        excel_path = tmp_path / "test_linked.xlsx"
        db_path = tmp_path / "test.db"

        # Create workbook with Linked Servers sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Linked Servers"

        # Headers per SHEET_ANNOTATION_CONFIG:
        # key_cols: Server, Instance, Linked Server, Local Login, Remote Login
        # editable_cols: Review Status, Purpose, Justification, Last Reviewed
        headers = [
            "⏳",  # Action column
            "Server",  # Key 1
            "Instance",  # Key 2
            "Linked Server",  # Key 3
            "Provider",
            "Data Source",
            "RPC Out",
            "Local Login",  # Key 4
            "Remote Login",  # Key 5
            "Impersonate",
            "Risk",
            "Review Status",  # Editable
            "Purpose",  # Editable - this was getting jumbled!
            "Justification",  # Editable
            "Last Reviewed",  # Editable
        ]
        ws.append(headers)

        # Add test data rows
        rows = [
            [
                "⏳",
                "srv1",
                "inst1",
                "LINKEDSRV1",
                "SQLNCLI",
                "srv2",
                "Yes",
                "admin",
                "remoteadmin",
                "No",
                "Low",
                "",
                "Purpose for row 1",
                "Just1",
                "",
            ],
            [
                "⏳",
                "srv1",
                "inst1",
                "LINKEDSRV2",
                "SQLNCLI",
                "srv3",
                "No",
                "(Default)",
                "(Default)",
                "No",
                "High",
                "✓ Exception",
                "Purpose for row 2",
                "Just2",
                "2025-01-01",
            ],
            [
                "⏳",
                "srv2",
                "inst1",
                "LINKEDSRV3",
                "SQLNCLI",
                "srv4",
                "Yes",
                "user1",
                "remoteuser1",
                "Yes",
                "Medium",
                "",
                "Purpose for row 3",
                "",
                "",
            ],
        ]
        for row in rows:
            ws.append(row)

        wb.save(excel_path)

        # Initialize DB
        store = HistoryStore(db_path)
        store.initialize_schema()

        self.service = AnnotationSyncService(db_path)
        self.excel_path = excel_path
        self.db_path = db_path

        return tmp_path

    def test_linked_servers_key_includes_linked_server_name(
        self, setup_linked_servers_excel
    ):
        """Verify entity keys include the Linked Server name, not just Server."""
        annotations = self.service.read_all_from_excel(self.excel_path)

        # Entity key should be: linked_server|server|instance|linked_server_name|local_login|remote_login
        # If column matching is wrong, "Server" might match "Linked Server" column

        # Check for correct keys
        expected_partial = "srv1|inst1|linkedsrv1"  # Should contain linked server name

        found_correct_key = False
        for key in annotations.keys():
            if expected_partial in key:
                found_correct_key = True
                break

        assert (
            found_correct_key
        ), f"Expected key containing '{expected_partial}'. Keys: {list(annotations.keys())}"

    def test_purpose_column_round_trip(self, setup_linked_servers_excel):
        """Verify Purpose column values survive read/write without getting jumbled."""
        # Read annotations
        annotations = self.service.read_all_from_excel(self.excel_path)

        # Find any linked_server annotation with purpose
        purpose_values = {}
        for key, fields in annotations.items():
            if key.startswith("linked_server|") and fields.get("purpose"):
                purpose_values[key] = fields["purpose"]

        assert (
            len(purpose_values) >= 2
        ), f"Expected at least 2 purpose values, got {len(purpose_values)}"

        # Modify purpose for one entry
        for key in purpose_values:
            annotations[key]["purpose"] = "MODIFIED PURPOSE"
            break  # Only modify first one

        # Write back
        cells_updated = self.service.write_all_to_excel(self.excel_path, annotations)
        assert cells_updated > 0

        # Re-read and verify
        reloaded = self.service.read_all_from_excel(self.excel_path)

        # Check purposes preserved (not jumbled)
        found_modified = False
        for key, fields in reloaded.items():
            if key.startswith("linked_server|"):
                purpose = fields.get("purpose", "")
                if purpose == "MODIFIED PURPOSE":
                    found_modified = True
                # Ensure purpose didn't get overwritten with wrong value
                assert purpose in [
                    "MODIFIED PURPOSE",
                    "Purpose for row 1",
                    "Purpose for row 2",
                    "Purpose for row 3",
                    "",
                ], f"Unexpected purpose value: {purpose}"

        assert found_modified, "Modified purpose was lost!"

    def test_key_column_separation(self, setup_linked_servers_excel):
        """Verify Server and Linked Server are treated as separate columns."""
        config = SHEET_ANNOTATION_CONFIG["Linked Servers"]

        # Server and Linked Server should both be in key_cols
        assert "Server" in config["key_cols"]
        assert "Linked Server" in config["key_cols"]

        # Read and verify keys have both Server AND Linked Server values
        annotations = self.service.read_all_from_excel(self.excel_path)

        for key in annotations:
            if key.startswith("linked_server|"):
                parts = key.split("|")
                # linked_server|server|instance|linked_server_name|local_login|remote_login
                assert len(parts) >= 4, f"Key doesn't have enough parts: {key}"
                server = parts[1]
                linked_server = parts[3] if len(parts) > 3 else ""

                # Server and Linked Server should be DIFFERENT
                # (unless we happen to have same name, but in test data they're different)
                if "linkedsrv" in linked_server:
                    assert (
                        server != linked_server
                    ), f"Server and Linked Server should be different: server={server}, linked_server={linked_server}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
