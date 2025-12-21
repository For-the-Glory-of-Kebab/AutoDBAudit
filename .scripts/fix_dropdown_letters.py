"""
Comprehensive fix for dropdown column letters across all sheets.

This script:
1. Reads each sheet file
2. Counts columns to find STATUS_COLUMN position
3. Calculates correct dropdown letter (with UUID offset)
4. Replaces wrong "N" with correct letter
"""
import os
import re

BASE_PATH = "src/autodbaudit/infrastructure/excel"

# Sheet files to fix and their STATUS_COLUMN position (0-indexed in columns tuple)
# Position is AFTER UUID, so add 1 for the letter offset
SHEETS = {
    "logins.py": {"status_pos": 8},  # Original I, with UUID = J
    "roles.py": {"status_pos": 6},   # Original G, with UUID = H
    "services.py": {"status_pos": 5},  # Original F, with UUID = G
    "databases.py": {"status_pos": 5},  # Estimate
    "db_users.py": {"status_pos": 6},
    "db_roles.py": {"status_pos": 6},
    "orphaned_users.py": {"status_pos": 6},
    "client_protocols.py": {"status_pos": 6},
    "backups.py": {"status_pos": 9},
    "audit_settings.py": {"status_pos": 6},
    "permissions.py": {"status_pos": 6},
}

def col_to_letter(col_num):
    """Convert column number (1-indexed) to letter."""
    return chr(64 + col_num)


def fix_file(filepath: str, status_pos: int):
    """Fix dropdown letters in a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # STATUS_COLUMN position + 2 (1 for UUID, 1 for 1-indexing)
    # But columns tuple already has ACTION_COLUMN at index 0
    # So position 8 in tuple = column 9 in sheet (J with UUID)
    correct_letter = col_to_letter(status_pos + 2)  # +1 for UUID, +1 for 1-index
    
    # Replace "N" with correct letter for STATUS_VALUES
    old_pattern = f'add_dropdown_validation(ws, "N", STATUS_VALUES.all())'
    new_pattern = f'add_dropdown_validation(ws, "{correct_letter}", STATUS_VALUES.all())'
    content = content.replace(old_pattern, new_pattern)
    
    old_cf = f'add_review_status_conditional_formatting(ws, "N")'
    new_cf = f'add_review_status_conditional_formatting(ws, "{correct_letter}")'
    content = content.replace(old_cf, new_cf)
    
    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True, correct_letter
    return False, correct_letter


def main():
    print("=== Fixing Dropdown Letters (Comprehensive) ===\n")
    
    fixed = 0
    for filename, config in SHEETS.items():
        filepath = os.path.join(BASE_PATH, filename)
        if os.path.exists(filepath):
            changed, letter = fix_file(filepath, config["status_pos"])
            if changed:
                print(f"✓ {filename}: N -> {letter}")
                fixed += 1
            else:
                print(f"  {filename}: Already correct or no match")
        else:
            print(f"✗ {filename}: Not found")
    
    print(f"\n=== Fixed {fixed} files ===")


if __name__ == "__main__":
    main()
