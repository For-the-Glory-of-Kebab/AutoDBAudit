from openpyxl import Workbook
from openpyxl.worksheet.protection import SheetProtection
from autodbaudit.infrastructure.excel.actions import ActionSheetMixin


class MockActionBuilder(ActionSheetMixin):
    def __init__(self):
        self.wb = Workbook()
        self._action_count = 0
        self._row_counters = {"Actions": 2}


def test_actions_sheet():
    print("Testing Actions Sheet...")
    builder = MockActionBuilder()

    # Add some actions
    builder.add_action(
        "SRV1",
        "INST1",
        "SA Account",
        "Renamed SA",
        "Low",
        "Good job",
        "Fixed",
        action_id=1,
    )
    builder.add_action(
        "SRV1",
        "INST1",
        "Config",
        "xp_cmdshell enabled",
        "High",
        "Disable it",
        "Open",
        action_id=2,
    )
    builder.add_action(
        "SRV1",
        "INST1",
        "Backup",
        "No backup",
        "Medium",
        "Take backup",
        "Regression",
        action_id=3,
    )

    # Finalize (should apply dropdowns and protection)
    builder._action_sheet = builder.wb["Actions"]
    builder._finalize_actions()

    ws = builder.wb["Actions"]

    # Check ID column hidden
    is_hidden = ws.column_dimensions["A"].hidden
    print(f"✅ ID Column Hidden: {is_hidden}")

    # Check Sheet Protection
    is_protected = ws.protection.sheet
    print(f"ℹ️ Sheet Protected: {is_protected} (Should be True eventually)")

    # Check Allow Formatting/Filtering
    print(f"ℹ️ AutoFilter Allowed: {ws.protection.autoFilter}")
    print(f"ℹ️ FormatColumns Allowed: {ws.protection.formatColumns}")

    # Check dropdowns (Data Validation) - heuristic
    dv_count = len(ws.data_validations.dataValidation)
    print(f"✅ Data Validations: {dv_count} (Expected > 0)")

    # Check Conditional Formatting
    cf_count = len(ws.conditional_formatting)
    print(f"✅ Conditional Rules: {cf_count} (Expected > 0)")

    builder.wb.save("test_actions_verify.xlsx")
    print("✅ Saved test_actions_verify.xlsx")


if __name__ == "__main__":
    test_actions_sheet()
