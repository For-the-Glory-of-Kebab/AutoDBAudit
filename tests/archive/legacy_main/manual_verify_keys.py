import sys
from pathlib import Path

# Add src to path
src_path = Path("src").absolute()
sys.path.insert(0, str(src_path))

try:
    from autodbaudit.application.annotation_sync import SHEET_ANNOTATION_CONFIG
except ImportError as e:
    print(f"CRITICAL: Failed to import config: {e}")
    sys.exit(1)

required_sheets = [
    "SA Account",
    "Server Logins",
    "Sensitive Roles",
    "Configuration",
    "Instances",
    "Services",
    "Databases",
    "Database Users",
    "Database Roles",
    "Permission Grants",
    "Orphaned Users",
    "Linked Servers",
    "Triggers",
    "Client Protocols",
    "Backups",
    "Audit Settings",
    "Encryption",
]

missing = []
print("--- Sheet Configuration Audit ---")
for sheet in required_sheets:
    if sheet in SHEET_ANNOTATION_CONFIG:
        cfg = SHEET_ANNOTATION_CONFIG[sheet]
        keys = cfg.get("key_cols", [])
        print(f"✅ {sheet:20} | Keys: {keys}")
    else:
        print(f"❌ {sheet:20} | MISSING CONFIG")
        missing.append(sheet)

print("-" * 40)
if missing:
    print(f"FAILED: Missing config for {len(missing)} sheets.")
    sys.exit(1)
else:
    print("SUCCESS: All critical sheets have valid sync configuration.")
    sys.exit(0)
