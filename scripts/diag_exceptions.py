# Simulate detect_exception_changes to see what it returns
import sys

sys.path.insert(0, "src")
from pathlib import Path
from autodbaudit.infrastructure.sqlite import HistoryStore
from autodbaudit.application.annotation_sync import AnnotationSyncService

db_paths = [Path("output/audit_001/audit_history.db"), Path("output/audit_history.db")]
db_path = next((p for p in db_paths if p.exists()), None)

excel_paths = [
    Path("output/audit_001/Audit_001_Latest.xlsx"),
    Path("output/Audit_Latest.xlsx"),
]
excel_path = next((p for p in excel_paths if p.exists()), None)

if not db_path or not excel_path:
    print(f"DB: {db_path}, Excel: {excel_path}")
    exit(1)

print(f"DB: {db_path}")
print(f"Excel: {excel_path}")

# Initialize services
store = HistoryStore(db_path)
annot_sync = AnnotationSyncService(db_path)

# Load annotations
old_annotations = annot_sync.load_from_db()
current_annotations = annot_sync.read_all_from_excel(excel_path)

print(f"\nOld annotations: {len(old_annotations)}")
print(f"Current annotations: {len(current_annotations)}")

# Get current findings
latest = store.get_latest_run_id()
current_findings = store.get_findings(latest)

print(f"Current findings: {len(current_findings)}")

# Detect exception changes
raw_exceptions = annot_sync.detect_exception_changes(
    old_annotations=old_annotations,
    new_annotations=current_annotations,
    current_findings=current_findings,
)

print(f"\n=== DETECTED EXCEPTION CHANGES ({len(raw_exceptions)}) ===")
for ex in raw_exceptions:
    print(
        f"  type={ex.get('change_type')} entity={ex.get('entity_type')} key={ex.get('full_key', '')[:50]}"
    )

# Also show linked server annotations to see if exceptions are there
print(f"\n=== LINKED SERVER ANNOTATIONS (current) ===")
for k, v in current_annotations.items():
    if "linked_server" in k.lower():
        just = v.get("justification", "")
        status = v.get("review_status", "")
        if just or status:
            print(f"  {k[:50]}: just='{just[:20]}...' status='{status}'")
