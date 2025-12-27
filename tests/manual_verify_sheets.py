from openpyxl import Workbook
from autodbaudit.infrastructure.excel.db_roles import DBRoleSheetMixin
from autodbaudit.infrastructure.excel.orphaned_users import OrphanedUserSheetMixin
from autodbaudit.infrastructure.excel.permissions import PermissionSheetMixin
from autodbaudit.infrastructure.excel.triggers import TriggerSheetMixin


class MockSheetBuilder(
    DBRoleSheetMixin, OrphanedUserSheetMixin, PermissionSheetMixin, TriggerSheetMixin
):
    def __init__(self):
        self.wb = Workbook()
        self._row_counters = {
            "Database Roles": 2,
            "Orphaned Users": 2,
            "Permission Grants": 2,
            "Triggers": 2,
        }
        self._issue_count = 0
        self._pass_count = 0
        self._warn_count = 0


def test_sheets():
    builder = MockSheetBuilder()

    print("Testing Database Roles...")
    builder.add_db_role_member("SRV1", "INST1", "MyDB", "db_owner", "User1", "SQL_USER")
    builder.add_db_role_member("SRV1", "INST1", "MyDB", "public", "User2", "SQL_USER")
    print("✅ Database Roles Added")

    print("\nTesting Orphaned Users...")
    builder.add_orphaned_user("SRV1", "INST1", "MyDB", "Orphan1", "SQL_USER")
    builder.add_orphaned_user_not_found("SRV1", "INST1")
    print("✅ Orphaned Users Added")

    print("\nTesting Permissions...")
    builder.add_permission(
        "SRV1", "INST1", "DATABASE", "MyDB", "Grantee1", "SELECT", "GRANT", "Table1"
    )
    builder.add_permission(
        "SRV1", "INST1", "SERVER", "", "Grantee2", "CONTROL SERVER", "GRANT", "Server"
    )
    print("✅ Permissions Added")

    print("\nTesting Triggers...")
    builder.add_trigger("SRV1", "INST1", "Trig1", "INSERT", True, "DATABASE", "MyDB")
    builder.add_trigger("SRV1", "INST1", "SrvTrig1", "LOGON", True, "SERVER", "")
    print("✅ Triggers Added")

    print("\nSaving test.xlsx...")
    builder.wb.save("test_sheets_verify.xlsx")
    print("✅ Saved")


if __name__ == "__main__":
    test_sheets()
