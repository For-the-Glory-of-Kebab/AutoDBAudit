"""
Simplified Test for Enhanced Excel Report V2
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from autodbaudit.infrastructure.sql.connector import SqlConnector
from autodbaudit.infrastructure.sql.query_provider import get_query_provider
from autodbaudit.infrastructure.excel import EnhancedReportWriter


def generate_report() -> None:
    """Generate report from SQL Server."""
    print("\n" + "=" * 60)
    print("ENHANCED EXCEL REPORT V2 - TEST")
    print("=" * 60)
    
    # Connect
    print("\n1. Connect...")
    conn = SqlConnector("localhost\\INTHEEND", "sql", "sa", "K@vand24")
    if not conn.test_connection():
        print("   FAIL")
        return
    print("   OK")
    
    info = conn.detect_version()
    prov = get_query_provider(info.version_major)
    sn = info.server_name.split("\\")[0]
    inst = info.instance_name or ""
    
    # Create writer
    w = EnhancedReportWriter()
    w.set_audit_info(1, "Test Corp", datetime.now())
    
    print("\n2. Collect data...")
    
    # INSTANCES
    print("   Instances...", end=" ")
    props = conn.execute_query(prov.get_instance_properties())
    if props:
        p = props[0]
        w.add_instance(
            server_name=sn,
            instance_name=inst, 
            version=p.get("Version", ""),
            version_major=p.get("VersionMajor", 0), 
            edition=p.get("Edition", ""),
            product_level=p.get("ProductLevel", ""), 
            is_clustered=bool(p.get("IsClustered")),
            is_hadr=False,
            ip_address="127.0.0.1",  # Localhost for testing
            os_version=p.get("OSVersion", "Windows Server"),
        )
    print("OK")
    
    # SA ACCOUNT
    print("   SA Account...", end=" ")
    logins = conn.execute_query(prov.get_server_logins())
    for l in logins:
        if l.get("IsSA"):
            w.add_sa_account(sn, inst, bool(l.get("IsDisabled")), 
                            l.get("LoginName", "sa").lower() != "sa",
                            l.get("LoginName", "sa"), l.get("DefaultDatabase", ""))
            if not l.get("IsDisabled"):
                w.add_action(sn, inst, "SA Account", "SA enabled", "critical", "Disable SA")
            break
    print("OK")
    
    # LOGINS
    print("   Logins...", end=" ")
    for l in logins:
        w.add_login(sn, inst, l.get("LoginName", ""), l.get("LoginType", ""),
                   bool(l.get("IsDisabled")), bool(l.get("IsSA")),
                   l.get("PasswordPolicyEnforced"), l.get("DefaultDatabase", ""))
    print(f"OK ({len(logins)})")
    
    # ROLES
    print("   Roles...", end=" ")
    roles = conn.execute_query(prov.get_server_role_members())
    for r in roles:
        w.add_role_member(sn, inst, r.get("RoleName", ""), r.get("MemberName", ""),
                         r.get("MemberType", ""), bool(r.get("MemberDisabled")))
    print(f"OK ({len(roles)})")
    
    # CONFIG
    print("   Config...", end=" ")
    configs = conn.execute_query(prov.get_advanced_options())
    for c in configs:
        n = c.get("SettingName", "")
        if n in ("xp_cmdshell", "remote access", "clr enabled"):
            w.add_config_setting(sn, inst, n, c.get("CurrentValue", 0), 0)
    print("OK")
    
    # SERVICES (mock)
    print("   Services...", end=" ")
    w.add_service(sn, "Engine", f"MSSQL${inst}", "Running", "Auto", f"NT Service\\MSSQL${inst}", True)
    w.add_service(sn, "Agent", f"Agent${inst}", "Running", "Auto", f"NT Service\\Agent${inst}", True)
    print("OK")
    
    # DATABASES
    print("   Databases...", end=" ")
    dbs = conn.execute_query(prov.get_databases())
    for d in dbs:
        w.add_database(sn, inst, d.get("DatabaseName", ""), d.get("Owner", ""),
                      d.get("RecoveryModel", ""), d.get("State", ""),
                      (d.get("DataSizeMB") or 0), bool(d.get("IsTrustworthy")))
    print(f"OK ({len(dbs)})")
    
    # DB USERS
    print("   DB Users...", end=" ")
    user_cnt = 0
    for d in dbs:
        dn = d.get("DatabaseName", "")
        if dn in ("master", "model", "msdb", "tempdb"):
            continue
        try:
            users = conn.execute_query(prov.get_database_users(dn))
            for u in users:
                w.add_db_user(sn, inst, dn, u.get("UserName", ""), u.get("UserType", ""),
                             u.get("MappedLogin"), bool(u.get("IsOrphaned")))
                user_cnt += 1
        except: pass
    print(f"OK ({user_cnt})")
    
    # DB ROLES
    print("   DB Roles...", end=" ")
    role_cnt = 0
    for d in dbs:
        dn = d.get("DatabaseName", "")
        if dn in ("master", "model", "msdb", "tempdb"):
            continue
        try:
            rls = conn.execute_query(prov.get_database_role_members(dn))
            for r in rls:
                w.add_db_role_member(sn, inst, dn, r.get("RoleName", ""), 
                                     r.get("MemberName", ""), r.get("MemberType", ""))
                role_cnt += 1
        except: pass
    print(f"OK ({role_cnt})")
    
    # LINKED SERVERS
    print("   Linked...", end=" ")
    ls = conn.execute_query(prov.get_linked_servers())
    for x in ls:
        w.add_linked_server(sn, inst, x.get("LinkedServerName", ""), x.get("Product", ""),
                           x.get("Provider", ""), x.get("DataSource", ""), bool(x.get("RpcOutEnabled")))
    print(f"OK ({len(ls)})")
    
    # TRIGGERS
    print("   Triggers...", end=" ")
    trg = conn.execute_query(prov.get_server_triggers())
    for t in trg:
        w.add_trigger(sn, inst, "SERVER", None, t.get("TriggerName", ""), 
                     t.get("EventType", ""), not bool(t.get("IsDisabled")))
    print(f"OK ({len(trg)})")
    
    # BACKUPS  
    print("   Backups...", end=" ")
    bk = conn.execute_query(prov.get_backup_history())
    for b in bk:
        w.add_backup_info(sn, inst, b.get("DatabaseName", ""), b.get("RecoveryModel", ""),
                         b.get("BackupDate"), b.get("DaysSinceBackup"))
    print(f"OK ({len(bk)})")
    
    # AUDIT SETTINGS
    print("   Audit...", end=" ")
    aud = conn.execute_query(prov.get_audit_settings())
    if aud:
        w.add_audit_setting(sn, inst, "Default Trace", str(aud[0].get("DefaultTraceEnabled", 0)), "1")
    print("OK")
    
    # SAVE
    print("\n3. Save...")
    out = Path(f"output/modular_test_{datetime.now().strftime('%H%M%S')}.xlsx")
    w.save(out)
    
    print(f"\n{'=' * 60}")
    print(f"SUCCESS: {out.absolute()}")
    print(f"Size: {out.stat().st_size:,} bytes | Sheets: {len(w.wb.sheetnames)}")
    for s in w.wb.sheetnames:
        print(f"   - {s}")


if __name__ == "__main__":
    generate_report()
