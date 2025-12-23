"""
Shared test fixtures for sheet annotation tests.

Provides reusable setup for creating test databases, workbooks, and annotations.
All tests import from here to avoid code duplication.
"""

from __future__ import annotations

import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any

from openpyxl import Workbook

# Will be imported when tests run
import sys
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


def create_temp_environment():
    """Create temp directory with DB and return paths."""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_history.db"
    excel_path = temp_dir / "test_audit.xlsx"
    return temp_dir, db_path, excel_path


def cleanup_temp_environment(temp_dir: Path):
    """Clean up temp directory."""
    shutil.rmtree(temp_dir, ignore_errors=True)


def init_test_database(db_path: Path):
    """Initialize test database with schema."""
    from autodbaudit.infrastructure.sqlite import HistoryStore, initialize_schema_v2
    
    store = HistoryStore(db_path)
    store.initialize_schema()
    conn = store._get_connection()
    initialize_schema_v2(conn)
    return store


def create_test_server_instance(conn: sqlite3.Connection) -> tuple[int, int]:
    """Create test server and instance, return (server_id, instance_id)."""
    cursor = conn.execute(
        "INSERT INTO servers (hostname, ip_address) VALUES (?, ?)",
        ("localhost", "127.0.0.1"),
    )
    conn.commit()
    server_id = cursor.lastrowid
    
    cursor = conn.execute(
        "INSERT INTO instances (server_id, instance_name, version, version_major) VALUES (?, ?, ?, ?)",
        (server_id, "TestInstance", "15.0.4123.1", 15),
    )
    conn.commit()
    instance_id = cursor.lastrowid
    
    return server_id, instance_id


def create_audit_run(conn: sqlite3.Connection, run_type: str = "audit") -> int:
    """Create an audit run, return run_id."""
    cursor = conn.execute(
        "INSERT INTO audit_runs (started_at, status, run_type) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), "running", run_type),
    )
    conn.commit()
    return cursor.lastrowid


def create_finding(
    conn: sqlite3.Connection,
    run_id: int,
    instance_id: int,
    entity_key: str,
    finding_type: str,
    entity_name: str,
    status: str = "FAIL",
    risk_level: str = "high",
    description: str = "Test finding",
):
    """Create a finding in the database."""
    from autodbaudit.infrastructure.sqlite.schema import save_finding
    
    save_finding(
        conn, run_id, instance_id, entity_key, finding_type,
        entity_name, status, risk_level, description,
    )
    conn.commit()


def create_excel_with_data(
    excel_path: Path,
    sheet_name: str,
    headers: list[str],
    data_rows: list[list[Any]],
) -> None:
    """Create Excel file with specified sheet and data."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in data_rows:
        ws.append(row)
    wb.save(excel_path)


def build_entity_key(*parts: str) -> str:
    """Build lowercase entity key from parts."""
    return "|".join(str(p).lower() for p in parts)


# Sheet-specific header definitions (matching current writer structure)
SHEET_HEADERS = {
    "Triggers": [
        "⏳", "Server", "Instance", "Scope", "Database", "Trigger Name",
        "Event", "Enabled", "Review Status", "Justification", "Last Revised",
    ],
    "Sensitive Roles": [
        "⏳", "Server", "Instance", "Role", "Member", "Member Type", "Enabled",
        "Review Status", "Justification", "Last Revised",
    ],
    "Permission Grants": [
        "⏳", "Server", "Instance", "Scope", "Database", "Grantee", "Permission",
        "State", "Entity Type", "Entity Name", "Risk",
        "Review Status", "Justification", "Last Reviewed", "Notes",
    ],
    "Encryption": [
        "Server", "Instance", "Database", "Key Type", "Key Name",
        "Algorithm", "Created", "Backup Status", "Status", "Notes",
    ],
    "Client Protocols": [
        "⏳", "Server", "Instance", "Protocol", "Enabled", "Port", "Status",
        "Notes", "Review Status", "Justification", "Last Revised",
    ],
    "Server Logins": [
        "⏳", "Server", "Instance", "Login Name", "Login Type", "Enabled",
        "Password Policy", "Default Database",
        "Review Status", "Justification", "Last Revised", "Notes",
    ],
    "SA Account": [
        "⏳", "Server", "Instance", "Status", "Is Disabled", "Is Renamed",
        "Current Name", "Default DB",
        "Review Status", "Justification", "Last Reviewed", "Notes",
    ],
    "Configuration": [
        "⏳", "Server", "Instance", "Setting", "Current", "Required",
        "Status", "Risk",
        "Review Status", "Exception Reason", "Last Reviewed",
    ],
    "Orphaned Users": [
        "⏳", "Server", "Instance", "Database", "User Name", "Type", "Status",
        "Review Status", "Justification", "Last Revised",
    ],
    "Database Users": [
        "⏳", "Server", "Instance", "Database", "User Name", "Type",
        "Mapped Login", "Login Status", "Compliant",
        "Review Status", "Justification", "Last Reviewed", "Notes",
    ],
    "Database Roles": [
        "⏳", "Server", "Instance", "Database", "Role", "Member",
        "Member Type", "Risk",
        "Review Status", "Justification", "Last Reviewed",
    ],
    "Databases": [
        "⏳", "Server", "Instance", "Database", "Owner", "Recovery", "State",
        "Data (MB)", "Log (MB)", "Trustworthy",
        "Review Status", "Justification", "Last Reviewed", "Notes",
    ],
    "Backups": [
        "⏳", "Server", "Instance", "Database", "Recovery Model",
        "Last Full Backup", "Days Since", "Backup Path", "Size (MB)", "Status",
        "Review Status", "Justification", "Last Reviewed", "Notes",
    ],
    "Services": [
        "⏳", "Server", "Instance", "Service Name", "Type", "Status",
        "Startup", "Service Account", "Compliant",
        "Review Status", "Justification", "Last Reviewed",
    ],
    "Linked Servers": [
        "⏳", "Server", "Instance", "Linked Server", "Provider", "Data Source",
        "RPC Out", "Local Login", "Remote Login", "Impersonate", "Risk",
        "Review Status", "Purpose", "Justification", "Last Revised",
    ],
    "Audit Settings": [
        "⏳", "Server", "Instance", "Setting", "Current Value", "Recommended",
        "Status", "Review Status", "Justification", "Last Reviewed", "Notes",
    ],
}
