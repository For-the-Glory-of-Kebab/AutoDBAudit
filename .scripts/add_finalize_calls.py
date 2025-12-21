"""
Add _finalize_sheet_with_uuid call to all sheet finalize methods.
"""
import os
import re

BASE_PATH = "src/autodbaudit/infrastructure/excel"

# Map of filename to (finalize_method, sheet_attribute)
SHEETS = {
    "triggers.py": ("_finalize_triggers", "_trigger_sheet"),
    "services.py": ("_finalize_services", "_service_sheet"),
    "roles.py": ("_finalize_roles", "_role_sheet"),
    "role_matrix.py": ("_finalize_role_matrix", "_role_matrix_sheet"),
    "permissions.py": ("_finalize_permissions", "_permission_sheet"),
    "orphaned_users.py": ("_finalize_orphaned_users", "_orphaned_sheet"),
    "logins.py": ("_finalize_logins", "_login_sheet"),
    "instances.py": ("_finalize_instances", "_instance_sheet"),
    "db_users.py": ("_finalize_db_users", "_db_user_sheet"),
    "db_roles.py": ("_finalize_db_roles", "_db_role_sheet"),
    "databases.py": ("_finalize_databases", "_database_sheet"),
    "config.py": ("_finalize_config", "_config_sheet"),
    "client_protocols.py": ("_finalize_client_protocols", "_protocol_sheet"),
    "backups.py": ("_finalize_backups", "_backup_sheet"),
    "audit_settings.py": ("_finalize_audit_settings", "_audit_sheet"),
    "encryption.py": ("_finalize_encryption", "_encryption_sheet"),
}


def fix_file(filepath: str, finalize_method: str, sheet_attr: str) -> bool:
    """Add _finalize_sheet_with_uuid call if not present."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if already has the call
    if "_finalize_sheet_with_uuid" in content:
        return False  # Already fixed
    
    # Find the finalize method and add the call
    # Pattern: def _finalize_xxx(self) -> None:\n        """..."""\n        if self._xxx_sheet:
    pattern = rf'(def {finalize_method}\(self\).*?:\s*""".*?""".*?if self\.{sheet_attr}:)'
    
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"  Warning: Could not find {finalize_method} pattern in {filepath}")
        return False
    
    # Add the finalize call after the existing content in the if block
    # We need to find where the if block ends and add our call before it
    
    # Simpler approach: Find "if self._xxx_sheet:" and add our call as last line
    if_pattern = rf'(if self\.{sheet_attr}:\n)((?:[ \t]+[^\n]+\n)+)'
    
    def add_finalize_call(m):
        indent = "            "  # 12 spaces (3 levels of indentation)
        # Check existing indent
        lines = m.group(2).split('\n')
        if lines:
            # Get indentation from first non-empty line
            for line in lines:
                if line.strip():
                    indent = line[:len(line) - len(line.lstrip())]
                    break
        
        finalize_call = f"{indent}self._finalize_sheet_with_uuid(self.{sheet_attr})\n"
        return m.group(1) + m.group(2).rstrip('\n') + '\n' + finalize_call
    
    new_content = re.sub(if_pattern, add_finalize_call, content)
    
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    
    return False


def main():
    print("=== Adding _finalize_sheet_with_uuid to all sheets ===\n")
    
    fixed = 0
    for filename, (finalize_method, sheet_attr) in SHEETS.items():
        filepath = os.path.join(BASE_PATH, filename)
        if os.path.exists(filepath):
            if fix_file(filepath, finalize_method, sheet_attr):
                print(f"✓ Fixed {filename}")
                fixed += 1
            else:
                print(f"  {filename}: Already has call or could not find pattern")
        else:
            print(f"✗ {filename}: Not found")
    
    print(f"\n=== Fixed {fixed} files ===")


if __name__ == "__main__":
    main()
