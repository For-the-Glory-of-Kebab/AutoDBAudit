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
    """
    SQL Server major version identifiers.
    
    Version mapping:
        10 = 2008/2008R2
        11 = 2012
        12 = 2014
        13 = 2016
        14 = 2017
        15 = 2019
        16 = 2022
        17 = 2025
        18+ = Future versions (use Sql2019PlusProvider)
    """
    SQL_2008 = 10
    SQL_2012 = 11
    SQL_2014 = 12
    SQL_2016 = 13
    SQL_2017 = 14
    SQL_2019 = 15
    SQL_2022 = 16
    SQL_2025 = 17


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
    
    # ========================================================================
    # Encryption
    # ========================================================================
    
    @abstractmethod
    def get_service_master_key(self) -> str:
        """Get Service Master Key status (instance-level)."""
    
    @abstractmethod
    def get_database_master_keys(self) -> str:
        """Get Database Master Keys across all databases."""
    
    @abstractmethod
    def get_tde_status(self) -> str:
        """Get Transparent Data Encryption status."""
    
    @abstractmethod
    def get_encryption_certificates(self) -> str:
        """Get certificates used for encryption."""


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
        # SQL 2008 doesn't have dm_os_host_info, use sys.dm_os_sys_info
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(256)) AS InstanceName,
            CAST(SERVERPROPERTY('MachineName') AS NVARCHAR(256)) AS MachineName,
            CAST(SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS NVARCHAR(256)) AS PhysicalMachine,
            CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS Version,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 4) AS INT) AS VersionMajor,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 3) AS INT) AS VersionMinor,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 2) AS INT) AS BuildNumber,
            CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256)) AS Edition,
            CAST(SERVERPROPERTY('ProductLevel') AS NVARCHAR(128)) AS ProductLevel,
            NULL AS CULevel,
            NULL AS KBArticle,
            CAST(SERVERPROPERTY('EngineEdition') AS INT) AS EngineEdition,
            CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered,
            CAST(SERVERPROPERTY('IsHadrEnabled') AS INT) AS IsHadrEnabled,
            CAST(SERVERPROPERTY('IsFullTextInstalled') AS INT) AS IsFullTextInstalled,
            CAST(SERVERPROPERTY('LicenseType') AS NVARCHAR(128)) AS LicenseType,
            'Windows' AS OSPlatform,
            NULL AS OSDistribution,
            @@VERSION AS FullVersionString,
            (SELECT cpu_count FROM sys.dm_os_sys_info) AS CPUCount,
            (SELECT physical_memory_in_bytes/1024/1024/1024 FROM sys.dm_os_sys_info) AS MemoryGB,
            (SELECT sqlserver_start_time FROM sys.dm_os_sys_info) AS SQLStartTime,
            -- Get IP from current connection
            (SELECT TOP 1 local_net_address 
             FROM sys.dm_exec_connections 
             WHERE local_net_address IS NOT NULL 
               AND local_net_address NOT LIKE '127.%'
               AND local_net_address NOT LIKE '169.254.%'
             ORDER BY connect_time DESC) AS IPAddress,
            (SELECT TOP 1 local_tcp_port 
             FROM sys.dm_exec_connections 
             WHERE local_tcp_port IS NOT NULL) AS TCPPort
        """
    
    def get_sql_services(self) -> str:
        # SQL 2008 doesn't have sys.dm_server_services
        # Use xp_cmdshell with wmic for cleaner output format
        return """
        SET NOCOUNT ON;
        
        DECLARE @xp_was_on BIT = 0;
        DECLARE @adv_was_on BIT = 0;
        
        SELECT @adv_was_on = CAST(value_in_use AS BIT)
        FROM sys.configurations WHERE name = 'show advanced options';
        
        SELECT @xp_was_on = CAST(value_in_use AS BIT)
        FROM sys.configurations WHERE name = 'xp_cmdshell';
        
        IF @adv_was_on = 0
            EXEC sp_configure 'show advanced options', 1;
        IF @xp_was_on = 0 OR @adv_was_on = 0
            RECONFIGURE WITH OVERRIDE;
        IF @xp_was_on = 0
            EXEC sp_configure 'xp_cmdshell', 1;
        IF @xp_was_on = 0
            RECONFIGURE WITH OVERRIDE;
        
        -- Use wmic list format for easier parsing
        CREATE TABLE #wmic (line NVARCHAR(2000));
        INSERT INTO #wmic
        EXEC xp_cmdshell 'wmic service where "name like ''%SQL%'' or name like ''MSSQL%'' or name like ''Report%''" get name,displayname,state,startmode,startname /format:list';
        
        -- Parse wmic output (format: Name=value on separate lines, blank between services)
        CREATE TABLE #parsed (
            ServiceName NVARCHAR(200),
            DisplayName NVARCHAR(300),
            Status NVARCHAR(50),
            StartupType NVARCHAR(50),
            ServiceAccount NVARCHAR(200)
        );
        
        -- Build result by parsing lines
        DECLARE @name NVARCHAR(200), @display NVARCHAR(300), @state NVARCHAR(50), @start NVARCHAR(50), @acct NVARCHAR(200);
        DECLARE @line NVARCHAR(2000);
        
        DECLARE line_cursor CURSOR FOR SELECT line FROM #wmic WHERE line IS NOT NULL AND LEN(LTRIM(RTRIM(line))) > 0;
        OPEN line_cursor;
        FETCH NEXT FROM line_cursor INTO @line;
        
        SET @name = NULL; SET @display = NULL; SET @state = NULL; SET @start = NULL; SET @acct = NULL;
        
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @line = LTRIM(RTRIM(@line));
            
            IF @line LIKE 'DisplayName=%' SET @display = SUBSTRING(@line, 13, LEN(@line));
            IF @line LIKE 'Name=%' SET @name = SUBSTRING(@line, 6, LEN(@line));
            IF @line LIKE 'StartMode=%' SET @start = SUBSTRING(@line, 11, LEN(@line));
            IF @line LIKE 'StartName=%' SET @acct = SUBSTRING(@line, 11, LEN(@line));
            IF @line LIKE 'State=%' SET @state = SUBSTRING(@line, 7, LEN(@line));
            
            -- When we have name and state, we have a complete record
            IF @name IS NOT NULL AND @state IS NOT NULL
            BEGIN
                INSERT INTO #parsed VALUES (@name, @display, @state, @start, @acct);
                SET @name = NULL; SET @display = NULL; SET @state = NULL; SET @start = NULL; SET @acct = NULL;
            END
            
            FETCH NEXT FROM line_cursor INTO @line;
        END
        CLOSE line_cursor;
        DEALLOCATE line_cursor;
        
        -- Return formatted results with instance extraction
        SELECT 
            ServiceName,
            CASE 
                WHEN ServiceName LIKE 'MSSQL$%' OR ServiceName = 'MSSQLSERVER' THEN 'Database Engine'
                WHEN ServiceName LIKE 'SQLAgent$%' OR ServiceName = 'SQLSERVERAGENT' THEN 'SQL Agent'
                WHEN ServiceName LIKE 'SQLBrowser%' THEN 'SQL Browser'
                WHEN ServiceName LIKE '%FullText%' OR ServiceName LIKE '%FDLauncher%' THEN 'Full-Text Search'
                WHEN ServiceName LIKE 'MSSQLServerOLAP%' THEN 'Analysis Services'
                WHEN ServiceName LIKE 'ReportServer%' THEN 'Reporting Services'
                WHEN ServiceName LIKE 'MsDtsServer%' THEN 'Integration Services'
                WHEN ServiceName LIKE '%Launchpad%' THEN 'Launchpad (ML)'
                WHEN ServiceName LIKE 'SQLWriter%' OR ServiceName LIKE '%VSS%' THEN 'VSS Writer'
                WHEN ServiceName LIKE '%CEIP%' OR ServiceName LIKE 'SQLTELEMETRY%' THEN 'CEIP Telemetry'
                ELSE 'Other SQL Service'
            END AS ServiceType,
            -- Extract instance name from service name (e.g., MSSQL$INTHEEND -> INTHEEND)
            CASE 
                WHEN ServiceName LIKE '%$%' THEN SUBSTRING(ServiceName, CHARINDEX('$', ServiceName) + 1, LEN(ServiceName))
                WHEN ServiceName IN ('MSSQLSERVER', 'SQLSERVERAGENT', 'SQLBrowser', 'SQLWriter') THEN '(Default)'
                ELSE NULL
            END AS InstanceName,
            Status,
            StartupType,
            ServiceAccount,
            DisplayName,
            CAST(NULL AS INT) AS ProcessId,
            CAST(NULL AS NVARCHAR(50)) AS LastStartup,
            CAST(0 AS INT) AS IsClustered,
            CAST(NULL AS NVARCHAR(100)) AS ClusterNode,
            CAST(NULL AS NVARCHAR(10)) AS FileInitEnabled
        FROM #parsed
        WHERE ServiceName IS NOT NULL
        ORDER BY 
            CASE 
                WHEN ServiceName LIKE 'MSSQL$%' OR ServiceName = 'MSSQLSERVER' THEN 1
                WHEN ServiceName LIKE 'SQLAgent$%' OR ServiceName = 'SQLSERVERAGENT' THEN 2
                ELSE 99
            END,
            ServiceName;
        
        DROP TABLE #parsed;
        DROP TABLE #wmic;
        
        IF @xp_was_on = 0
            EXEC sp_configure 'xp_cmdshell', 0;
        IF @xp_was_on = 0 OR @adv_was_on = 0
            RECONFIGURE WITH OVERRIDE;
        IF @adv_was_on = 0
            EXEC sp_configure 'show advanced options', 0;
        IF @adv_was_on = 0
            RECONFIGURE WITH OVERRIDE;
        
        SET NOCOUNT OFF;
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
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id) AS SizeMB,
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id AND mf.type = 0) AS DataSizeMB,
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id AND mf.type = 1) AS LogSizeMB
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
            COALESCE(NULLIF(s.product, ''), s.provider) AS Product,
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
            CASE 
                WHEN p.name IS NULL THEN '(All Logins)'
                ELSE p.name 
            END AS LocalLogin,
            CASE 
                WHEN ll.uses_self_credential = 1 THEN '(Impersonate)'
                WHEN ll.remote_name IS NOT NULL THEN ll.remote_name
                ELSE '(No Mapping)'
            END AS RemoteLogin,
            ll.uses_self_credential AS Impersonate,
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
            d.state_desc AS DatabaseState,
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
            bs.user_name AS BackupUser,
            DATEDIFF(DAY, bs.backup_finish_date, GETDATE()) AS DaysSinceBackup
        FROM sys.databases d
        LEFT JOIN (
            SELECT database_name, MAX(backup_set_id) AS max_id
            FROM msdb.dbo.backupset WHERE type = 'D' GROUP BY database_name
        ) latest ON d.name = latest.database_name
        LEFT JOIN msdb.dbo.backupset bs ON latest.max_id = bs.backup_set_id
        LEFT JOIN msdb.dbo.backupmediafamily bmf ON bs.media_set_id = bmf.media_set_id
        WHERE d.database_id > 4  -- Exclude system DBs
          AND d.state_desc = 'ONLINE'  -- Only online databases
        ORDER BY d.name
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
    
    def get_service_master_key(self) -> str:
        return """
        SELECT 
            'SMK' AS KeyType,
            name AS KeyName,
            algorithm_desc AS Algorithm,
            create_date AS CreatedDate,
            modify_date AS ModifyDate,
            key_length AS KeyLength
        FROM master.sys.symmetric_keys 
        WHERE name = '##MS_ServiceMasterKey##'
        """
    
    def get_database_master_keys(self) -> str:
        # SQL 2008: Need to iterate databases, return consolidated view
        return """
        SET NOCOUNT ON;
        
        CREATE TABLE #dmk_results (
            DatabaseName NVARCHAR(256),
            KeyName NVARCHAR(256),
            Algorithm NVARCHAR(128),
            CreatedDate DATETIME,
            ModifyDate DATETIME,
            KeyLength INT
        );
        
        DECLARE @sql NVARCHAR(MAX);
        DECLARE @db NVARCHAR(256);
        
        DECLARE db_cursor CURSOR FOR 
        SELECT name FROM sys.databases 
        WHERE state_desc = 'ONLINE' AND database_id > 4;
        
        OPEN db_cursor;
        FETCH NEXT FROM db_cursor INTO @db;
        
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @sql = 'INSERT INTO #dmk_results 
                SELECT ''' + @db + ''' AS DatabaseName,
                    name, algorithm_desc, create_date, modify_date, key_length
                FROM [' + @db + '].sys.symmetric_keys 
                WHERE name = ''##MS_DatabaseMasterKey##''';
            BEGIN TRY
                EXEC sp_executesql @sql;
            END TRY
            BEGIN CATCH
                -- Skip inaccessible databases
            END CATCH
            FETCH NEXT FROM db_cursor INTO @db;
        END
        
        CLOSE db_cursor;
        DEALLOCATE db_cursor;
        
        SELECT * FROM #dmk_results;
        DROP TABLE #dmk_results;
        
        SET NOCOUNT OFF;
        """
    
    def get_tde_status(self) -> str:
        # SQL 2008 R2 has sys.dm_database_encryption_keys
        return """
        SELECT 
            d.name AS DatabaseName,
            dek.encryption_state AS EncryptionState,
            CASE dek.encryption_state
                WHEN 0 THEN 'No encryption key'
                WHEN 1 THEN 'Unencrypted'
                WHEN 2 THEN 'Encryption in progress'
                WHEN 3 THEN 'Encrypted'
                WHEN 4 THEN 'Key change in progress'
                WHEN 5 THEN 'Decryption in progress'
                WHEN 6 THEN 'Protection change in progress'
                ELSE 'Unknown'
            END AS EncryptionStateDesc,
            dek.key_algorithm AS Algorithm,
            dek.key_length AS KeyLength,
            dek.encryptor_type AS EncryptorType,
            c.name AS CertificateName,
            dek.create_date AS CreatedDate,
            dek.set_date AS ModifyDate,
            dek.percent_complete AS PercentComplete
        FROM sys.databases d
        LEFT JOIN sys.dm_database_encryption_keys dek ON d.database_id = dek.database_id
        LEFT JOIN master.sys.certificates c ON dek.encryptor_thumbprint = c.thumbprint
        WHERE d.database_id > 4
        ORDER BY d.name
        """
    
    def get_encryption_certificates(self) -> str:
        return """
        SELECT 
            name AS CertificateName,
            certificate_id AS CertificateId,
            subject AS Subject,
            start_date AS StartDate,
            expiry_date AS ExpiryDate,
            pvt_key_encryption_type_desc AS PrivateKeyEncryption,
            is_active_for_begin_dialog AS IsActiveForDialog,
            DATEDIFF(DAY, GETDATE(), expiry_date) AS DaysUntilExpiry
        FROM master.sys.certificates
        WHERE name NOT LIKE '##MS_%'
        ORDER BY name
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
        # 2017+ has dm_os_host_info for OS version
        return """
        SELECT 
            CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(256)) AS ServerName,
            CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(256)) AS InstanceName,
            CAST(SERVERPROPERTY('MachineName') AS NVARCHAR(256)) AS MachineName,
            CAST(SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS NVARCHAR(256)) AS PhysicalMachine,
            CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS Version,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 4) AS INT) AS VersionMajor,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 3) AS INT) AS VersionMinor,
            CAST(PARSENAME(CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), 2) AS INT) AS BuildNumber,
            CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256)) AS Edition,
            CAST(SERVERPROPERTY('ProductLevel') AS NVARCHAR(128)) AS ProductLevel,
            CAST(SERVERPROPERTY('ProductUpdateLevel') AS NVARCHAR(128)) AS CULevel,
            CAST(SERVERPROPERTY('ProductUpdateReference') AS NVARCHAR(128)) AS KBArticle,
            CAST(SERVERPROPERTY('EngineEdition') AS INT) AS EngineEdition,
            CAST(SERVERPROPERTY('IsClustered') AS INT) AS IsClustered,
            CAST(SERVERPROPERTY('IsHadrEnabled') AS INT) AS IsHadrEnabled,
            CAST(SERVERPROPERTY('IsFullTextInstalled') AS INT) AS IsFullTextInstalled,
            CAST(SERVERPROPERTY('LicenseType') AS NVARCHAR(128)) AS LicenseType,
            (SELECT host_platform FROM sys.dm_os_host_info) AS OSPlatform,
            (SELECT host_distribution FROM sys.dm_os_host_info) AS OSDistribution,
            (SELECT host_release FROM sys.dm_os_host_info) AS OSRelease,
            (SELECT cpu_count FROM sys.dm_os_sys_info) AS CPUCount,
            (SELECT physical_memory_kb/1024/1024 FROM sys.dm_os_sys_info) AS MemoryGB,
            (SELECT sqlserver_start_time FROM sys.dm_os_sys_info) AS SQLStartTime,
            -- Get IP address from current connection (most reliable non-loopback IP)
            (SELECT TOP 1 local_net_address 
             FROM sys.dm_exec_connections 
             WHERE local_net_address IS NOT NULL 
               AND local_net_address NOT LIKE '127.%'
               AND local_net_address NOT LIKE '169.254.%'
               AND local_net_address != '::1'
             ORDER BY connect_time DESC) AS IPAddress,
            -- Get TCP port
            (SELECT TOP 1 local_tcp_port 
             FROM sys.dm_exec_connections 
             WHERE local_tcp_port IS NOT NULL) AS TCPPort
        """
    
    def get_sql_services(self) -> str:
        # sys.dm_server_services gives all SQL-related services
        return """
        SELECT 
            servicename AS ServiceName,
            CASE 
                WHEN servicename LIKE '%SQL Server (%' THEN 'Database Engine'
                WHEN servicename LIKE '%Agent%' THEN 'SQL Agent'
                WHEN servicename LIKE '%Browser%' THEN 'SQL Browser'
                WHEN servicename LIKE '%Full-text%' OR servicename LIKE '%Fulltext%' THEN 'Full-Text Search'
                WHEN servicename LIKE '%Analysis%' OR servicename LIKE '%SSAS%' THEN 'Analysis Services'
                WHEN servicename LIKE '%Reporting%' OR servicename LIKE '%SSRS%' THEN 'Reporting Services'
                WHEN servicename LIKE '%Integration%' OR servicename LIKE '%SSIS%' THEN 'Integration Services'
                WHEN servicename LIKE '%Launchpad%' THEN 'Launchpad (ML)'
                WHEN servicename LIKE '%VSS%' OR servicename LIKE '%Writer%' THEN 'VSS Writer'
                WHEN servicename LIKE '%CEIP%' OR servicename LIKE '%Telemetry%' THEN 'CEIP Telemetry'
                WHEN servicename LIKE '%PolyBase%' THEN 'PolyBase'
                ELSE 'Other'
            END AS ServiceType,
            -- Extract instance name from service display name
            CASE 
                WHEN servicename LIKE '%(%)%' THEN 
                    SUBSTRING(servicename, CHARINDEX('(', servicename) + 1, 
                              CHARINDEX(')', servicename) - CHARINDEX('(', servicename) - 1)
                ELSE NULL
            END AS InstanceName,
            startup_type_desc AS StartupType,
            status_desc AS Status,
            service_account AS ServiceAccount,
            servicename AS DisplayName,
            process_id AS ProcessId,
            last_startup_time AS LastStartup,
            is_clustered AS IsClustered,
            cluster_nodename AS ClusterNode,
            instant_file_initialization_enabled AS FileInitEnabled
        FROM sys.dm_server_services
        ORDER BY 
            CASE 
                WHEN servicename LIKE '%SQL Server (%' THEN 1
                WHEN servicename LIKE '%Agent%' THEN 2
                ELSE 99
            END,
            servicename
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
            (SELECT SUM(size * 8.0 / 1024) FROM sys.master_files mf WHERE mf.database_id = d.database_id) AS SizeMB,
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
            COALESCE(NULLIF(s.product, ''), s.provider) AS Product,
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
            CASE 
                WHEN p.name IS NULL THEN '(All Logins)'
                ELSE p.name 
            END AS LocalLogin,
            CASE 
                WHEN ll.uses_self_credential = 1 THEN '(Impersonate)'
                WHEN ll.remote_name IS NOT NULL THEN ll.remote_name
                ELSE '(No Mapping)'
            END AS RemoteLogin,
            ll.uses_self_credential AS Impersonate,
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
    
    def get_service_master_key(self) -> str:
        return """
        SELECT 
            'SMK' AS KeyType,
            name AS KeyName,
            algorithm_desc AS Algorithm,
            create_date AS CreatedDate,
            modify_date AS ModifyDate,
            key_length AS KeyLength
        FROM master.sys.symmetric_keys 
        WHERE name = '##MS_ServiceMasterKey##'
        """
    
    def get_database_master_keys(self) -> str:
        # 2012+: Use sp_MSforeachdb for convenience
        return """
        SET NOCOUNT ON;
        
        CREATE TABLE #dmk_results (
            DatabaseName NVARCHAR(256),
            KeyName NVARCHAR(256),
            Algorithm NVARCHAR(128),
            CreatedDate DATETIME,
            ModifyDate DATETIME,
            KeyLength INT
        );
        
        DECLARE @sql NVARCHAR(MAX);
        DECLARE @db NVARCHAR(256);
        
        DECLARE db_cursor CURSOR FOR 
        SELECT name FROM sys.databases 
        WHERE state_desc = 'ONLINE' AND database_id > 4;
        
        OPEN db_cursor;
        FETCH NEXT FROM db_cursor INTO @db;
        
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @sql = N'INSERT INTO #dmk_results 
                SELECT ''' + @db + N''' AS DatabaseName,
                    name, algorithm_desc, create_date, modify_date, key_length
                FROM [' + @db + N'].sys.symmetric_keys 
                WHERE name = ''##MS_DatabaseMasterKey##''';
            BEGIN TRY
                EXEC sp_executesql @sql;
            END TRY
            BEGIN CATCH
                -- Skip inaccessible databases
            END CATCH
            FETCH NEXT FROM db_cursor INTO @db;
        END
        
        CLOSE db_cursor;
        DEALLOCATE db_cursor;
        
        SELECT * FROM #dmk_results;
        DROP TABLE #dmk_results;
        
        SET NOCOUNT OFF;
        """
    
    def get_tde_status(self) -> str:
        return """
        SELECT 
            d.name AS DatabaseName,
            d.is_encrypted AS IsEncrypted,
            dek.encryption_state AS EncryptionState,
            CASE dek.encryption_state
                WHEN 0 THEN 'No encryption key'
                WHEN 1 THEN 'Unencrypted'
                WHEN 2 THEN 'Encryption in progress'
                WHEN 3 THEN 'Encrypted'
                WHEN 4 THEN 'Key change in progress'
                WHEN 5 THEN 'Decryption in progress'
                WHEN 6 THEN 'Protection change in progress'
                ELSE 'Unknown'
            END AS EncryptionStateDesc,
            dek.key_algorithm AS Algorithm,
            dek.key_length AS KeyLength,
            dek.encryptor_type AS EncryptorType,
            c.name AS CertificateName,
            c.expiry_date AS CertExpiryDate,
            dek.create_date AS CreatedDate,
            dek.set_date AS ModifyDate,
            dek.percent_complete AS PercentComplete
        FROM sys.databases d
        LEFT JOIN sys.dm_database_encryption_keys dek ON d.database_id = dek.database_id
        LEFT JOIN master.sys.certificates c ON dek.encryptor_thumbprint = c.thumbprint
        WHERE d.database_id > 4
        ORDER BY d.name
        """
    
    def get_encryption_certificates(self) -> str:
        return """
        SELECT 
            name AS CertificateName,
            certificate_id AS CertificateId,
            subject AS Subject,
            issuer_name AS Issuer,
            start_date AS StartDate,
            expiry_date AS ExpiryDate,
            pvt_key_encryption_type_desc AS PrivateKeyEncryption,
            pvt_key_last_backup_date AS PrivateKeyLastBackup,
            is_active_for_begin_dialog AS IsActiveForDialog,
            DATEDIFF(DAY, GETDATE(), expiry_date) AS DaysUntilExpiry,
            CASE WHEN pvt_key_last_backup_date IS NULL THEN 0 ELSE 1 END AS IsBackedUp
        FROM master.sys.certificates
        WHERE name NOT LIKE '##MS_%'
        ORDER BY name
        """


def get_query_provider(version_major: int) -> QueryProvider:
    """
    Factory function to get the appropriate query provider for a SQL Server version.
    
    This function is future-proof: any version >= 11 (SQL 2012) uses 
    Sql2019PlusProvider, which works for 2012, 2014, 2016, 2017, 2019, 
    2022, 2025, and future versions since T-SQL syntax is stable.
    
    Args:
        version_major: Major version number
            - 10 = SQL Server 2008/2008R2
            - 11 = SQL Server 2012
            - 12 = SQL Server 2014
            - 13 = SQL Server 2016
            - 14 = SQL Server 2017
            - 15 = SQL Server 2019
            - 16 = SQL Server 2022
            - 17 = SQL Server 2025
            - 18+ = Future versions (uses Sql2019PlusProvider)
        
    Returns:
        QueryProvider instance appropriate for the version
    """
    if version_major <= 10:
        return Sql2008Provider()
    # All versions 2012+ use the same provider (T-SQL is stable)
    return Sql2019PlusProvider()
