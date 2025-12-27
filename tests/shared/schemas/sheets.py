"""
Accurate Excel Schema Definitions

Extracted DIRECTLY from docs/REPORT_SCHEMA.md.
This is the SINGLE SOURCE OF TRUTH for test expectations.

Key Rules:
- Most data sheets have hidden _UUID in column A
- Most data sheets have ⏳ Action indicator in column B
- Column letters in schema are VISIBLE columns (starting at B or C)
- Exceptions: Cover, Instances, Encryption, and Role Matrix have different structure
"""

from __future__ import annotations

from typing import NamedTuple


class SheetSpec(NamedTuple):
    """Specification for a single sheet."""

    name: str
    has_uuid: bool  # Hidden column A with UUID
    has_action: bool  # Column B has ⏳ action indicator
    first_headers: list[str]  # First few VISIBLE headers (after hidden cols)


# Extracted from REPORT_SCHEMA.md - THE SOURCE OF TRUTH
SHEET_SPECS = [
    # 1. Cover - special structure
    SheetSpec(
        "Cover",
        has_uuid=False,
        has_action=False,
        first_headers=["Icon", "Labels", "Values"],
    ),
    # 2. Instances - NO action column, starts with Config Name
    SheetSpec(
        "Instances",
        has_uuid=False,
        has_action=False,
        first_headers=["Config Name", "Server", "Instance", "Machine Name"],
    ),
    # 3. SA Account - has action column
    SheetSpec(
        "SA Account",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Status", "Is Disabled"],
    ),
    # 4. Configuration - has action column
    SheetSpec(
        "Configuration",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Setting", "Current"],
    ),
    # 5. Server Logins - has action column
    SheetSpec(
        "Server Logins",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Login Name", "Login Type"],
    ),
    # 6. Sensitive Roles - has action column
    SheetSpec(
        "Sensitive Roles",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Role", "Member"],
    ),
    # 7. Services - has action column
    SheetSpec(
        "Services",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Service Name", "Type"],
    ),
    # 8. Databases - has action column
    SheetSpec(
        "Databases",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Database", "Owner"],
    ),
    # 9. Database Users - has action column
    SheetSpec(
        "Database Users",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Database", "User Name"],
    ),
    # 10. Database Roles - has action column
    SheetSpec(
        "Database Roles",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Database", "Role"],
    ),
    # 11. Orphaned Users - has action column
    SheetSpec(
        "Orphaned Users",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Database", "User Name"],
    ),
    # 12. Permission Grants - has action column
    SheetSpec(
        "Permission Grants",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Scope", "Database"],
    ),
    # 13. Role Matrix - NO action column, starts with Server
    SheetSpec(
        "Role Matrix",
        has_uuid=False,
        has_action=False,
        first_headers=["Server", "Instance", "Database", "Principal Name"],
    ),
    # 14. Linked Servers - has action column
    SheetSpec(
        "Linked Servers",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Linked Server", "Provider"],
    ),
    # 15. Triggers - has action column
    SheetSpec(
        "Triggers",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Scope", "Database"],
    ),
    # 16. Backups - has action column
    SheetSpec(
        "Backups",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Database", "Recovery"],
    ),
    # 17. Client Protocols - has action column
    SheetSpec(
        "Client Protocols",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Protocol", "Enabled"],
    ),
    # 18. Encryption - NO action column, starts with Server
    SheetSpec(
        "Encryption",
        has_uuid=False,
        has_action=False,
        first_headers=["Server", "Instance", "Database", "Key Type"],
    ),
    # 19. Audit Settings - has action column
    SheetSpec(
        "Audit Settings",
        has_uuid=True,
        has_action=True,
        first_headers=["Server", "Instance", "Setting", "Current"],
    ),
    # 20. Actions - special structure, no UUID but starts with ID
    SheetSpec(
        "Actions",
        has_uuid=False,
        has_action=False,
        first_headers=["ID", "Server", "Instance", "Category"],
    ),
]

# Quick lookup by name
SHEET_SPEC_BY_NAME = {spec.name: spec for spec in SHEET_SPECS}

# All expected sheet names
EXPECTED_SHEET_NAMES = [spec.name for spec in SHEET_SPECS]

# Sheets with action indicator (for tests that check ⏳)
SHEETS_WITH_ACTION = [spec.name for spec in SHEET_SPECS if spec.has_action]

# Sheets with hidden UUID column
SHEETS_WITH_UUID = [spec.name for spec in SHEET_SPECS if spec.has_uuid]


def get_visible_column_start(sheet_name: str) -> int:
    """
    Get 1-indexed column number where visible data starts.

    Returns:
        1 for sheets without hidden cols (Cover, Instances, etc)
        2 for sheets with UUID only (none currently)
        3 for sheets with UUID and Action cols
    """
    spec = SHEET_SPEC_BY_NAME.get(sheet_name)
    if not spec:
        return 1

    start = 1
    if spec.has_uuid:
        start += 1  # Skip hidden UUID
    if spec.has_action:
        start += 1  # Skip action indicator
    return start
