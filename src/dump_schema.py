import sqlite3
import sys

try:
    conn = sqlite3.connect("output/audit_history.db")
    cursor = conn.cursor()

    # Get all tables
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print(f"Found {len(tables)} tables.")

    for (table_name,) in tables:
        print(f"\nTABLE: {table_name}")
        columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        # cid, name, type, notnull, dflt_value, pk
        for col in columns:
            pk_str = " (PK)" if col[5] else ""
            print(f"  - {col[1]:<20} {col[2]:<10} {pk_str}")

except Exception as e:
    print(e)
finally:
    if "conn" in locals():
        conn.close()
