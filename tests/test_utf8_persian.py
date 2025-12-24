import pytest
import sqlite3
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from autodbaudit.infrastructure.sqlite.store import HistoryStore
from autodbaudit.infrastructure.excel.writer import EnhancedReportWriter


@pytest.fixture
def temp_output(tmp_path):
    return tmp_path


def test_persian_sqlite_persistence(temp_output):
    """Verify that Persian text can be saved and retrieved from SQLite."""
    db_path = temp_output / "audit_history_u8.db"

    # Persian strings
    persian_note = "تست یادداشت فارسی"  # "Persian note test"
    persian_server = "سرور_اصلی"  # "Main_Server"

    store = HistoryStore(db_path)
    store.initialize_schema()

    # Simulate a run
    run = store.begin_audit_run(organization="Test Org", config_hash="abc")
    run_id = run.id

    # Add an action with Persian text (using upsert_action as proxy for text storage)
    action_id = store.upsert_action(
        initial_run_id=run_id,
        entity_key="SERVER|INSTANCE|test",
        action_type="Fixed",
        status="Closed",
        action_date=datetime.now(timezone.utc).isoformat(),
        description=persian_note,  # Persian Description
        sync_run_id=run_id,
        finding_type="Config",
        notes="More Persian: " + persian_note,
    )

    store.close()

    # Verify retrieval via simple SQL to ensure raw bytes are correct
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT description, notes FROM action_log WHERE id=?", (action_id,))
    row = cursor.fetchone()
    saved_desc = row[0]
    saved_notes = row[1]

    assert (
        persian_note in saved_desc
    ), f"SQLite: Description content mismatch. Got {saved_desc}"
    assert (
        persian_note in saved_notes
    ), f"SQLite: Notes content mismatch. Got {saved_notes}"

    conn.close()
    print("\n✅ SQLite persists Persian text correctly.")


def test_persian_excel_export(temp_output):
    """Verify that Persian text is correctly written to Excel."""
    file_path = temp_output / "Persian_Report.xlsx"

    persian_text_1 = "این یک تست است"  # "This is a test"
    persian_text_2 = "وضعیت قرمز"  # "Red Status"

    writer = EnhancedReportWriter()

    # Add an instance with Persian content
    writer.add_instance(
        config_name="Test Config",
        server_name="Localhost",
        instance_name="Exp",
        machine_name="Server1",
        ip_address="127.0.0.1",
        tcp_port=1433,
        version="15.0",
        version_major=15,
        edition="Developer",
        product_level="RTM",
        version_status="WARN",
        version_status_note=persian_text_1,  # Use Persian in a tooltip/note
    )

    # Add Action with Persian content
    writer.add_action(
        server_name="Localhost",
        instance_name="Exp",
        category="General",
        finding="Sample Finding",
        risk_level="High",
        recommendation=persian_text_2,  # Persian recommendation
        status="Open",
        notes=persian_text_1,  # Persian notes
    )

    writer.save(file_path)

    # Verify by reading back with pandas
    # Note: openpyxl engine is standard for xlsx
    df = pd.read_excel(file_path, sheet_name="Actions", engine="openpyxl")

    # Verify 'Notes' column contains the Persian text
    found = False
    for col in df.columns:
        if df[col].astype(str).str.contains(persian_text_1).any():
            found = True
            break

    assert (
        found
    ), f"Excel: Could not find Persian note '{persian_text_1}' in Actions sheet."

    print("✅ Excel writes Persian text correctly.")
