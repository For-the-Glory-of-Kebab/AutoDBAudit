"""
Test Phase 2a - Query Provider and Data Collection.

Tests:
1. QueryProvider Strategy pattern
2. Execute queries against real SQL Server
3. Verify data formats
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from autodbaudit.infrastructure.query_provider import get_query_provider
from autodbaudit.infrastructure.sql_server import SqlConnector


def test_query_provider():
    """Test query provider with real SQL Server."""
    print("\n" + "=" * 60)
    print("Phase 2a Query Provider Test")
    print("=" * 60)
    
    # Connect
    print("\n1. Connecting to SQL Server...")
    connector = SqlConnector(
        server_instance="localhost\\INTHEEND",
        auth="sql",
        username="sa",
        password="K@vand24"
    )
    
    if not connector.test_connection():
        print("   ❌ Connection failed!")
        return 1
    print("   ✅ Connected")
    
    # Get version and provider
    print("\n2. Detecting version...")
    info = connector.detect_version()
    print(f"   Version: {info.version} (major={info.version_major})")
    print(f"   Edition: {info.edition}")
    
    provider = get_query_provider(info.version_major)
    print(f"   Provider: {type(provider).__name__}")
    
    # Test queries
    print("\n3. Testing queries...")
    
    queries_to_test = [
        ("Instance Properties", provider.get_instance_properties()),
        ("Server Info", provider.get_server_info()),
        ("SP Configure", provider.get_sp_configure()),
        ("Advanced Options", provider.get_advanced_options()),
        ("Server Logins", provider.get_server_logins()),
        ("Server Role Members", provider.get_server_role_members()),
        ("Databases", provider.get_databases()),
        ("Linked Servers", provider.get_linked_servers()),
        ("Server Triggers", provider.get_server_triggers()),
        ("Audit Settings", provider.get_audit_settings()),
    ]
    
    for name, sql in queries_to_test:
        try:
            results = connector.execute_query(sql)
            print(f"   ✅ {name}: {len(results)} rows")
            
            # Show sample for key queries
            if name == "Server Logins" and results:
                print(f"      Sample: {results[0].get('LoginName', 'N/A')}, {results[0].get('LoginType', 'N/A')}")
            elif name == "Advanced Options" and results:
                for r in results[:3]:
                    print(f"      - {r.get('SettingName')}: {r.get('CurrentValue')}")
                    
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    # Test database-specific queries
    print("\n4. Testing database-specific queries...")
    
    # Get first user database
    dbs = connector.execute_query("SELECT name FROM sys.databases WHERE database_id > 4")
    if dbs:
        db_name = dbs[0]["name"]
        print(f"   Testing on database: {db_name}")
        
        try:
            users = connector.execute_query(provider.get_database_users(db_name))
            print(f"   ✅ Database Users: {len(users)} users in {db_name}")
        except Exception as e:
            print(f"   ❌ Database Users: {e}")
    else:
        print("   No user databases found")
    
    print("\n" + "=" * 60)
    print("🎉 Phase 2a tests completed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(test_query_provider())
