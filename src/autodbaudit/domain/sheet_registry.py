"""
Centralized Sheet Registry.

SINGLE SOURCE OF TRUTH for all Excel sheet specifications.
All modules must import from here - no duplicate definitions.

This solves the root cause of sync bugs where different files
had inconsistent key_columns, entity_types, and editable_columns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class SheetSpec:
    """
    Complete specification for an Excel sheet.

    Attributes:
        name: Excel sheet tab name
        entity_type: DB entity type identifier (e.g., "backup", "service")
        key_columns: Columns forming unique row key (Server, Instance, ...)
        editable_columns: Map of Excel column -> DB field for sync
        annotation_column: Primary column for user notes/justification
        has_uuid: Sheet has hidden UUID in column A
        has_action: Sheet has ⏳ indicator in column B
        tracks_exceptions: Include in exception stats
        tracks_actions: Log changes to Actions sheet
        is_info_only: No discrepancies possible (e.g., Instances)
    """

    name: str
    entity_type: str
    key_columns: tuple[str, ...] = ()
    editable_columns: dict[str, str] = field(default_factory=dict)
    annotation_column: str = "Notes"
    has_uuid: bool = True
    has_action: bool = True
    tracks_exceptions: bool = True
    tracks_actions: bool = True
    is_info_only: bool = False

    def get_entity_key_from_row(self, row_dict: dict[str, str]) -> str:
        """Build entity key from row data dictionary."""
        parts = [str(row_dict.get(col, "")).strip() for col in self.key_columns]
        return "|".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# SHEET REGISTRY - THE SINGLE SOURCE OF TRUTH
# ═══════════════════════════════════════════════════════════════════════════

SHEET_REGISTRY: dict[str, SheetSpec] = {}


def _register(spec: SheetSpec) -> SheetSpec:
    """Register a sheet spec and return it."""
    SHEET_REGISTRY[spec.name] = spec
    return spec


# ─────────────────────────────────────────────────────────────────────────────
# Special Sheets (no UUID/Action columns)
# ─────────────────────────────────────────────────────────────────────────────

COVER = _register(
    SheetSpec(
        name="Cover",
        entity_type="cover",
        key_columns=(),
        has_uuid=False,
        has_action=False,
        tracks_exceptions=False,
        tracks_actions=False,
        is_info_only=True,
    )
)

INSTANCES = _register(
    SheetSpec(
        name="Instances",
        entity_type="instance",
        key_columns=("Config Name", "Server", "Instance"),
        editable_columns={"Notes": "notes", "Last Revised": "last_revised"},
        annotation_column="Notes",
        has_uuid=False,
        has_action=False,
        tracks_exceptions=False,
        tracks_actions=False,
        is_info_only=True,
    )
)

ACTIONS = _register(
    SheetSpec(
        name="Actions",
        entity_type="action",
        key_columns=("ID",),
        editable_columns={"Notes": "notes", "Detected Date": "action_date"},
        annotation_column="Notes",
        has_uuid=False,
        has_action=False,
        tracks_exceptions=False,
        tracks_actions=False,  # Actions sheet doesn't log to itself
        is_info_only=True,
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# Security Sheets (with UUID + Action columns)
# ─────────────────────────────────────────────────────────────────────────────

SA_ACCOUNT = _register(
    SheetSpec(
        name="SA Account",
        entity_type="sa_account",
        key_columns=("Server", "Instance"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Justification",
    )
)

CONFIGURATION = _register(
    SheetSpec(
        name="Configuration",
        entity_type="config",
        key_columns=("Server", "Instance", "Setting"),
        editable_columns={
            "Review Status": "review_status",
            "Exception Reason": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Exception Reason",
    )
)

SERVER_LOGINS = _register(
    SheetSpec(
        name="Server Logins",
        entity_type="login",
        key_columns=("Server", "Instance", "Login Name"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Justification",
    )
)

SENSITIVE_ROLES = _register(
    SheetSpec(
        name="Sensitive Roles",
        entity_type="server_role",
        key_columns=("Server", "Instance", "Role", "Member"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Justification",
    )
)

SERVICES = _register(
    SheetSpec(
        name="Services",
        entity_type="service",
        key_columns=("Server", "Instance", "Service Name"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Justification",
    )
)

DATABASES = _register(
    SheetSpec(
        name="Databases",
        entity_type="database",
        key_columns=("Server", "Instance", "Database"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Justification",
    )
)

DATABASE_USERS = _register(
    SheetSpec(
        name="Database Users",
        entity_type="db_user",
        key_columns=("Server", "Instance", "Database", "User Name"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Justification",
    )
)

DATABASE_ROLES = _register(
    SheetSpec(
        name="Database Roles",
        entity_type="db_role",
        key_columns=("Server", "Instance", "Database", "Role", "Member"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Justification",
    )
)

ORPHANED_USERS = _register(
    SheetSpec(
        name="Orphaned Users",
        entity_type="orphaned_user",
        key_columns=("Server", "Instance", "Database", "User Name"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Justification",
    )
)

PERMISSION_GRANTS = _register(
    SheetSpec(
        name="Permission Grants",
        entity_type="permission",
        key_columns=("Server", "Instance", "Scope", "Grantee", "Permission"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Justification",
    )
)

ROLE_MATRIX = _register(
    SheetSpec(
        name="Role Matrix",
        entity_type="role_matrix",
        key_columns=("Server", "Instance", "Database", "Principal Name"),
        editable_columns={},  # Info-only, no editable columns
        has_action=False,  # NO indicator column - info only
        tracks_exceptions=False,
        tracks_actions=False,
        is_info_only=True,
    )
)

LINKED_SERVERS = _register(
    SheetSpec(
        name="Linked Servers",
        entity_type="linked_server",
        key_columns=("Server", "Instance", "Linked Server"),
        editable_columns={
            "Review Status": "review_status",
            "Purpose": "purpose",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Purpose",
    )
)

TRIGGERS = _register(
    SheetSpec(
        name="Triggers",
        entity_type="trigger",
        key_columns=("Server", "Instance", "Scope", "Trigger Name"),
        editable_columns={
            "Review Status": "review_status",
            "Notes": "notes",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Notes",
    )
)

BACKUPS = _register(
    SheetSpec(
        name="Backups",
        entity_type="backup",
        key_columns=("Server", "Instance", "Database"),  # CORRECT: Full composite key
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Notes",
    )
)

CLIENT_PROTOCOLS = _register(
    SheetSpec(
        name="Client Protocols",
        entity_type="protocol",
        key_columns=("Server", "Instance", "Protocol"),
        editable_columns={
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
        annotation_column="Justification",
    )
)

ENCRYPTION = _register(
    SheetSpec(
        name="Encryption",
        entity_type="encryption",
        key_columns=("Server", "Instance", "Key Type", "Key Name"),
        editable_columns={"Notes": "notes"},
        annotation_column="Notes",
        has_action=False,  # Info-only sheet
        tracks_exceptions=False,
        is_info_only=True,
    )
)

AUDIT_SETTINGS = _register(
    SheetSpec(
        name="Audit Settings",
        entity_type="audit_settings",
        key_columns=("Server", "Instance", "Setting"),
        editable_columns={
            "Review Status": "review_status",
            "Exception Reason": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
        annotation_column="Exception Reason",
    )
)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


def get_spec(sheet_name: str) -> SheetSpec | None:
    """Get sheet spec by name. Returns None if not found."""
    return SHEET_REGISTRY.get(sheet_name)


def get_spec_by_entity_type(entity_type: str) -> SheetSpec | None:
    """Get sheet spec by entity type. Returns None if not found."""
    for spec in SHEET_REGISTRY.values():
        if spec.entity_type == entity_type:
            return spec
    return None


def get_all_trackable_sheets() -> list[SheetSpec]:
    """Get all sheets that track exceptions."""
    return [s for s in SHEET_REGISTRY.values() if s.tracks_exceptions]


def get_all_action_logging_sheets() -> list[SheetSpec]:
    """Get all sheets that log to Actions."""
    return [s for s in SHEET_REGISTRY.values() if s.tracks_actions]


def get_key_columns(sheet_name: str) -> tuple[str, ...]:
    """Get key columns for a sheet. Empty tuple if not found."""
    spec = get_spec(sheet_name)
    return spec.key_columns if spec else ()


def get_entity_type(sheet_name: str) -> str:
    """Get entity type for a sheet. Empty string if not found."""
    spec = get_spec(sheet_name)
    return spec.entity_type if spec else ""


def get_editable_columns(sheet_name: str) -> dict[str, str]:
    """Get editable columns mapping for a sheet."""
    spec = get_spec(sheet_name)
    return dict(spec.editable_columns) if spec else {}
