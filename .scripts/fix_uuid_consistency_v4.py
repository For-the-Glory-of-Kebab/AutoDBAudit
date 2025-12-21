"""
Fix final column letter discrepancies in db_roles, db_users, permissions.
Shifts columns by +1 where previous calculation was off.
"""
import os

BASE_PATH = "src/autodbaudit/infrastructure/excel"

def fix_module(filename, replacements):
    path = os.path.join(BASE_PATH, filename)
    if not os.path.exists(path):
        print(f"Skipping {filename}")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Fixed {filename}")

def run_fixes():
    # DB Users: Shift Status(H->I), Comp(I->J), Review(J->K)
    # Status (Validation for Mapped/System/Orphaned)
    fix_module("db_users.py", [
        # Review: J -> K (Reverse order safely) (Wait, my previous script put it at J)
        # Check current state: "J", STATUS_VALUES.all()
        ('add_dropdown_validation(ws, "J", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "K", STATUS_VALUES.all())'),
        ('add_review_status_conditional_formatting(ws, "J")', 'add_review_status_conditional_formatting(ws, "K")'),
        
        # Compliant: I -> J
        ('add_dropdown_validation(ws, "I", ["✓", "⚠️ Review"', 'add_dropdown_validation(ws, "J", ["✓", "⚠️ Review"'),
        
        # Status: H -> I
        ('add_dropdown_validation(ws, "H", ["✓ Mapped"', 'add_dropdown_validation(ws, "I", ["✓ Mapped"')
    ])

    # DB Roles: Shift Role(E->F), Type(G->H), Risk(H->I), Review(I->J)
    fix_module("db_roles.py", [
        # Review: I -> J
        ('add_dropdown_validation(ws, "I", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "J", STATUS_VALUES.all())'),
        ('add_review_status_conditional_formatting(ws, "I")', 'add_review_status_conditional_formatting(ws, "J")'),
        
        # Risk: H -> I
        ('add_dropdown_validation(ws, "H", ["🔴 High"', 'add_dropdown_validation(ws, "I", ["🔴 High"'),
        
        # Type: G -> H
        ('add_dropdown_validation(ws, "G", ["🪟 Windows"', 'add_dropdown_validation(ws, "H", ["🪟 Windows"'),
        
        # Role: E -> F
        ('add_dropdown_validation(ws, "E", [\n            "👑 db_owner"', 'add_dropdown_validation(ws, "F", [\n            "👑 db_owner"')
    ])
    
    # Permissions: Review H -> J (Shifted +2? I -> J? previous was H)
    # Perm Cols: Action(B), Serv(C), Inst(D), DB(E), Schema(F), Obj(G), Princ(H), Perm(I), Rev(J)
    # Current state is "H".
    fix_module("permissions.py", [
        ('add_dropdown_validation(ws, "H", STATUS_VALUES.all())', 'add_dropdown_validation(ws, "J", STATUS_VALUES.all())'),
        ('add_review_status_conditional_formatting(ws, "H")', 'add_review_status_conditional_formatting(ws, "J")')
    ])

if __name__ == "__main__":
    print("=== Fixing Final Column Letters ===\n")
    run_fixes()
