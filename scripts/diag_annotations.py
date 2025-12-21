# Check annotation keys in database
import sys

sys.path.insert(0, "src")
from pathlib import Path
import sqlite3

db_paths = [Path("output/audit_001/audit_history.db"), Path("output/audit_history.db")]
db_path = next((p for p in db_paths if p.exists()), None)

if not db_path:
    print("No database found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Get sample annotations
rows = conn.execute(
    "SELECT entity_key, justification, review_status FROM annotations WHERE justification IS NOT NULL AND justification != '' LIMIT 20"
).fetchall()

print(f"=== ANNOTATIONS WITH JUSTIFICATION ({len(rows)}) ===")
for r in rows:
    print(
        f"  key={r['entity_key'][:60]} just={r['justification'][:30] if r['justification'] else ''}"
    )

# Get all distinct entity_key prefixes
prefixes = conn.execute(
    """
    SELECT DISTINCT SUBSTR(entity_key, 1, INSTR(entity_key || '|', '|') - 1) as prefix
    FROM annotations
"""
).fetchall()
print(f"\n=== ENTITY KEY PREFIXES ===")
for p in prefixes:
    print(f"  {p['prefix']}")

conn.close()
