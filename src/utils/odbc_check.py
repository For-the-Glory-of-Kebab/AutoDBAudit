"""
ODBC driver detection and diagnostics.

Utility to check available SQL Server ODBC drivers on the system.
"""

import pyodbc
import logging


logger = logging.getLogger(__name__)


def check_odbc_drivers():
    """
    Check and display available ODBC drivers.
    
    Prints driver information to console and logs.
    """
    drivers = pyodbc.drivers()
    
    print("\n" + "=" * 60)
    print("Available ODBC Drivers")
    print("=" * 60)
    
    if not drivers:
        print("❌ No ODBC drivers found!")
        print("\nPlease install Microsoft ODBC Driver 17 or 18 for SQL Server")
        logger.error("No ODBC drivers detected")
        return
    
    # Categorize drivers
    sql_server_drivers = []
    other_drivers = []
    
    for driver in drivers:
        if "SQL Server" in driver:
            sql_server_drivers.append(driver)
        else:
            other_drivers.append(driver)
    
    # Display SQL Server drivers
    if sql_server_drivers:
        print("\n✅ SQL Server Drivers:")
        for driver in sorted(sql_server_drivers, reverse=True):
            if "ODBC Driver" in driver:
                version = driver.split("ODBC Driver ")[1].split(" ")[0]
                status = "✅ RECOMMENDED" if int(version) >= 17 else "⚠️  Legacy"
                print(f"  - {driver} {status}")
            else:
                print(f"  - {driver} ⚠️  Legacy/Fallback")
    else:
        print("\n❌ No SQL Server ODBC drivers found!")
        print("   Please install: ODBC Driver 18 for SQL Server")
    
    # Display other drivers
    if other_drivers and len(other_drivers) <= 5:
        print(f"\nℹ️  Other ODBC drivers ({len(other_drivers)}):")
        for driver in sorted(other_drivers):
            print(f"  - {driver}")
    elif other_drivers:
        print(f"\nℹ️  {len(other_drivers)} other ODBC drivers available")
    
    print("=" * 60 + "\n")
    
    # Log summary
    logger.info(f"ODBC drivers detected: {len(drivers)} total, "
               f"{len(sql_server_drivers)} SQL Server")
