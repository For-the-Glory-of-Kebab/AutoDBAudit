"""
Test script to validate project setup and imports.

Run this to verify:
- All dependencies installed correctly
- Imports work
- Basic functionality operational
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test all core imports."""
    print("=" * 60)
    print("Testing AutoDBAudit Project Setup (Refactored Layout)")
    print("=" * 60)
    
    try:
        print("\n✓ Testing stdlib imports...")
        import json
        import logging
        from pathlib import Path
        from dataclasses import dataclass
        print("  ✅ Stdlib imports OK")
        
        print("\n✓ Testing pyodbc...")
        import pyodbc
        drivers = pyodbc.drivers()
        print(f"  ✅ pyodbc OK - {len(drivers)} ODBC drivers found")
        
        print("\n✓ Testing openpyxl...")
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws['A1'] = "Test"
        print("  ✅ openpyxl OK - Workbook creation successful")
        
        print("\n✓ Testing pywin32...")
        import win32crypt
        print("  ✅ pywin32 OK - DPAPI available")
        
        print("\n✓ Testing project modules (NEW LAYOUT)...")
        from autodbaudit.infrastructure.config_loader import ConfigLoader, SqlTarget, AuditConfig
        from autodbaudit.infrastructure.sql.connector import SqlConnector, SqlServerInfo
        from autodbaudit.application.audit_service import AuditService
        from autodbaudit.infrastructure.logging_config import setup_logging
        from autodbaudit.infrastructure.odbc_check import check_odbc_drivers
        from autodbaudit.infrastructure.sql_queries import load_queries_for_version
        print("  ✅ All project modules import successfully")
        
        print("\n✓ Testing dataclass instantiation...")
        target = SqlTarget(
            id="test1",
            server="localhost",
            instance="SQLEXPRESS",
            auth="integrated"
        )
        print(f"  ✅ SqlTarget created: {target.display_name}")
        
        print("\n✓ Testing ConfigLoader...")
        config_loader = ConfigLoader("config")
        print("  ✅ ConfigLoader instantiated")
        
        print("\n✓ Testing AuditService...")
        audit_service = AuditService()
        print("  ✅ AuditService instantiated")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Project setup complete!")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
