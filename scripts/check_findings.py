"""Check finding types in database."""

import sqlite3

conn = sqlite3.connect("output/audit_history.db")
rows = conn.execute(
    "SELECT DISTINCT finding_type, status FROM findings WHERE status IN ('FAIL', 'WARN') ORDER BY finding_type"
).fetchall()

print("Finding types with FAIL/WARN status:")
for r in rows:
    print(f"  {r[0]}: {r[1]}")

# Also check SA specifically - ALL statuses
sa_rows = conn.execute(
    "SELECT finding_type, status, entity_name, COUNT(*) FROM findings WHERE finding_type = 'sa_account' GROUP BY finding_type, status, entity_name"
).fetchall()
print(f"\nSA Account findings (all statuses): {len(sa_rows)}")
for r in sa_rows:
    print(f"  {r}")

# Also check logins table for is_sa_account
sa_logins = conn.execute(
    "SELECT name, is_disabled, is_sa_account FROM logins WHERE is_sa_account = 1 LIMIT 10"
).fetchall()
print(f"\nLogins with is_sa_account=1: {len(sa_logins)}")
for r in sa_logins:
    print(f"  {r}")

conn.close()
