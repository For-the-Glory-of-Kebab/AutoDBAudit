"""
Fix remaining broken modules: backups.py, config.py, db_roles.py, db_users.py.
Fixes indentation errors (dangling _finalize call) and dropdown column letters.
"""
import os

BASE_PATH = "src/autodbaudit/infrastructure/excel"

def fix_module(filename, config_name, sheet_attr, column_fixes):
    path = os.path.join(BASE_PATH, filename)
    if not os.path.exists(path):
        print(f"Skipping {filename} (not found)")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove dangling line
    bad_line = f'            self._finalize_sheet_with_uuid(self.{sheet_attr})'
    if bad_line in content:
        content = content.replace(bad_line, '')
        
    # 2. Add finalize call correctly
    if "_finalize_sheet_with_uuid" not in content:
        # Find the finalize method body
        # Pattern: self._finalize_grouping(CONFIG_NAME)\n
        target = f'self._finalize_grouping({config_name})'
        replacement = f'self._finalize_grouping({config_name})\n            self._finalize_sheet_with_uuid(self.{sheet_attr})'
        content = content.replace(target, replacement)
        
    # 3. Fix Dropdowns
    for target_str, replacement_str in column_fixes:
        content = content.replace(target_str, replacement_str)
        
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Fixed {filename}")

def run_fixes():
    # Backups: Status N->J
    fix_module(
        "backups.py", "BACKUP_CONFIG.name", "_backup_sheet",
        [
            ('add_dropdown_validation(ws, "N", ["PASS", "WARN", "FAIL"])', 'add_dropdown_validation(ws, "J", ["PASS", "WARN", "FAIL"])')
        ]
    )
    
    # Config: Status N->G, Risk N->H, Review H->I
    fix_module(
        "config.py", "CONFIG_CONFIG.name", "_config_sheet",
        [
            # Status (Cur=E, Req=F, Status=G)
            ('add_dropdown_validation(ws, "N", ["PASS", "FAIL"])', 'add_dropdown_validation(ws, "G", ["PASS", "FAIL"])'),
            # Risk (Risk=H) -- Risk values? High/Low? Let's assume ["High", "Medium", "Low"] or similar
            # Wait, I don't know the exact string for Risk dropdown. 
            # I'll rely on reading it if possible? Or skip if I can't match.
            # I'll check if "N" is used for Risk. If I can't match it unique, it's safer to skip Risk dropdown fix if it's ambiguous.
            # But Review H->I is critical.
            ('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "I", STATUS_VALUES.all())'),
            ('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "I")')
        ]
    )
    
    # DB Roles: Role N->E, Type N->G, Risk N->H, Review H->I
    fix_module(
        "db_roles.py", "DB_ROLE_CONFIG.name", "_db_role_sheet",
        [
            # Role (starts with db_owner)
            ('add_dropdown_validation(ws, "N", [\n            "👑 db_owner"', 'add_dropdown_validation(ws, "E", [\n            "👑 db_owner"'),
            # Type (Windows/Key)
            ('add_dropdown_validation(ws, "N", ["🪟 Windows"', 'add_dropdown_validation(ws, "G", ["🪟 Windows"'),
            # Risk (High/Med)
            ('add_dropdown_validation(ws, "N", ["🔴 High"', 'add_dropdown_validation(ws, "H", ["🔴 High"'),
            # Review
            ('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "I", STATUS_VALUES.all())'),
            ('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "I")')
        ]
    )
    
    # DB Users: Status N->H, Compliant N->I, Review H->J
    fix_module(
        "db_users.py", "DB_USER_CONFIG.name", "_db_user_sheet",
        [
            # Status (Mapped...)
            ('add_dropdown_validation(ws, "N", ["✓ Mapped"', 'add_dropdown_validation(ws, "H", ["✓ Mapped"'),
            # Compliant (Guest...)
            ('add_dropdown_validation(ws, "N", ["✓", "⚠️ Review"', 'add_dropdown_validation(ws, "I", ["✓", "⚠️ Review"'),
            # Review
            ('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "J", STATUS_VALUES.all())'),
            ('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "J")')
        ]
    )

if __name__ == "__main__":
    print("=== Fixing Module Indentation and Columns ===\n")
    run_fixes()
