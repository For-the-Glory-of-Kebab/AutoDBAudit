"""
SQL Query Provider - Strategy Pattern for version-specific queries.

Provides a clean abstraction for SQL Server version differences:
- Sql2008Provider: Compatible with SQL Server 2008/2008 R2
- Sql2019PlusProvider: Uses modern features (STRING_AGG, etc.)

Usage:
    provider = get_query_provider(version_major=15)  # SQL 2019
    sql = provider.get_server_logins()
    results = connector.execute_query(sql)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class SqlVersion(Enum):
    """SQL Server major version identifiers."""
    SQL_2008 = 10
    SQL_2012 = 11
    SQL_2014 = 12
    SQL_2016 = 13
    SQL_2017 = 14
    SQL_2019 = 15
    SQL_2022 = 16


@dataclass(frozen=True)
class QueryInfo:
    """Metadata about a SQL query."""
    name: str
    description: str
    min_version: int = 10  # Minimum SQL Server major version
    category: str = "general"


class QueryProvider(ABC):
    """
    Abstract base class for version-specific SQL queries.
    
    Each method returns a SQL query string appropriate for
    the SQL Server version this provider supports.
    """
    
    # Override in subclasses
    VERSION_NAME: ClassVar[str] = "Unknown"
    MIN_VERSION: ClassVar[int] = 10
    MAX_VERSION: ClassVar[int] = 99
    
    # ========================================================================
    # Server Information
    # ========================================================================
    
    @abstractmethod
    def get_server_info(self) -> str:
        """Get server OS and installation information."""
    
    @abstractmethod
    def get_instance_properties(self) -> str:
        """Get SQL Server instance properties."""
    
    # ========================================================================
    # Services
    # ========================================================================
    
    @abstractmethod
    def get_sql_services(self) -> str:
        """Get SQL Server services (requires xp_regread or WMI)."""
    
    # ========================================================================
    # Configuration
    # ========================================================================
    
    @abstractmethod
    def get_sp_configure(self) -> str:
        """Get all sp_configure settings."""
    
    @abstractmethod
    def get_advanced_options(self) -> str:
        """Get advanced configuration options."""
    
    # ========================================================================
    # Security - Logins
    # ========================================================================
    
    @abstractmethod
    def get_server_logins(self) -> str:
        """Get all server logins with properties."""
    
    @abstractmethod
    def get_server_role_members(self) -> str:
        """Get server role memberships."""
    
    @abstractmethod
    def get_login_permissions(self) -> str:
        """Get server-level permissions for logins."""
    
    # ========================================================================
    # Security - Databases
    # ========================================================================
    
    @abstractmethod
    def get_databases(self) -> str:
        """Get all databases with properties."""
    
    @abstractmethod
    def get_database_users(self, database: str) -> str:
        """Get users for a specific database."""
    
    @abstractmethod
    def get_database_role_members(self, database: str) -> str:
        """Get database role memberships."""
    
    @abstractmethod
    def get_orphaned_users(self, database: str) -> str:
        """Get orphaned database users."""
    
    # ========================================================================
    # Linked Servers
    # ========================================================================
    
    @abstractmethod
    def get_linked_servers(self) -> str:
        """Get all linked servers with configuration."""
    
    @abstractmethod
    def get_linked_server_logins(self) -> str:
        """Get linked server login mappings."""
    
    # ========================================================================
    # Triggers
    # ========================================================================
    
    @abstractmethod
    def get_server_triggers(self) -> str:
        """Get server-level (DDL) triggers."""
    
    @abstractmethod
    def get_database_triggers(self, database: str) -> str:
        """Get database-level triggers."""
    
    # ========================================================================
    # Backups
    # ========================================================================
    
    @abstractmethod
    def get_backup_history(self) -> str:
        """Get backup history from msdb."""
    
    @abstractmethod
    def get_backup_jobs(self) -> str:
        """Get SQL Agent jobs related to backups."""
    
    # ========================================================================
    # Audit Settings
    # ========================================================================
    
    @abstractmethod
    def get_audit_settings(self) -> str:
        """Get login audit and security settings."""


class Sql2008Provider(QueryProvider):
    """
    Query provider for SQL Server 2008/2008 R2.
    
    Avoids features not available in 2008:
    - No STRING_AGG (use FOR XML PATH)
    - No TRY_CAST (use CASE with ISNUMERIC)
    - Different DMV structure
    - physical_memory_in_bytes instead of physical_memory_kb
    """
    
    VERSION_NAME = "SQL Server 2008/2008R2"
    MIN_VERSION = 10
    MAX_VERSION = 10
    
    def get_server_info(self) -> str:
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            CAST(SERVERPROPERTY('MachineName') AS NVARCHAR(256)) AS MachineName,
            CAST(SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS NVARCHAR(256)) AS PhysicalName,
            (SELECT cpu_count FROM sys.dm_os_sys_info) AS CPU_Count,
            (SELECT physical_memory_in_bytes/1024/1024/1024 FROM sys.dm_os_sys_info) AS Memory_GB,
            (SELECT sqlserver_start_time FROM sys.dm_os_sys_info) AS SQL_Start_Time,
            CAST(SERVERPROPERTY('Collation') AS NVARCHAR(256)) AS Collation,
            CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS INT) AS WindowsAuthOnly,
            CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered,
            CAST(SERVERPROPERTY('IsHadrEnabled') AS INT) AS IsHadrEnabled
        """
    
    def get_instance_properties(self) -> str:
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(256)) AS InstanceName,
            CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS Version,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 4) AS INT) AS VersionMajor,
            CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256)) AS Edition,
            CAST(SERVERPROPERTY('ProductLevel') AS NVARCHAR(128)) AS ProductLevel,
            CAST(SERVERPROPERTY('EngineEdition') AS INT) AS EngineEdition,
            CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered,
            CAST(SERVERPROPERTY('IsFullTextInstalled') AS INT) AS IsFullTextInstalled,
            CAST(SERVERPROPERTY('LicenseType') AS NVARCHAR(128)) AS LicenseType
        """
    
    def get_sql_services(self) -> str:
        # 2008: Limited ability to query services from T-SQL
        # This returns a placeholder - actual service info comes from WMI/PowerShell
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            'SQL Server' AS ServiceType,
            @@SERVICENAME AS ServiceName,
            'Information requires WMI query' AS Note
        """
    
    def get_sp_configure(self) -> str:
        return """
        SELECT 
            name AS SettingName,
            CAST(value AS INT) AS ConfiguredValue,
            CAST(value_in_use AS INT) AS RunningValue,
            CAST(minimum AS INT) AS MinValue,
            CAST(maximum AS INT) AS MaxValue,
            CAST(is_dynamic AS INT) AS IsDynamic,
            CAST(is_advanced AS INT) AS IsAdvanced,
            description AS Description
        FROM sys.configurations
        ORDER BY name
        """
    
    def get_advanced_options(self) -> str:
        return """
        SELECT 
            name AS SettingName,
            CAST(value_in_use AS INT) AS CurrentValue
        FROM sys.configurations
        WHERE name IN (
            'xp_cmdshell',
            'Ole Automation Procedures', 
            'clr enabled',
            'cross db ownership chaining',
            'Ad Hoc Distributed Queries',
            'remote access',
            'Database Mail XPs',
            'scan for startup procs',
            'show advanced options'
        )
        """
    
    def get_server_logins(self) -> str:
        return """
        SELECT 
            p.name AS LoginName,
            p.principal_id AS PrincipalId,
            p.type_desc AS LoginType,
            p.is_disabled AS IsDisabled,
            p.create_date AS CreateDate,
            p.modify_date AS ModifyDate,
            p.default_database_name AS DefaultDatabase,
            p.default_language_name AS DefaultLanguage,
            CAST(LOGINPROPERTY(p.name, 'PasswordLastSetTime') AS DATETIME) AS PasswordLastSet,
            CAST(LOGINPROPERTY(p.name, 'IsExpired') AS INT) AS IsExpired,
            CAST(LOGINPROPERTY(p.name, 'IsLocked') AS INT) AS IsLocked,
            CAST(LOGINPROPERTY(p.name, 'IsMustChange') AS INT) AS MustChangePassword,
            CAST(LOGINPROPERTY(p.name, 'BadPasswordCount') AS INT) AS BadPasswordCount,
            CASE WHEN p.name = 'sa' THEN 1 ELSE 0 END AS IsSA,
            sl.is_policy_checked AS PasswordPolicyEnforced,
            sl.is_expiration_checked AS PasswordExpirationEnabled
        FROM sys.server_principals p
        LEFT JOIN sys.sql_logins sl ON p.principal_id = sl.principal_id
        WHERE p.type IN ('S', 'U', 'G', 'C', 'K')  -- SQL, Windows User, Group, Cert, Asym Key
        ORDER BY p.name
        """
    
    def get_server_role_members(self) -> str:
        return """
        SELECT 
            r.name AS RoleName,
            m.name AS MemberName,
            m.type_desc AS MemberType,
            m.is_disabled AS MemberDisabled
        FROM sys.server_role_members rm
        JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
        JOIN sys.server_principals m ON rm.member_principal_id = m.principal_id
        ORDER BY r.name, m.name
        """
    
    def get_login_permissions(self) -> str:
        return """
        SELECT 
            p.name AS LoginName,
            perm.permission_name AS Permission,
            perm.state_desc AS PermissionState,
            perm.class_desc AS PermissionClass
        FROM sys.server_permissions perm
        JOIN sys.server_principals p ON perm.grantee_principal_id = p.principal_id
        WHERE perm.state IN ('G', 'W')  -- Grant, Grant with Grant
        ORDER BY p.name, perm.permission_name
        """
    
    def get_databases(self) -> str:
        return """
        SELECT 
            d.database_id AS DatabaseId,
            d.name AS DatabaseName,
            d.create_date AS CreateDate,
            d.collation_name AS Collation,
            d.user_access_desc AS UserAccess,
            d.state_desc AS State,
            d.recovery_model_desc AS RecoveryModel,
            d.is_auto_close_on AS AutoClose,
            d.is_auto_shrink_on AS AutoShrink,
            d.is_read_only AS IsReadOnly,
            d.is_trustworthy_on AS IsTrustworthy,
            d.is_db_chaining_on AS DbChaining,
            d.is_broker_enabled AS BrokerEnabled,
            SUSER_SNAME(d.owner_sid) AS Owner,
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id) AS SizeMB
        FROM sys.databases d
        ORDER BY d.name
        """
    
    def get_database_users(self, database: str) -> str:
        # Note: Caller must USE database first or use dynamic SQL
        return f"""
        SELECT 
            dp.name AS UserName,
            dp.principal_id AS PrincipalId,
            dp.type_desc AS UserType,
            dp.default_schema_name AS DefaultSchema,
            dp.create_date AS CreateDate,
            dp.modify_date AS ModifyDate,
            sp.name AS MappedLogin,
            CASE WHEN sp.name IS NULL AND dp.type != 'R' AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys') 
                 THEN 1 ELSE 0 END AS IsOrphaned
        FROM [{database}].sys.database_principals dp
        LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
        WHERE dp.type IN ('S', 'U', 'G', 'C', 'K')
        ORDER BY dp.name
        """
    
    def get_database_role_members(self, database: str) -> str:
        return f"""
        SELECT 
            r.name AS RoleName,
            m.name AS MemberName,
            m.type_desc AS MemberType
        FROM [{database}].sys.database_role_members rm
        JOIN [{database}].sys.database_principals r ON rm.role_principal_id = r.principal_id
        JOIN [{database}].sys.database_principals m ON rm.member_principal_id = m.principal_id
        ORDER BY r.name, m.name
        """
    
    def get_orphaned_users(self, database: str) -> str:
        return f"""
        SELECT 
            dp.name AS UserName,
            dp.type_desc AS UserType,
            dp.create_date AS CreateDate
        FROM [{database}].sys.database_principals dp
        LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
        WHERE dp.type IN ('S', 'U', 'G')
          AND sp.name IS NULL
          AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')
        """
    
    def get_linked_servers(self) -> str:
        return """
        SELECT 
            s.server_id AS ServerId,
            s.name AS LinkedServerName,
            s.product AS Product,
            s.provider AS Provider,
            s.data_source AS DataSource,
            s.catalog AS Catalog,
            s.is_linked AS IsLinked,
            s.is_remote_login_enabled AS RemoteLoginEnabled,
            s.is_rpc_out_enabled AS RpcOutEnabled,
            s.is_data_access_enabled AS DataAccessEnabled,
            s.modify_date AS ModifyDate
        FROM sys.servers s
        WHERE s.is_linked = 1
        ORDER BY s.name
        """
    
    def get_linked_server_logins(self) -> str:
        return """
        SELECT 
            s.name AS LinkedServerName,
            COALESCE(p.name, '** All Logins **') AS LocalLogin,
            ll.remote_name AS RemoteLogin,
            ll.uses_self_credential AS UsesSelf,
            ll.modify_date AS ModifyDate
        FROM sys.linked_logins ll
        JOIN sys.servers s ON ll.server_id = s.server_id
        LEFT JOIN sys.server_principals p ON ll.local_principal_id = p.principal_id
        WHERE s.is_linked = 1
        ORDER BY s.name, p.name
        """
    
    def get_server_triggers(self) -> str:
        return """
        SELECT 
            t.name AS TriggerName,
            t.parent_class_desc AS TriggerLevel,
            te.type_desc AS EventType,
            t.create_date AS CreateDate,
            t.modify_date AS ModifyDate,
            t.is_disabled AS IsDisabled,
            t.is_ms_shipped AS IsMsShipped
        FROM sys.server_triggers t
        LEFT JOIN sys.server_trigger_events te ON t.object_id = te.object_id
        ORDER BY t.name
        """
    
    def get_database_triggers(self, database: str) -> str:
        return f"""
        SELECT 
            t.name AS TriggerName,
            OBJECT_NAME(t.parent_id, DB_ID('{database}')) AS ParentObject,
            t.type_desc AS TriggerType,
            t.create_date AS CreateDate,
            t.modify_date AS ModifyDate,
            t.is_disabled AS IsDisabled,
            t.is_instead_of_trigger AS IsInsteadOf
        FROM [{database}].sys.triggers t
        WHERE t.parent_class = 0  -- Database triggers only
        ORDER BY t.name
        """
    
    def get_backup_history(self) -> str:
        return """
        SELECT 
            d.name AS DatabaseName,
            d.recovery_model_desc AS RecoveryModel,
            bs.backup_finish_date AS BackupDate,
            bs.type AS BackupType,
            CASE bs.type 
                WHEN 'D' THEN 'Full'
                WHEN 'I' THEN 'Differential'
                WHEN 'L' THEN 'Log'
                ELSE bs.type 
            END AS BackupTypeName,
            bs.backup_size / 1024 / 1024 AS BackupSizeMB,
            DATEDIFF(MINUTE, bs.backup_start_date, bs.backup_finish_date) AS DurationMinutes,
            bmf.physical_device_name AS BackupPath,
            bs.server_name AS BackupServer,
            bs.user_name AS BackupUser
        FROM sys.databases d
        LEFT JOIN msdb.dbo.backupset bs ON d.name = bs.database_name
        LEFT JOIN msdb.dbo.backupmediafamily bmf ON bs.media_set_id = bmf.media_set_id
        WHERE d.database_id > 4  -- Exclude system DBs
        ORDER BY d.name, bs.backup_finish_date DESC
        """
    
    def get_backup_jobs(self) -> str:
        return """
        SELECT 
            j.name AS JobName,
            j.enabled AS IsEnabled,
            j.date_created AS CreateDate,
            j.date_modified AS ModifyDate,
            CASE ja.run_status
                WHEN 0 THEN 'Failed'
                WHEN 1 THEN 'Succeeded'
                WHEN 2 THEN 'Retry'
                WHEN 3 THEN 'Canceled'
                WHEN 4 THEN 'In Progress'
                ELSE 'Unknown'
            END AS LastRunStatus,
            ja.run_date AS LastRunDate,
            ja.run_duration AS LastRunDuration,
            ja.message AS LastMessage
        FROM msdb.dbo.sysjobs j
        CROSS APPLY (
            SELECT TOP 1 h.run_status, h.run_date, h.run_duration, h.message
            FROM msdb.dbo.sysjobhistory h
            WHERE h.job_id = j.job_id AND h.step_id = 0
            ORDER BY h.run_date DESC, h.run_time DESC
        ) ja
        WHERE j.name LIKE '%backup%' OR j.name LIKE '%bak%'
        ORDER BY j.name
        """
    
    def get_audit_settings(self) -> str:
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'default trace enabled') AS DefaultTraceEnabled,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'c2 audit mode') AS C2AuditMode,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'common criteria compliance enabled') AS CommonCriteria
        """


class Sql2019PlusProvider(QueryProvider):
    """
    Query provider for SQL Server 2012 and later.
    
    Uses modern features where beneficial:
    - STRING_AGG (2017+, with fallback)
    - TRY_CAST where helpful
    - dm_os_host_info (2017+)
    - Better error handling
    """
    
    VERSION_NAME = "SQL Server 2012+"
    MIN_VERSION = 11
    MAX_VERSION = 99
    
    def get_server_info(self) -> str:
        # dm_os_host_info is 2017+, fall back gracefully
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            CAST(SERVERPROPERTY('MachineName') AS NVARCHAR(256)) AS MachineName,
            CAST(SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS NVARCHAR(256)) AS PhysicalName,
            (SELECT cpu_count FROM sys.dm_os_sys_info) AS CPU_Count,
            (SELECT physical_memory_kb/1024/1024 FROM sys.dm_os_sys_info) AS Memory_GB,
            (SELECT sqlserver_start_time FROM sys.dm_os_sys_info) AS SQL_Start_Time,
            CAST(SERVERPROPERTY('Collation') AS NVARCHAR(256)) AS Collation,
            CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS INT) AS WindowsAuthOnly,
            CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered,
            CAST(SERVERPROPERTY('IsHadrEnabled') AS INT) AS IsHadrEnabled,
            CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(512)) AS DefaultDataPath,
            CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS NVARCHAR(512)) AS DefaultLogPath,
            CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(512)) AS DefaultBackupPath
        """
    
    def get_instance_properties(self) -> str:
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(256)) AS InstanceName,
            CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS Version,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 4) AS INT) AS VersionMajor,
            CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256)) AS Edition,
            CAST(SERVERPROPERTY('ProductLevel') AS NVARCHAR(128)) AS ProductLevel,
            CAST(SERVERPROPERTY('ProductUpdateLevel') AS NVARCHAR(128)) AS UpdateLevel,
            CAST(SERVERPROPERTY('ProductUpdateReference') AS NVARCHAR(128)) AS UpdateReference,
            CAST(SERVERPROPERTY('EngineEdition') AS INT) AS EngineEdition,
            CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered,
            CAST(SERVERPROPERTY('IsFullTextInstalled') AS INT) AS IsFullTextInstalled,
            CAST(SERVERPROPERTY('IsPolyBaseInstalled') AS INT) AS IsPolyBaseInstalled,
            CAST(SERVERPROPERTY('IsXTPSupported') AS INT) AS IsInMemoryOLTPSupported,
            CAST(SERVERPROPERTY('LicenseType') AS NVARCHAR(128)) AS LicenseType
        """
    
    def get_sql_services(self) -> str:
        # Same limitation as 2008 - service info requires WMI/PowerShell
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            'SQL Server' AS ServiceType,
            @@SERVICENAME AS ServiceName,
            'Service details require WMI/PowerShell query' AS Note
        """
    
    def get_sp_configure(self) -> str:
        return """
        SELECT 
            name AS SettingName,
            CAST(value AS INT) AS ConfiguredValue,
            CAST(value_in_use AS INT) AS RunningValue,
            CAST(minimum AS INT) AS MinValue,
            CAST(maximum AS INT) AS MaxValue,
            CAST(is_dynamic AS INT) AS IsDynamic,
            CAST(is_advanced AS INT) AS IsAdvanced,
            description AS Description
        FROM sys.configurations
        ORDER BY name
        """
    
    def get_advanced_options(self) -> str:
        return """
        SELECT 
            name AS SettingName,
            CAST(value_in_use AS INT) AS CurrentValue,
            CASE 
                WHEN name IN ('xp_cmdshell', 'Ole Automation Procedures', 'Ad Hoc Distributed Queries', 
                             'remote access', 'Database Mail XPs') AND value_in_use = 1 
                THEN 'FAIL'
                WHEN name = 'clr enabled' AND value_in_use = 1 THEN 'WARN'
                ELSE 'OK'
            END AS Status
        FROM sys.configurations
        WHERE name IN (
            'xp_cmdshell',
            'Ole Automation Procedures', 
            'clr enabled',
            'cross db ownership chaining',
            'Ad Hoc Distributed Queries',
            'remote access',
            'Database Mail XPs',
            'scan for startup procs',
            'show advanced options',
            'remote admin connections',
            'allow updates',
            'backup compression default',
            'contained database authentication'
        )
        """
    
    def get_server_logins(self) -> str:
        return """
        SELECT 
            p.name AS LoginName,
            p.principal_id AS PrincipalId,
            p.sid AS SID,
            p.type_desc AS LoginType,
            p.is_disabled AS IsDisabled,
            p.create_date AS CreateDate,
            p.modify_date AS ModifyDate,
            p.default_database_name AS DefaultDatabase,
            p.default_language_name AS DefaultLanguage,
            CAST(LOGINPROPERTY(p.name, 'PasswordLastSetTime') AS DATETIME) AS PasswordLastSet,
            CAST(LOGINPROPERTY(p.name, 'IsExpired') AS INT) AS IsExpired,
            CAST(LOGINPROPERTY(p.name, 'IsLocked') AS INT) AS IsLocked,
            CAST(LOGINPROPERTY(p.name, 'IsMustChange') AS INT) AS MustChangePassword,
            CAST(LOGINPROPERTY(p.name, 'BadPasswordCount') AS INT) AS BadPasswordCount,
            CASE WHEN p.name = 'sa' OR p.sid = 0x01 THEN 1 ELSE 0 END AS IsSA,
            sl.is_policy_checked AS PasswordPolicyEnforced,
            sl.is_expiration_checked AS PasswordExpirationEnabled,
            CASE WHEN sl.password_hash IS NULL AND p.type = 'S' THEN 1 ELSE 0 END AS IsEmptyPassword
        FROM sys.server_principals p
        LEFT JOIN sys.sql_logins sl ON p.principal_id = sl.principal_id
        WHERE p.type IN ('S', 'U', 'G', 'C', 'K')
        ORDER BY p.name
        """
    
    def get_server_role_members(self) -> str:
        return """
        SELECT 
            r.name AS RoleName,
            r.principal_id AS RolePrincipalId,
            m.name AS MemberName,
            m.principal_id AS MemberPrincipalId,
            m.type_desc AS MemberType,
            m.is_disabled AS MemberDisabled,
            m.create_date AS MemberCreateDate
        FROM sys.server_role_members rm
        JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
        JOIN sys.server_principals m ON rm.member_principal_id = m.principal_id
        ORDER BY r.name, m.name
        """
    
    def get_login_permissions(self) -> str:
        return """
        SELECT 
            p.name AS LoginName,
            perm.permission_name AS Permission,
            perm.state_desc AS PermissionState,
            perm.class_desc AS PermissionClass,
            CASE WHEN perm.state = 'W' THEN 1 ELSE 0 END AS WithGrantOption
        FROM sys.server_permissions perm
        JOIN sys.server_principals p ON perm.grantee_principal_id = p.principal_id
        WHERE perm.state IN ('G', 'W')
        ORDER BY p.name, perm.permission_name
        """
    
    def get_databases(self) -> str:
        return """
        SELECT 
            d.database_id AS DatabaseId,
            d.name AS DatabaseName,
            d.create_date AS CreateDate,
            d.collation_name AS Collation,
            d.user_access_desc AS UserAccess,
            d.state_desc AS State,
            d.recovery_model_desc AS RecoveryModel,
            d.compatibility_level AS CompatibilityLevel,
            d.is_auto_close_on AS AutoClose,
            d.is_auto_shrink_on AS AutoShrink,
            d.is_read_only AS IsReadOnly,
            d.is_trustworthy_on AS IsTrustworthy,
            d.is_db_chaining_on AS DbChaining,
            d.is_broker_enabled AS BrokerEnabled,
            d.is_encrypted AS IsEncrypted,
            d.containment_desc AS Containment,
            SUSER_SNAME(d.owner_sid) AS Owner,
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id AND mf.type = 0) AS DataSizeMB,
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id AND mf.type = 1) AS LogSizeMB
        FROM sys.databases d
        ORDER BY d.name
        """
    
    def get_database_users(self, database: str) -> str:
        return f"""
        SELECT 
            dp.name AS UserName,
            dp.principal_id AS PrincipalId,
            dp.type_desc AS UserType,
            dp.default_schema_name AS DefaultSchema,
            dp.create_date AS CreateDate,
            dp.modify_date AS ModifyDate,
            dp.authentication_type_desc AS AuthenticationType,
            sp.name AS MappedLogin,
            CASE WHEN sp.name IS NULL AND dp.type IN ('S', 'U', 'G') 
                      AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')
                      AND dp.authentication_type != 2  -- Not contained user
                 THEN 1 ELSE 0 END AS IsOrphaned,
            CASE WHEN dp.name = 'guest' AND EXISTS (
                SELECT 1 FROM [{database}].sys.database_permissions p 
                WHERE p.grantee_principal_id = dp.principal_id 
                  AND p.permission_name = 'CONNECT'
                  AND p.state = 'G'
            ) THEN 1 ELSE 0 END AS GuestEnabled
        FROM [{database}].sys.database_principals dp
        LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
        WHERE dp.type IN ('S', 'U', 'G', 'C', 'K')
        ORDER BY dp.name
        """
    
    def get_database_role_members(self, database: str) -> str:
        return f"""
        SELECT 
            r.name AS RoleName,
            r.principal_id AS RolePrincipalId,
            m.name AS MemberName,
            m.principal_id AS MemberPrincipalId,
            m.type_desc AS MemberType
        FROM [{database}].sys.database_role_members rm
        JOIN [{database}].sys.database_principals r ON rm.role_principal_id = r.principal_id
        JOIN [{database}].sys.database_principals m ON rm.member_principal_id = m.principal_id
        ORDER BY r.name, m.name
        """
    
    def get_orphaned_users(self, database: str) -> str:
        return f"""
        SELECT 
            dp.name AS UserName,
            dp.type_desc AS UserType,
            dp.create_date AS CreateDate,
            dp.default_schema_name AS DefaultSchema
        FROM [{database}].sys.database_principals dp
        LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
        WHERE dp.type IN ('S', 'U', 'G')
          AND sp.name IS NULL
          AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')
          AND dp.authentication_type != 2  -- Not contained database user
        """
    
    def get_linked_servers(self) -> str:
        return """
        SELECT 
            s.server_id AS ServerId,
            s.name AS LinkedServerName,
            s.product AS Product,
            s.provider AS Provider,
            s.data_source AS DataSource,
            s.location AS Location,
            s.provider_string AS ProviderString,
            s.catalog AS Catalog,
            s.is_linked AS IsLinked,
            s.is_remote_login_enabled AS RemoteLoginEnabled,
            s.is_rpc_out_enabled AS RpcOutEnabled,
            s.is_data_access_enabled AS DataAccessEnabled,
            s.is_collation_compatible AS CollationCompatible,
            s.uses_remote_collation AS UsesRemoteCollation,
            s.collation_name AS CollationName,
            s.connect_timeout AS ConnectTimeout,
            s.query_timeout AS QueryTimeout,
            s.modify_date AS ModifyDate
        FROM sys.servers s
        WHERE s.is_linked = 1
        ORDER BY s.name
        """
    
    def get_linked_server_logins(self) -> str:
        return """
        SELECT 
            s.name AS LinkedServerName,
            COALESCE(p.name, '** All Logins **') AS LocalLogin,
            ll.remote_name AS RemoteLogin,
            ll.uses_self_credential AS UsesSelf,
            ll.modify_date AS ModifyDate,
            CASE 
                WHEN ll.remote_name = 'sa' OR ll.remote_name LIKE '%admin%' 
                THEN 'HIGH_PRIVILEGE' 
                ELSE 'NORMAL' 
            END AS RiskLevel
        FROM sys.linked_logins ll
        JOIN sys.servers s ON ll.server_id = s.server_id
        LEFT JOIN sys.server_principals p ON ll.local_principal_id = p.principal_id
        WHERE s.is_linked = 1
        ORDER BY s.name, p.name
        """
    
    def get_server_triggers(self) -> str:
        return """
        SELECT 
            t.name AS TriggerName,
            t.parent_class_desc AS TriggerLevel,
            te.type_desc AS EventType,
            t.create_date AS CreateDate,
            t.modify_date AS ModifyDate,
            t.is_disabled AS IsDisabled,
            t.is_ms_shipped AS IsMsShipped
        FROM sys.server_triggers t
        LEFT JOIN sys.server_trigger_events te ON t.object_id = te.object_id
        ORDER BY t.name
        """
    
    def get_database_triggers(self, database: str) -> str:
        return f"""
        SELECT 
            t.name AS TriggerName,
            OBJECT_SCHEMA_NAME(t.parent_id, DB_ID('{database}')) AS SchemaName,
            OBJECT_NAME(t.parent_id, DB_ID('{database}')) AS ParentObject,
            t.type_desc AS TriggerType,
            t.create_date AS CreateDate,
            t.modify_date AS ModifyDate,
            t.is_disabled AS IsDisabled,
            t.is_instead_of_trigger AS IsInsteadOf,
            t.is_not_for_replication AS NotForReplication,
            t.is_ms_shipped AS IsMsShipped
        FROM [{database}].sys.triggers t
        ORDER BY t.name
        """
    
    def get_backup_history(self) -> str:
        return """
        SELECT 
            d.name AS DatabaseName,
            d.recovery_model_desc AS RecoveryModel,
            d.state_desc AS DatabaseState,
            bs.backup_finish_date AS BackupDate,
            bs.type AS BackupType,
            CASE bs.type 
                WHEN 'D' THEN 'Full'
                WHEN 'I' THEN 'Differential'
                WHEN 'L' THEN 'Log'
                WHEN 'F' THEN 'Filegroup'
                ELSE bs.type 
            END AS BackupTypeName,
            bs.backup_size / 1024 / 1024 AS BackupSizeMB,
            bs.compressed_backup_size / 1024 / 1024 AS CompressedSizeMB,
            DATEDIFF(MINUTE, bs.backup_start_date, bs.backup_finish_date) AS DurationMinutes,
            bmf.physical_device_name AS BackupPath,
            bs.server_name AS BackupServer,
            bs.user_name AS BackupUser,
            bs.is_copy_only AS IsCopyOnly,
            DATEDIFF(DAY, bs.backup_finish_date, GETDATE()) AS DaysSinceBackup
        FROM sys.databases d
        OUTER APPLY (
            SELECT TOP 1 * FROM msdb.dbo.backupset b 
            WHERE b.database_name = d.name AND b.type = 'D'
            ORDER BY b.backup_finish_date DESC
        ) bs
        LEFT JOIN msdb.dbo.backupmediafamily bmf ON bs.media_set_id = bmf.media_set_id
        WHERE d.database_id > 4
        ORDER BY d.name
        """
    
    def get_backup_jobs(self) -> str:
        return """
        SELECT 
            j.job_id AS JobId,
            j.name AS JobName,
            j.enabled AS IsEnabled,
            j.date_created AS CreateDate,
            j.date_modified AS ModifyDate,
            c.name AS Category,
            SUSER_SNAME(j.owner_sid) AS Owner,
            CASE jh.run_status
                WHEN 0 THEN 'Failed'
                WHEN 1 THEN 'Succeeded'
                WHEN 2 THEN 'Retry'
                WHEN 3 THEN 'Canceled'
                WHEN 4 THEN 'In Progress'
                ELSE 'Unknown'
            END AS LastRunStatus,
            msdb.dbo.agent_datetime(jh.run_date, jh.run_time) AS LastRunDateTime,
            jh.run_duration AS LastRunDuration,
            jh.message AS LastMessage
        FROM msdb.dbo.sysjobs j
        LEFT JOIN msdb.dbo.syscategories c ON j.category_id = c.category_id
        OUTER APPLY (
            SELECT TOP 1 h.run_status, h.run_date, h.run_time, h.run_duration, h.message
            FROM msdb.dbo.sysjobhistory h
            WHERE h.job_id = j.job_id AND h.step_id = 0
            ORDER BY h.run_date DESC, h.run_time DESC
        ) jh
        WHERE j.name LIKE '%backup%' 
           OR j.name LIKE '%bak%'
           OR c.name = 'Database Maintenance'
        ORDER BY j.name
        """
    
    def get_audit_settings(self) -> str:
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'default trace enabled') AS DefaultTraceEnabled,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'c2 audit mode') AS C2AuditMode,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'common criteria compliance enabled') AS CommonCriteria,
            (SELECT CAST(value_in_use AS INT) FROM sys.configurations WHERE name = 'contained database authentication') AS ContainedDbAuth
        """


def get_query_provider(version_major: int) -> QueryProvider:
    """
    Factory function to get the appropriate query provider for a SQL Server version.
    
    Args:
        version_major: Major version number (10=2008, 11=2012, ..., 16=2022)
        
    Returns:
        QueryProvider instance appropriate for the version
    """
    if version_major <= 10:
        return Sql2008Provider()
    return Sql2019PlusProvider()
