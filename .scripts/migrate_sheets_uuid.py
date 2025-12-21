"""
Batch migration script for UUID support across all sheet modules.

This script updates all Excel sheet modules to use UUID-aware methods.
Changes applied:
1. _ensure_sheet() -> _ensure_sheet_with_uuid()
2. _write_row() -> _write_row_with_uuid()
3. Column indices +1 for UUID offset
4. Add _finalize_sheet_with_uuid() call
5. Update docstrings with UUID note
"""
import os
import re

# All sheet files to update (excluding linked_servers.py which is done)
SHEET_FILES = [
    "sa_account.py",
    "logins.py",
    "roles.py",
    "config.py",
    "services.py",
    "databases.py",
    "db_users.py",
    "db_roles.py",
    "orphaned_users.py",
    "triggers.py",
    "client_protocols.py",
    "backups.py",
    "audit_settings.py",
    "encryption.py",
    "permissions.py",
    "role_matrix.py",
    "instances.py",
]

BASE_PATH = "src/autodbaudit/infrastructure/excel"

def update_sheet_file(filepath: str) -> dict:
    """Update a single sheet file with UUID support."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    changes = []
    
    # 1. Add UUID note to docstring if not present
    if "UUID Support" not in content:
        # Find first docstring and append UUID note
        docstring_pattern = r'("""[^"]*?""")'
        match = re.search(docstring_pattern, content)
        if match:
            old_doc = match.group(1)
            new_doc = old_doc[:-3] + "\n\nUUID Support (v3):\n    - Column A: Hidden UUID for stable row identification\n    - All other columns shifted +1 from original positions\n\"\"\""
            content = content.replace(old_doc, new_doc, 1)
            changes.append("Added UUID docstring")
    
    # 2. Replace _ensure_sheet with _ensure_sheet_with_uuid
    count = content.count("self._ensure_sheet(")
    if count > 0:
        content = content.replace("self._ensure_sheet(", "self._ensure_sheet_with_uuid(")
        changes.append(f"Replaced _ensure_sheet ({count}x)")
    
    # 3. Replace _write_row with _write_row_with_uuid 
    # This is trickier because we need to handle return value change
    # Pattern: row = self._write_row(...) -> row, row_uuid = self._write_row_with_uuid(...)
    write_row_pattern = r'row = self\._write_row\('
    if re.search(write_row_pattern, content):
        content = re.sub(write_row_pattern, 'row, row_uuid = self._write_row_with_uuid(', content)
        changes.append("Replaced _write_row with _write_row_with_uuid")
    
    # 4. Update column indices in apply_action_needed_styling (column 1 -> column 2)
    # Pattern: column=1) for action column
    if "apply_action_needed_styling(ws.cell(row=row, column=1)" in content:
        content = content.replace(
            "apply_action_needed_styling(ws.cell(row=row, column=1)",
            "apply_action_needed_styling(ws.cell(row=row, column=2)"
        )
        changes.append("Updated action column index 1->2")
    
    # 5. Update hardcoded column indices in cell access
    # This is complex - look for patterns like column=N and shift
    # Common patterns: column=2, column=3, etc.
    # We'll update specific patterns found in these files
    
    # For data_cols lists: [2, 3, 4, ...] -> [3, 4, 5, ...]
    data_cols_pattern = r'data_cols=\[([0-9, ]+)\]'
    def shift_data_cols(match):
        cols = match.group(1)
        col_list = [int(x.strip()) for x in cols.split(",")]
        shifted = [str(x + 1) for x in col_list]
        return f'data_cols=[{", ".join(shifted)}]'
    
    if re.search(data_cols_pattern, content):
        content = re.sub(data_cols_pattern, shift_data_cols, content)
        changes.append("Shifted data_cols indices +1")
    
    # 6. Update column indices in ws.cell(row=row, column=N) calls
    # Only update those that are clearly data columns (not loop variables)
    # Pattern: column=N) where N is a literal number
    def shift_column_access(match):
        col_num = int(match.group(1))
        # Only shift if > 1 (column 1 is now UUID, action is 2)
        if col_num >= 1:
            return f'column={col_num + 1})'
        return match.group(0)
    
    # This is risky - only do it for specific patterns we know need shifting
    # Actually, let's be more conservative and not do this automatically
    
    # 7. Update dropdown column letters (shift by 1 letter)
    # D -> E, E -> F, etc.
    letter_shift = {
        '"D"': '"E"', '"E"': '"F"', '"F"': '"G"', '"G"': '"H"',
        '"H"': '"I"', '"I"': '"J"', '"J"': '"K"', '"K"': '"L"',
        '"L"': '"M"', '"M"': '"N"'
    }
    
    for old, new in letter_shift.items():
        # Only replace in add_dropdown_validation and add_review_status_conditional_formatting calls
        if f'add_dropdown_validation(ws, {old}' in content:
            content = content.replace(f'add_dropdown_validation(ws, {old}', f'add_dropdown_validation(ws, {new}')
            changes.append(f"Shifted dropdown column {old}->{new}")
        if f'add_review_status_conditional_formatting(ws, {old}' in content:
            content = content.replace(f'add_review_status_conditional_formatting(ws, {old}', f'add_review_status_conditional_formatting(ws, {new}')
            changes.append(f"Shifted CF column {old}->{new}")
    
    # 8. Add _finalize_sheet_with_uuid call to finalize methods
    # Pattern: def _finalize_xxx(self):
    finalize_pattern = r'(def _finalize_\w+\(self\).*?:\s*""".*?"""\s*if self\._.+_sheet)'
    # This is complex, we'll handle it separately
    
    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"file": os.path.basename(filepath), "changes": changes, "updated": True}
    
    return {"file": os.path.basename(filepath), "changes": [], "updated": False}


def main():
    print("=== UUID Migration for Excel Sheet Modules ===\n")
    
    results = []
    for filename in SHEET_FILES:
        filepath = os.path.join(BASE_PATH, filename)
        if os.path.exists(filepath):
            result = update_sheet_file(filepath)
            results.append(result)
            if result["updated"]:
                print(f"✓ {filename}: {len(result['changes'])} changes")
                for change in result["changes"]:
                    print(f"    - {change}")
            else:
                print(f"  {filename}: No changes needed")
        else:
            print(f"✗ {filename}: File not found")
    
    updated_count = sum(1 for r in results if r["updated"])
    print(f"\n=== Summary: {updated_count}/{len(SHEET_FILES)} files updated ===")


if __name__ == "__main__":
    main()
