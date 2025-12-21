"""
Fix column letters for dropdowns and ensure protection in remaining sheets.

This script corrects the column letters used for data validation dropdowns
in roles.py, orphaned_users.py, and audit_settings.py.
It also adds the missing _finalize_sheet_with_uuid call to audit_settings.py.
"""
import os

BASE_PATH = "src/autodbaudit/infrastructure/excel"

def fix_roles():
    path = os.path.join(BASE_PATH, "roles.py")
    if not os.path.exists(path):
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Fix Review Status letter: H -> I
    # Use specific patterns to avoid replacing things we assume are correct but might be ambiguous
    content = content.replace('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "I", STATUS_VALUES.all())')
    content = content.replace('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "I")')
    
    # 2. Fix Enabled letter: G -> H
    # Note: Previous manual edit might have set it to G or N. 
    # Current state (Step 865) set it to G. We want H.
    content = content.replace('add_dropdown_validation(ws, "G", ["✓ Yes", "✗ No"])', 'add_dropdown_validation(ws, "H", ["✓ Yes", "✗ No"])')
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Fixed roles.py (Enabled=H, Review=I)")

def fix_orphaned():
    path = os.path.join(BASE_PATH, "orphaned_users.py")
    if not os.path.exists(path):
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Fix Review Status: H -> I
    content = content.replace('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "I", STATUS_VALUES.all())')
    content = content.replace('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "I")')
    
    # 2. Fix Status: G -> H
    # Current state (Step 869) set to G.
    content = content.replace('add_dropdown_validation(ws, "G", ["⚠️ Orphaned", "✓ Fixed", "❌ Removed"])', 'add_dropdown_validation(ws, "H", ["⚠️ Orphaned", "✓ Fixed", "❌ Removed"])')
    
    # 3. Fix Type: F -> G
    # Current state (Step 869) set to F.
    content = content.replace('add_dropdown_validation(ws, "F", ["🪟 Windows", "🔑 SQL"])', 'add_dropdown_validation(ws, "G", ["🪟 Windows", "🔑 SQL"])')
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Fixed orphaned_users.py (Type=G, Status=H, Review=I)")

def fix_audit():
    path = os.path.join(BASE_PATH, "audit_settings.py")
    if not os.path.exists(path):
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Fix Review Status: H -> I (Current is H, but I wrote N->H in my plan, actually H is original)
    # Original columns: ... Status, Review Status ...
    # Wait, check Step 879.
    # Col 120: add_dropdown_validation(ws, "N", ["PASS", "FAIL"]) -> Status
    # Col 122: add_dropdown_validation(ws, "H", STATUS_VALUES.all()) -> Review
    # OK.
    
    # Review Status: H -> I
    content = content.replace('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "I", STATUS_VALUES.all())')
    content = content.replace('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "I")')
    
    # Status: N -> H
    content = content.replace('add_dropdown_validation(ws, "N", ["PASS", "FAIL"])', 'add_dropdown_validation(ws, "H", ["PASS", "FAIL"])')
    
    # Add _finalize_sheet_with_uuid if missing
    if "_finalize_sheet_with_uuid" not in content:
        target = "self._finalize_grouping(AUDIT_SETTING_CONFIG.name)"
        replacement = "self._finalize_grouping(AUDIT_SETTING_CONFIG.name)\n            self._finalize_sheet_with_uuid(self._audit_setting_sheet)"
        content = content.replace(target, replacement)
        if "_finalize_sheet_with_uuid" in content:
            print("  Added _finalize_sheet_with_uuid call")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Fixed audit_settings.py (Status=H, Review=I, protection added)")

def fix_databases():
    path = os.path.join(BASE_PATH, "databases.py")
    if not os.path.exists(path):
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove dangling line if present (caused by previous script error)
    # The line is indented and at the end or near end
    bad_line = '            self._finalize_sheet_with_uuid(self._database_sheet)'
    if bad_line in content:
        # Check if it's in the wrong place. Easy way: just remove all occurrences and insert correctly.
        content = content.replace(bad_line, '')
        
    # 2. Add finalize call correctly
    if "_finalize_sheet_with_uuid" not in content: # We just removed it
        target = "self._finalize_grouping(DATABASE_CONFIG.name)"
        replacement = "self._finalize_grouping(DATABASE_CONFIG.name)\n            self._finalize_sheet_with_uuid(self._database_sheet)"
        content = content.replace(target, replacement)
        
    # 3. Fix Dropdowns
    # Recovery: N -> F
    content = content.replace('add_dropdown_validation(ws, "N", ["🛡️ Full"', 'add_dropdown_validation(ws, "F", ["🛡️ Full"')
    # State: N -> G
    content = content.replace('add_dropdown_validation(ws, "N", ["✓ Online"', 'add_dropdown_validation(ws, "G", ["✓ Online"')
    # Trustworthy: N -> J
    content = content.replace('add_dropdown_validation(ws, "N", ["✓ ON"', 'add_dropdown_validation(ws, "J", ["✓ ON"')
    # Review Status: G -> K
    content = content.replace('add_dropdown_validation(ws, "G", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "K", STATUS_VALUES.all())')
    content = content.replace('add_review_status_conditional_formatting(ws, "G")', 'add_review_status_conditional_formatting(ws, "K")')
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Fixed databases.py (Recovery=F, State=G, Trustworthy=J, Review=K, indent fixed)")

if __name__ == "__main__":
    print("=== Fixing UUID consistency ===\n")
    fix_roles()
    fix_orphaned()
    fix_audit()
    fix_databases()
