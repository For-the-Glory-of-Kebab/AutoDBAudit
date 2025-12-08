"""
Comprehensive Multi-Instance Test Script.

Tests ALL sheets for SQL Server 2008, 2022, and 2025 instances.
"""

import json
from datetime import datetime
from pathlib import Path

from autodbaudit.infrastructure.sql.connector import SqlConnector
from autodbaudit.infrastructure.sql.query_provider import get_query_provider
from autodbaudit.infrastructure.excel import EnhancedReportWriter


def load_targets() -> list:
    """Load SQL targets from config file."""
    with open("config/sql_targets.json", encoding="utf-8") as f:
        return json.load(f)["targets"]


def test_instance(target: dict, writer: EnhancedReportWriter) -> bool:
    """Test a single SQL Server instance and collect ALL data."""
    name = target.get("display_name", target["server"])
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    # Build server\\instance string
    server = target["server"]
    instance = target.get("instance", "")
    server_instance = f"{server}\\{instance}" if instance else server
    
    # Create connector
    auth_mode = "sql" if target.get("auth") == "sql" else "integrated"
    conn = SqlConnector(
        server_instance=server_instance,
        auth=auth_mode,
        username=target.get("username"),
        password=target.get("password"),
    )
    
    # Test connection
    print("   Testing connection...", end=" ")
    if not conn.test_connection():
        print("FAILED")
        return False
    print("OK")
    
    try:
        # Get version and query provider
        version = conn.detect_version()
        print(f"   Version: SQL {version.version_major} ({version.version})")
        prov = get_query_provider(version.version_major)
        print(f"   Provider: {type(prov).__name__}")
        
        sn = target["server"]
        inst = target.get("instance", "")
        
        # ================================================================
        # 1. INSTANCE PROPERTIES
        # ================================================================
        print("   [1/12] Instance...", end=" ")
        props = conn.execute_query(prov.get_instance_properties())
        if props:
            p = props[0]
            # Build OS info string
            os_platform = p.get("OSPlatform", "")
            os_distro = p.get("OSDistribution", "")
            os_release = p.get("OSRelease", "")
            if os_distro:
                os_info = f"{os_distro} ({os_release})" if os_release else os_distro
            elif os_platform:
                os_info = os_platform
            else:
                # Try to extract from @@VERSION for SQL 2008
                full_ver = p.get("FullVersionString", "")
                if "Windows" in str(full_ver):
                    # Extract Windows version from @@VERSION
                    os_info = "Windows"
                else:
                    os_info = ""
            
            # Get config name from target
            config_name = target.get("display_name", sn)
            
            # Get machine name from SQL
            machine_name = p.get("MachineName", "") or p.get("PhysicalMachine", "")
            
            # Get IP: prioritize config > DMV, show both if available
            config_ip = target.get("ip_address", "")
            dmv_ip = p.get("IPAddress", "")
            tcp_port = p.get("TCPPort")
            
            # Combine IPs: use config IP primarily, add DMV binding if different
            if config_ip and dmv_ip and config_ip != dmv_ip:
                # Show both: config IP (reported binding)
                ip_address = f"{config_ip} ({dmv_ip})"
            elif config_ip:
                ip_address = config_ip
            else:
                ip_address = dmv_ip
            
            writer.add_instance(
                config_name=config_name,
                server_name=sn,
                instance_name=inst,
                machine_name=machine_name,
                ip_address=ip_address,
                tcp_port=tcp_port,
                version=p.get("Version", ""),
                version_major=p.get("VersionMajor", 0),
                edition=p.get("Edition", ""),
                product_level=p.get("ProductLevel", ""),
                is_clustered=bool(p.get("IsClustered")),
                is_hadr=bool(p.get("IsHadrEnabled")),
                os_info=os_info,
                cpu_count=p.get("CPUCount"),
                memory_gb=p.get("MemoryGB"),
                cu_level=p.get("CULevel", ""),
                build_number=p.get("BuildNumber"),
            )
        print("OK")
        
        # ================================================================
        # 2. SA ACCOUNT DETECTION
        # ================================================================
        print("   [2/12] SA Account...", end=" ")
        logins = conn.execute_query(prov.get_server_logins())
        sa_found = False
        for lg in logins:
            # Check for SA (sid = 0x01) or renamed SA (like $@)
            is_sa = bool(lg.get("IsSA"))
            login_name = lg.get("LoginName", "")
            
            if is_sa:
                sa_found = True
                is_disabled = bool(lg.get("IsDisabled"))
                # SA is renamed if name is not "sa"
                is_renamed = login_name.lower() != "sa"
                
                writer.add_sa_account(
                    server_name=sn,
                    instance_name=inst,
                    is_disabled=is_disabled,
                    is_renamed=is_renamed,
                    current_name=login_name,
                    default_db=lg.get("DefaultDatabase", "master"),
                )
        if not sa_found:
            print("WARN (no SA found)")
        else:
            print("OK")
        
        # ================================================================
        # 3. SERVER LOGINS
        # ================================================================
        print("   [3/12] Logins...", end=" ")
        for lg in logins:
            writer.add_login(
                server_name=sn,
                instance_name=inst,
                login_name=lg.get("LoginName", ""),
                login_type=lg.get("LoginType", ""),
                is_disabled=bool(lg.get("IsDisabled")),
                pwd_policy=lg.get("PasswordPolicyEnforced"),
                default_db=lg.get("DefaultDatabase", ""),
            )
        print(f"OK ({len(logins)})")
        
        # ================================================================
        # 4. SERVER ROLES
        # ================================================================
        print("   [4/12] Roles...", end=" ")
        roles = conn.execute_query(prov.get_server_role_members())
        for r in roles:
            writer.add_role_member(
                server_name=sn,
                instance_name=inst,
                role_name=r.get("RoleName", ""),
                member_name=r.get("MemberName", ""),
                member_type=r.get("MemberType", ""),
                is_disabled=bool(r.get("MemberDisabled")),
            )
        print(f"OK ({len(roles)})")
        
        # ================================================================
        # 5. CONFIGURATION (sp_configure)
        # ================================================================
        print("   [5/12] Config...", end=" ")
        try:
            configs = conn.execute_query(prov.get_sp_configure())
            # Security-relevant settings per db-requirements.md
            # Required value is the secure default (usually 0 = disabled)
            security_settings = {
                # HIGH RISK - command execution
                "xp_cmdshell": (0, "high"),                       # Req #10
                "Ole Automation Procedures": (0, "high"),         # OLE attack surface
                
                # MEDIUM RISK - feature surface area
                "clr enabled": (0, "medium"),                     # CLR code execution
                "clr strict security": (1, "medium"),             # CLR security (2017+)
                "Ad Hoc Distributed Queries": (0, "medium"),      # Req #16
                "Database Mail XPs": (0, "medium"),               # Req #18
                "cross db ownership chaining": (0, "medium"),     # Cross-DB access
                "remote access": (0, "medium"),                   # Req #20
                "remote admin connections": (0, "medium"),        # DAC remote
                "scan for startup procs": (0, "medium"),          # Auto-exec procs
                "external scripts enabled": (0, "medium"),        # R/Python exec
                
                # LOW RISK - monitoring/info
                "show advanced options": (0, "low"),              # Hides advanced
                "default trace enabled": (1, "low"),              # Audit trace
            }
            config_count = 0
            for cfg in configs:
                setting_name = cfg.get("SettingName", "")  # Fixed: was "Name"
                setting_key = setting_name.lower()
                
                # Check against our security settings (case-insensitive)
                match = None
                for key, (required, risk) in security_settings.items():
                    if key.lower() == setting_key:
                        match = (required, risk, key)
                        break
                
                if match:
                    required, risk, display_name = match
                    current = cfg.get("RunningValue", 0) or 0  # Fixed: was ConfigValue
                    writer.add_config_setting(
                        server_name=sn,
                        instance_name=inst,
                        setting_name=setting_name,
                        current_value=int(current),
                        required_value=required,
                        risk_level=risk,
                    )
                    config_count += 1
            print(f"OK ({config_count})")
        except Exception as e:
            print(f"SKIP ({e})")
        
        # ================================================================
        # 6. SERVICES
        # ================================================================
        print("   [6/12] Services...", end=" ")
        try:
            services = conn.execute_query(prov.get_sql_services())
            
            # Build list of services with their instance assignments
            service_list = []
            for svc in services:
                # Use InstanceName from query if available
                svc_instance = svc.get("InstanceName") or inst or "(Default)"
                
                # For shared services (no instance in name), use "(Shared)"
                svc_type = svc.get("ServiceType", "Other")
                if svc_type in ("SQL Browser", "VSS Writer", "Integration Services"):
                    svc_instance = "(Shared)"
                
                service_list.append({
                    "instance": svc_instance,
                    "name": svc.get("ServiceName") or svc.get("DisplayName", ""),
                    "type": svc_type,
                    "status": svc.get("Status", "Unknown"),
                    "startup": svc.get("StartupType", ""),
                    "account": svc.get("ServiceAccount", ""),
                })
            
            # Sort by instance name to group services together
            # Put (Shared) at the end
            def sort_key(s):
                inst = s["instance"]
                if inst == "(Shared)":
                    return ("Z", inst)  # Sort to end
                return ("A", inst)
            
            service_list.sort(key=sort_key)
            
            # Add sorted services
            for svc in service_list:
                writer.add_service(
                    server_name=sn,
                    instance_name=svc["instance"],
                    service_name=svc["name"],
                    service_type=svc["type"],
                    status=svc["status"],
                    startup_type=svc["startup"],
                    service_account=svc["account"],
                )
            print(f"OK ({len(service_list)})")
        except Exception as e:
            print(f"SKIP ({e})")
        
        # ================================================================
        # 7. DATABASES
        # ================================================================
        print("   [7/12] Databases...", end=" ")
        dbs = conn.execute_query(prov.get_databases())
        user_dbs = [db for db in dbs if db.get("DatabaseName") not in 
                    ("master", "tempdb", "model", "msdb")]
        for db in dbs:
            writer.add_database(
                server_name=sn,
                instance_name=inst,
                database_name=db.get("DatabaseName", ""),
                owner=db.get("Owner", ""),
                recovery_model=db.get("RecoveryModel", ""),
                state=db.get("State", ""),
                data_size_mb=db.get("DataSizeMB") or db.get("SizeMB"),
                log_size_mb=db.get("LogSizeMB"),
                is_trustworthy=bool(db.get("IsTrustworthy")),
            )
        print(f"OK ({len(dbs)})")
        
        # ================================================================
        # 8. DATABASE USERS (per-database)
        # ================================================================
        print("   [8/12] DB Users...", end=" ")
        user_count = 0
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            state = db.get("State", "ONLINE")
            if state != "ONLINE":
                continue  # Skip offline/restoring databases
            try:
                users = conn.execute_query(prov.get_database_users(db_name))
                for u in users:
                    user_name = u.get("UserName", "")
                    mapped_login = u.get("MappedLogin")
                    user_type = u.get("UserType", "")
                    
                    # Determine orphan status (no mapped login for SQL/Windows users)
                    is_orphaned = (
                        mapped_login is None and 
                        user_type in ("SQL_USER", "WINDOWS_USER") and
                        user_name not in ("dbo", "guest", "INFORMATION_SCHEMA", "sys")
                    )
                    
                    # Check if GUEST has CONNECT permission (security issue)
                    guest_enabled = bool(u.get("GuestEnabled"))
                    
                    writer.add_db_user(
                        server_name=sn,
                        instance_name=inst,
                        database_name=db_name,
                        user_name=user_name,
                        user_type=user_type,
                        mapped_login=mapped_login,
                        is_orphaned=is_orphaned,
                        has_connect=guest_enabled if user_name.lower() == "guest" else True,
                    )
                    user_count += 1
                    
                    # Also add to Orphaned Users sheet if orphaned (non-system)
                    if is_orphaned:
                        writer.add_orphaned_user(
                            server_name=sn,
                            instance_name=inst,
                            database_name=db_name,
                            user_name=user_name,
                            user_type=user_type,
                        )
            except Exception:
                pass  # Skip databases we can't access
        print(f"OK ({user_count})")
        
        # ================================================================
        # 9. DATABASE ROLES (per-database)
        # ================================================================
        print("   [9/12] DB Roles...", end=" ")
        role_count = 0
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            state = db.get("State", "ONLINE")
            if state != "ONLINE":
                continue
            try:
                db_roles = conn.execute_query(prov.get_database_role_members(db_name))
                for r in db_roles:
                    writer.add_db_role_member(
                        server_name=sn,
                        instance_name=inst,
                        database_name=db_name,
                        role_name=r.get("RoleName", ""),
                        member_name=r.get("MemberName", ""),
                        member_type=r.get("MemberType", ""),
                    )
                    role_count += 1
            except Exception:
                pass
        print(f"OK ({role_count})")
        
        # ================================================================
        # 10. LINKED SERVERS
        # ================================================================
        print("   [10/12] Linked Servers...", end=" ")
        linked_count = 0
        try:
            linked = conn.execute_query(prov.get_linked_servers())
            login_mappings = conn.execute_query(prov.get_linked_server_logins())
            
            # Build mapping dict: linked_server_name -> (local, remote, impersonate, risk)
            # Pick the highest-risk mapping for display
            mapping_info: dict[str, tuple[str, str, bool, str]] = {}
            for m in login_mappings:
                ls_name = m.get("LinkedServerName", "")
                remote = m.get("RemoteLogin") or ""
                local = m.get("LocalLogin", "")
                impersonate = bool(m.get("Impersonate"))
                risk = m.get("RiskLevel", "NORMAL")
                
                # Store if not yet recorded, or if this is higher risk
                if ls_name not in mapping_info or risk == "HIGH_PRIVILEGE":
                    mapping_info[ls_name] = (local, remote, impersonate, risk)
            
            for ls in linked:
                ls_name = ls.get("LinkedServerName", "")
                local, remote, impersonate, risk = mapping_info.get(ls_name, ("", "", False, ""))
                
                writer.add_linked_server(
                    server_name=sn,
                    instance_name=inst,
                    linked_server_name=ls_name,
                    product=ls.get("Product") or "",
                    provider=ls.get("Provider") or "",
                    data_source=ls.get("DataSource") or "",
                    rpc_out=bool(ls.get("RpcOutEnabled")),
                    local_login=local,
                    remote_login=remote,
                    impersonate=impersonate,
                    risk_level=risk,
                )
                linked_count += 1
            print(f"OK ({linked_count})")
        except Exception as e:
            print(f"SKIP ({e})")
        
        # ================================================================
        # 11. TRIGGERS (Server + Database level)
        # ================================================================
        print("   [11/12] Triggers...", end=" ")
        trigger_count = 0
        
        # Server-level triggers
        try:
            server_triggers = conn.execute_query(prov.get_server_triggers())
            for t in server_triggers:
                writer.add_trigger(
                    server_name=sn,
                    instance_name=inst,
                    level="SERVER",
                    database_name=None,
                    trigger_name=t.get("TriggerName", ""),
                    event_type=t.get("EventType", ""),
                    is_enabled=bool(t.get("IsEnabled")),
                )
                trigger_count += 1
        except Exception:
            pass
        
        # Database-level triggers
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            state = db.get("State", "ONLINE")
            if state != "ONLINE":
                continue
            try:
                db_triggers = conn.execute_query(prov.get_database_triggers(db_name))
                for t in db_triggers:
                    writer.add_trigger(
                        server_name=sn,
                        instance_name=inst,
                        level="DATABASE",
                        database_name=db_name,
                        trigger_name=t.get("TriggerName", ""),
                        event_type=t.get("EventType", ""),
                        is_enabled=bool(t.get("IsEnabled")),
                    )
                    trigger_count += 1
            except Exception:
                pass
        print(f"OK ({trigger_count})")
        
        # ================================================================
        # 12. BACKUPS
        # ================================================================
        print("   [12/12] Backups...", end=" ")
        try:
            backups = conn.execute_query(prov.get_backup_history())
            for b in backups:
                writer.add_backup_info(
                    server_name=sn,
                    instance_name=inst,
                    database_name=b.get("DatabaseName", ""),
                    recovery_model=b.get("RecoveryModel", ""),
                    last_backup_date=b.get("BackupDate"),
                    days_since=b.get("DaysSinceBackup"),
                    backup_path=b.get("BackupPath", ""),
                    backup_size_mb=b.get("BackupSizeMB"),
                )
            print(f"OK ({len(backups)})")
        except Exception as e:
            print(f"SKIP ({e})")
        
        # ================================================================
        # AUDIT SETTINGS
        # ================================================================
        print("   [+] Audit Settings...", end=" ")
        try:
            audit = conn.execute_query(prov.get_audit_settings())
            for a in audit:
                writer.add_audit_setting(
                    server_name=sn,
                    instance_name=inst,
                    setting_name=a.get("SettingName", "Login Auditing"),
                    current_value=a.get("CurrentValue", ""),
                    recommended_value="All",  # Best practice: audit all logins
                )
            print("OK")
        except Exception as e:
            print(f"SKIP ({e})")
        
        return True
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    print("=" * 60)
    print("COMPREHENSIVE MULTI-INSTANCE TEST")
    print("=" * 60)
    
    targets = load_targets()
    print(f"\nFound {len(targets)} targets in config")
    
    # Create single writer for all instances
    writer = EnhancedReportWriter()
    writer.set_audit_info(1, "Multi-Instance Security Audit", datetime.now())
    
    results = {}
    for target in targets:
        if not target.get("enabled", True):
            print(f"\nSkipping disabled: {target.get('display_name', 'Unknown')}")
            continue
        
        success = test_instance(target, writer)
        results[target.get("display_name", "Unknown")] = success
    
    # Save report
    print("\n" + "=" * 60)
    print("Saving report...")
    ts = datetime.now().strftime("%H%M%S")
    out = Path(f"output/full_audit_{ts}.xlsx")
    writer.save(out)
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"   {status} | {name}")
    
    print(f"\nReport: {out.absolute()}")
    print(f"Size: {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
