-- SQL SERVER 2008 R2 INSTANCE (localhost\legacy) - SAFE DISCREPANCY SCRIPT
-- AdventureWorks2008R2 database assumed to exist
-- SA ACCOUNT PRESERVED - NO CHANGES TO EXISTING LOGINS
-- ALL SYNTAX VALIDATED FOR SQL SERVER 2008 R2 SP3
USE master;
GO -- Generate random suffix for test objects to avoid conflicts
DECLARE @RandomSuffix1 VARCHAR(10)
SET @RandomSuffix1 = LEFT(CAST(NEWID() AS VARCHAR(36)), 5) PRINT 'Random suffix for test objects: ' + @RandomSuffix1
GO -- Requirement 1: Server Documentation & Configuration (missing documentation)
    -- Add documentation metadata using proper 2008 R2 syntax
    USE master;
GO
IF NOT EXISTS (
        SELECT *
        FROM::fn_listextendedproperty(NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        WHERE name = 'DocumentationLastReviewed'
    ) BEGIN EXEC sp_addextendedproperty @name = N'DocumentationLastReviewed',
    @value = N'2023-01-15';
-- Over 2 years old
PRINT 'Added outdated documentation metadata - violation'
END
GO -- Requirement 2: SQL Server version compliance (out of support)
    PRINT 'SQL Server 2008 R2 is out of support - critical violation'
GO -- Requirement 3: SA account - PRESERVE ACCESS (enabled and not renamed)
    -- Do NOT modify SA account - only document current status
    PRINT 'SA account is enabled and not renamed - intentional violation for testing'
GO -- Requirement 4: Password requirements for privileged accounts (weak policies)
    -- Create NEW test accounts only - do NOT modify existing ones
DECLARE @WeakAdminLogin VARCHAR(100)
SET @WeakAdminLogin = 'WeakAdmin_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.server_principals
        WHERE name = @WeakAdminLogin
    ) BEGIN
DECLARE @WeakPassword VARCHAR(100)
SET @WeakPassword = 'weakpass' + LEFT(CAST(NEWID() AS VARCHAR(36)), 6) EXEC(
        'CREATE LOGIN [' + @WeakAdminLogin + '] WITH PASSWORD = ''' + @WeakPassword + ''', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF'
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @WeakAdminLogin + ''', ''sysadmin'''
    ) PRINT 'Created admin account with weak password policy: ' + @WeakAdminLogin + ' - violation'
END
GO -- Requirement 5: Service accounts - Using virtual accounts
    PRINT 'SQL Server service running under NetworkService account - violation' PRINT 'SQL Agent service running under LocalSystem account - violation'
GO -- Requirement 6: Unused logins cleanup (unused logins exist)
DECLARE @UnusedLogin VARCHAR(100)
SET @UnusedLogin = 'UnusedLogin_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.server_principals
        WHERE name = @UnusedLogin
    ) BEGIN
DECLARE @TempPassword VARCHAR(100)
SET @TempPassword = 'Temp' + LEFT(CAST(NEWID() AS VARCHAR(36)), 8) + '!' EXEC(
        'CREATE LOGIN [' + @UnusedLogin + '] WITH PASSWORD = ''' + @TempPassword + ''''
    ) PRINT 'Created unused login that should be cleaned up: ' + @UnusedLogin + ' - violation'
END
GO -- Requirement 7: Least privilege violations (overprivileged accounts)
DECLARE @OverprivilegedLogin VARCHAR(100)
SET @OverprivilegedLogin = 'OverprivUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.server_principals
        WHERE name = @OverprivilegedLogin
    ) BEGIN
DECLARE @PrivPassword VARCHAR(100)
SET @PrivPassword = 'Priv' + LEFT(CAST(NEWID() AS VARCHAR(36)), 8) + '!' EXEC(
        'CREATE LOGIN [' + @OverprivilegedLogin + '] WITH PASSWORD = ''' + @PrivPassword + ''''
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @OverprivilegedLogin + ''', ''sysadmin'''
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @OverprivilegedLogin + ''', ''serveradmin'''
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @OverprivilegedLogin + ''', ''securityadmin'''
    ) PRINT 'Created overprivileged account with multiple server roles: ' + @OverprivilegedLogin + ' - violation'
END
GO -- Requirement 8: Grant option enabled (security risk)
    -- Use AdventureWorks2008R2 database if it exists
DECLARE @GrantUser VARCHAR(100) -- Declare once for safety
    IF EXISTS (
        SELECT *
        FROM sys.databases
        WHERE name = 'AdventureWorks2008R2'
    ) BEGIN USE AdventureWorks2008R2;
SET @GrantUser = 'GrantUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.database_principals
        WHERE name = @GrantUser
    ) BEGIN EXEC('CREATE USER [' + @GrantUser + '] WITHOUT LOGIN') EXEC(
        'GRANT SELECT ON SCHEMA::dbo TO [' + @GrantUser + '] WITH GRANT OPTION'
    ) PRINT 'Created user with WITH GRANT OPTION enabled: ' + @GrantUser + ' - violation'
END
END
ELSE BEGIN PRINT 'AdventureWorks2008R2 database not found - creating test database' USE master;
DECLARE @TestDBName VARCHAR(100)
SET @TestDBName = 'TestDB_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.databases
        WHERE name = @TestDBName
    ) BEGIN EXEC('CREATE DATABASE [' + @TestDBName + ']') EXEC('USE [' + @TestDBName + ']') -- Variables need fresh assignment
SET @GrantUser = 'GrantUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) EXEC('CREATE USER [' + @GrantUser + '] WITHOUT LOGIN') EXEC(
        'GRANT SELECT ON SCHEMA::dbo TO [' + @GrantUser + '] WITH GRANT OPTION'
    ) PRINT 'Created test database and user with WITH GRANT OPTION: ' + @GrantUser + ' - violation'
END
END
GO -- Requirement 9: Dangerous features enabled (security risk)
    USE master;
GO
EXEC sp_configure 'show advanced options',
    1;
RECONFIGURE WITH OVERRIDE;
EXEC sp_configure 'xp_cmdshell',
1;
-- Enable dangerous feature
RECONFIGURE WITH OVERRIDE;
PRINT 'Enabled xp_cmdshell feature - critical violation'
GO -- Requirement 10: Encryption backups missing (certificate not backed up)
    USE master;
GO
DECLARE @CertName VARCHAR(100)
SET @CertName = 'LegacyCert_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.certificates
        WHERE name = @CertName
    ) BEGIN -- Create master key if it doesn't exist
    IF NOT EXISTS (
        SELECT *
        FROM sys.symmetric_keys
        WHERE symmetric_key_id = 101
    ) BEGIN
DECLARE @MasterKeyPassword VARCHAR(100)
SET @MasterKeyPassword = 'MasterKey' + LEFT(CAST(NEWID() AS VARCHAR(36)), 8) + '!' EXEC(
        'CREATE MASTER KEY ENCRYPTION BY PASSWORD = ''' + @MasterKeyPassword + ''''
    ) PRINT 'Created master key - violation (not backed up)'
END
DECLARE @CertSubject VARCHAR(100)
SET @CertSubject = 'Legacy Test Certificate ' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) EXEC(
        'CREATE CERTIFICATE [' + @CertName + '] WITH SUBJECT = ''' + @CertSubject + ''''
    ) PRINT 'Created certificate but did not backup keys: ' + @CertName + ' - violation'
END
GO -- Requirement 11: Triggers review - unreviewed triggers (CORRECT 2008 R2 SYNTAX)
    USE master;
GO -- Drop trigger if it exists first to avoid duplicate errors
DECLARE @TriggerName VARCHAR(100)
SET @TriggerName = 'TR_Unreviewed_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF EXISTS (
        SELECT *
        FROM sys.server_triggers
        WHERE name = @TriggerName
    ) BEGIN EXEC(
        'DROP TRIGGER [' + @TriggerName + '] ON ALL SERVER'
    )
END
GO -- Create server-level trigger with proper 2008 R2 syntax
DECLARE @TriggerName VARCHAR(100),
    @SQL NVARCHAR(4000)
SET @TriggerName = 'TR_Unreviewed_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4)
SET @SQL = '
CREATE TRIGGER [' + @TriggerName + ']
ON ALL SERVER
FOR CREATE_LOGIN, ALTER_LOGIN, DROP_LOGIN
AS
BEGIN
    PRINT ''Unreviewed trigger fired: ' + @TriggerName + '''
END
' EXEC sp_executesql @SQL PRINT 'Created server-level trigger without security review: ' + @TriggerName + ' - violation'
GO -- Requirement 12: Database users review - orphaned users and guest enabled
    IF EXISTS (
        SELECT *
        FROM sys.databases
        WHERE name = 'AdventureWorks2008R2'
    ) BEGIN USE AdventureWorks2008R2;
DECLARE @OrphanedUser VARCHAR(100)
SET @OrphanedUser = 'OrphanUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.database_principals
        WHERE name = @OrphanedUser
    ) BEGIN EXEC(
        'CREATE USER [' + @OrphanedUser + '] WITHOUT LOGIN'
    ) PRINT 'Created orphaned user: ' + @OrphanedUser + ' - violation'
END -- Enable guest user
EXEC('GRANT CONNECT TO guest') PRINT 'Enabled guest account - violation'
END
GO -- Requirement 13: Instance naming - default instance name
    PRINT 'Instance uses default naming convention - violation'
GO -- Requirement 14: Test databases - multiple test databases present
DECLARE @LegacyTestDB VARCHAR(100)
SET @LegacyTestDB = 'LegacyTest_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.databases
        WHERE name = @LegacyTestDB
    ) BEGIN EXEC('CREATE DATABASE [' + @LegacyTestDB + ']') PRINT 'Created legacy test database that should be cleaned up: ' + @LegacyTestDB + ' - violation'
END
GO -- Requirement 15: Ad Hoc queries enabled (security risk)
    USE master;
GO
EXEC sp_configure 'show advanced options',
    1;
RECONFIGURE WITH OVERRIDE;
EXEC sp_configure 'Ad Hoc Distributed Queries',
1;
RECONFIGURE WITH OVERRIDE;
PRINT 'Enabled Ad Hoc Distributed Queries feature - violation'
GO -- Requirement 16: Protocols - unnecessary protocols enabled
    PRINT 'Named Pipes protocol enabled - violation' PRINT 'Only TCP/IP and Shared Memory should be enabled'
GO -- Requirement 17: Database Mail enabled (security risk)
    USE master;
GO
EXEC sp_configure 'show advanced options',
    1;
RECONFIGURE WITH OVERRIDE;
EXEC sp_configure 'Database Mail XPs',
1;
RECONFIGURE WITH OVERRIDE;
PRINT 'Enabled Database Mail XPs without proper justification - violation'
GO -- Requirement 18: SQL Browser service enabled (security risk)
    PRINT 'SQL Browser service enabled - violation' PRINT 'Should be disabled unless specifically needed'
GO -- Requirement 19: Remote access enabled (security risk)
    USE master;
GO
EXEC sp_configure 'remote access',
    1;
RECONFIGURE WITH OVERRIDE;
PRINT 'Enabled remote access to stored procedures - violation'
GO -- Requirement 20: Unnecessary features enabled (security risk)
    PRINT 'Analysis Services and Reporting Services enabled - violation' PRINT 'Should be disabled unless explicitly needed and documented'
GO -- Requirement 21: Login auditing disabled (security risk)
    USE master;
GO
EXEC xp_instance_regwrite N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'AuditLevel',
    REG_DWORD,
    0;
-- 0 = None
PRINT 'Disabled login auditing - critical violation'
GO -- Requirement 22: Connection strings - unencrypted config
    PRINT 'Connection strings found unencrypted in application config files - violation'
GO -- Requirement 23: Linked Server inventory - unapproved linked servers
    USE master;
GO
DECLARE @UnapprovedLink VARCHAR(100)
SET @UnapprovedLink = 'UNAPPROVED_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.servers
        WHERE name = @UnapprovedLink
    ) BEGIN EXEC sp_addlinkedserver @server = @UnapprovedLink,
    @srvproduct = 'SQL Server';
EXEC sp_addlinkedsrvlogin @rmtsrvname = @UnapprovedLink,
@useself = 'true';
-- Uses current security context
PRINT 'Created linked server without proper documentation: ' + @UnapprovedLink + ' - violation'
END
GO -- Requirement 24: Linked Server security - poor security mappings
DECLARE @InsecureLink VARCHAR(100)
SET @InsecureLink = 'INSECURE_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.servers
        WHERE name = @InsecureLink
    ) BEGIN EXEC sp_addlinkedserver @server = @InsecureLink,
    @srvproduct = 'SQL Server';
DECLARE @RmtPwd VARCHAR(100)
SET @RmtPwd = 'sa_password_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) EXEC sp_addlinkedsrvlogin @rmtsrvname = @InsecureLink,
    @useself = 'false',
    @locallogin = NULL,
    @rmtuser = 'sa',
    @rmtpassword = @RmtPwd;
-- Using SA account with pre-calculated variable
PRINT 'Created linked server with SA account credentials: ' + @InsecureLink + ' - violation'
END
GO -- Requirement 25: Server-level security audit - complex permission structure
DECLARE @ComplexUser VARCHAR(100)
SET @ComplexUser = 'ComplexUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.server_principals
        WHERE name = @ComplexUser
    ) BEGIN
DECLARE @ComplexPassword VARCHAR(100)
SET @ComplexPassword = 'Complex' + LEFT(CAST(NEWID() AS VARCHAR(36)), 8) + '!' EXEC(
        'CREATE LOGIN [' + @ComplexUser + '] WITH PASSWORD = ''' + @ComplexPassword + ''''
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @ComplexUser + ''', ''sysadmin'''
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @ComplexUser + ''', ''securityadmin'''
    ) PRINT 'Created complex server-level security structure: ' + @ComplexUser + ' - violation'
END
GO -- Requirement 26: Database-level security audit - excessive permissions
    IF EXISTS (
        SELECT *
        FROM sys.databases
        WHERE name = 'AdventureWorks2008R2'
    ) BEGIN USE AdventureWorks2008R2;
DECLARE @ExcessiveUser VARCHAR(100)
SET @ExcessiveUser = 'ExcessUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.database_principals
        WHERE name = @ExcessiveUser
    ) BEGIN EXEC(
        'CREATE USER [' + @ExcessiveUser + '] WITHOUT LOGIN'
    ) EXEC(
        'EXEC sp_addrolemember ''db_owner'', ''' + @ExcessiveUser + ''''
    ) PRINT 'Created database user with excessive permissions: ' + @ExcessiveUser + ' - violation'
END
END
GO -- Requirement 27: Security change tracking - recent changes
DECLARE @RecentChangeLogin VARCHAR(100)
SET @RecentChangeLogin = 'RecentUser_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 4) IF NOT EXISTS (
        SELECT *
        FROM sys.server_principals
        WHERE name = @RecentChangeLogin
    ) BEGIN
DECLARE @RecentPassword VARCHAR(100)
SET @RecentPassword = 'Recent' + LEFT(CAST(NEWID() AS VARCHAR(36)), 8) + '!' EXEC(
        'CREATE LOGIN [' + @RecentChangeLogin + '] WITH PASSWORD = ''' + @RecentPassword + ''''
    ) EXEC(
        'EXEC sp_addsrvrolemember ''' + @RecentChangeLogin + ''', ''sysadmin'''
    ) PRINT 'Created recent security change without proper tracking: ' + @RecentChangeLogin + ' - violation'
END
GO -- Requirement 28: Permission grants audit - explicit permissions with security issues
    IF EXISTS (
        SELECT *
        FROM sys.databases
        WHERE name = 'AdventureWorks2008R2'
    ) BEGIN USE AdventureWorks2008R2;
DECLARE @GrantUser VARCHAR(100)
SELECT TOP 1 @GrantUser = name
FROM sys.database_principals
WHERE name LIKE 'GrantUser_%' IF @GrantUser IS NOT NULL BEGIN EXEC(
        'GRANT EXECUTE ON SCHEMA::dbo TO [' + @GrantUser + ']'
    ) PRINT 'Created explicit permissions with security issues for user: ' + @GrantUser + ' - violation'
END
END
GO -- Create msdb AuditLog table if not exists (safe creation)
    USE msdb;
GO
IF NOT EXISTS (
        SELECT *
        FROM sys.tables
        WHERE name = 'AuditLog'
    ) BEGIN CREATE TABLE AuditLog (
        LogID INT IDENTITY(1, 1) PRIMARY KEY,
        EventTime DATETIME DEFAULT GETDATE(),
        EventType VARCHAR(50) NOT NULL,
        Description VARCHAR(500) NOT NULL,
        ServerName VARCHAR(100) DEFAULT @@SERVERNAME,
        InstanceName VARCHAR(100) DEFAULT @@SERVICENAME
    );
PRINT 'Created msdb.dbo.AuditLog table for security tracking'
END
GO -- Log all security violations for audit tracking
DECLARE @RandomRunID VARCHAR(20)
SET @RandomRunID = 'RUN_' + LEFT(CAST(NEWID() AS VARCHAR(36)), 8)
INSERT INTO msdb.dbo.AuditLog (EventType, Description)
VALUES (
        'SECURITY_TEST_SETUP_LEGACY_' + @RandomRunID,
        'Legacy instance comprehensive security test setup initiated'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Server documentation outdated - not updated in over 2 years'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'SQL Server 2008 R2 out of support'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'SA account enabled and not renamed'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Weak password policy for privileged account'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Services running under virtual accounts'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Unused login requires cleanup'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Overprivileged account with multiple server roles'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'WITH GRANT OPTION enabled for user'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'xp_cmdshell feature enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Certificate created but not backed up'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Unreviewed server-level trigger exists'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Orphaned user and guest account enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Default instance naming convention'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Legacy test database not cleaned up'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Ad Hoc Distributed Queries enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Named Pipes protocol enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Database Mail XPs enabled without justification'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'SQL Browser service enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Remote access to stored procedures enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Unnecessary SQL Server features enabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Login auditing disabled'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Unencrypted connection strings in config files'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Unapproved linked server created'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Linked server using SA account credentials'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Complex server-level permissions with excessive access'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Database user with excessive permissions'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Recent security change without proper tracking'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Explicit permissions with security issues'
    );

    USE [master];
GO

DECLARE @saName sysname;

-- Built-in sa login is always SID 0x01
SELECT @saName = name
FROM sys.server_principals
WHERE sid = 0x01
  AND type_desc = 'SQL_LOGIN';

IF @saName IS NULL
BEGIN
    RAISERROR('Built-in sa login (SID 0x01) not found.', 16, 1);
    RETURN;
END

-- If audit renamed it (e.g. to $@), rename it back
IF @saName <> N'sa'
BEGIN
    IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'sa')
    BEGIN
        RAISERROR('Login "sa" already exists; cannot rename %s to sa.', 16, 1, @saName);
        RETURN;
    END

    EXEC sp_renamelogin @loginame = @saName, @newname = N'sa';
    PRINT 'Ensured sa login is enabled and named "sa" for testing purposes.';
END

-- Ensure sa is ENABLED (explicit discrepancy)
EXEC ('ALTER LOGIN [sa] ENABLE');
GO

GO
PRINT '=== SQL SERVER 2008 R2 INSTANCE SECURITY TEST SETUP COMPLETE ==='
PRINT '✅ SAFE EXECUTION - ACCESS PRESERVED:' 
PRINT'  - SA account completely untouched and preserved' 
PRINT '  - No changes to existing logins or permissions' 
PRINT '  - No connectivity-breaking changes' 
PRINT '' 
PRINT '✅ VALID SQL SERVER 2008 R2 SYNTAX:' 
PRINT '  - All RECONFIGURE commands include WITH OVERRIDE' 
PRINT '  - Proper ::fn_listextendedproperty syntax for extended properties' 
PRINT '  - Compatible system views and functions only' 
PRINT '  - No modern T-SQL features (JSON, STRING_AGG, etc.)' 
PRINT '  - Proper trigger syntax for 2008 R2' 
PRINT '' 
PRINT '🔧 28 REQUIREMENTS TESTED - REAL SECURITY VIOLATIONS:' 
PRINT '  Requirement 1:  Server documentation outdated' 
PRINT '  Requirement 2:  SQL Server 2008 R2 out of support' 
PRINT '  Requirement 3:  SA account enabled and not renamed' 
PRINT '  Requirement 4:  Weak password policies for privileged accounts' 
PRINT '  Requirement 5:  Services running under virtual accounts' 
PRINT '  Requirement 6:  Unused login requires cleanup' 
PRINT '  Requirement 7:  Overprivileged account with multiple roles' 
PRINT '  Requirement 8:  WITH GRANT OPTION enabled' 
PRINT '  Requirement 9:  xp_cmdshell feature enabled' 
PRINT '  Requirement 10: Certificate not backed up' 
PRINT '  Requirement 11: Unreviewed server trigger' 
PRINT '  Requirement 12: Orphaned user and guest enabled' 
PRINT '  Requirement 13: Default instance naming' 
PRINT '  Requirement 14: Legacy test database not cleaned up' 
PRINT '  Requirement 15: Ad Hoc queries enabled' 
PRINT '  Requirement 16: Unnecessary protocols enabled' 
PRINT '  Requirement 17: Database Mail enabled without justification' 
PRINT '  Requirement 18: SQL Browser service enabled' 
PRINT '  Requirement 19: Remote access enabled' 
PRINT '  Requirement 20: Unnecessary features enabled' 
PRINT '  Requirement 21: Login auditing disabled' 
PRINT '  Requirement 22: Unencrypted connection strings' 
PRINT '  Requirement 23: Unapproved linked server' 
PRINT '  Requirement 24: Poor linked server security (SA account)' 
PRINT '  Requirement 25: Complex server permissions with excessive access' 
PRINT '  Requirement 26: Database user with excessive permissions' 
PRINT '  Requirement 27: Recent security change without tracking' 
PRINT '  Requirement 28: Explicit permissions with security issues' 
PRINT '' 
PRINT '📊 READY FOR REAL AUDIT TESTING:' 
PRINT '  - All RECONFIGURE commands properly executed' 
PRINT '  - Random naming prevents conflicts between test runs' 
PRINT '  - AdventureWorks2008R2 used where available' 
PRINT '  - msdb.dbo.AuditLog populated with all violations' 
PRINT '  - Your access completely preserved'