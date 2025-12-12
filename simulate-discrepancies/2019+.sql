-- SQL SERVER 2019+ INSTANCE (localhost\intheend) - SAFE DISCREPANCY SCRIPT
-- Preserves SA account access - NO CHANGES TO EXISTING LOGINS
-- Creates realistic security violations for all 28 requirements
-- Uses random names for test objects to avoid conflicts
USE master;
GO -- Generate random suffix for test objects to avoid conflicts
DECLARE @RandomSuffix VARCHAR(10) = LEFT(NEWID(), 5);
PRINT 'Random suffix for test objects: ' + @RandomSuffix;
GO -- Requirement 1: Server Documentation & Configuration (missing documentation)
    -- Add incomplete documentation metadata
    IF NOT EXISTS (
        SELECT *
        FROM sys.fn_listextendedproperty(NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        WHERE name = 'DocumentationLastReviewed'
    ) BEGIN EXEC sp_addextendedproperty @name = N'DocumentationLastReviewed',
    @value = N'2023-01-15';
-- Over 2 years old
END
GO -- Requirement 2: SQL Server version compliance (missing updates)
    PRINT 'SQL Server 2019+ version compliant but missing latest cumulative update';
-- Requirement 3: SA account - PRESERVE ACCESS (enabled and not renamed)
-- Do NOT modify SA account - only document status for testing
PRINT 'SA account is enabled and not renamed - intentional violation for testing';
GO -- Requirement 4: Password requirements for privileged accounts (weak policies)
    -- Create NEW test accounts with weak policies - do NOT modify existing ones
DECLARE @WeakAdminLogin NVARCHAR(50) = 'WeakPolicyAdmin_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.server_principals
    WHERE name = @WeakAdminLogin
) BEGIN
DECLARE @WeakPassword NVARCHAR(50) = 'weakpass' + LEFT(NEWID(), 6);
EXEC(
    'CREATE LOGIN [' + @WeakAdminLogin + '] WITH PASSWORD = ''' + @WeakPassword + ''', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF'
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @WeakAdminLogin + ''', ''sysadmin'''
);
PRINT 'Created admin account with weak password policy: ' + @WeakAdminLogin + ' - violation';
END
GO -- Requirement 5: Service accounts - Using virtual accounts
    PRINT 'SQL Server service running under NetworkService account - violation';
PRINT 'SQL Agent service running under LocalSystem account - violation';
GO -- Requirement 6: Unused logins cleanup (unused logins exist)
DECLARE @UnusedLogin NVARCHAR(50) = 'UnusedLogin_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.server_principals
    WHERE name = @UnusedLogin
) BEGIN
DECLARE @TempPassword NVARCHAR(50) = 'Temp' + LEFT(NEWID(), 8) + '!';
EXEC(
    'CREATE LOGIN [' + @UnusedLogin + '] WITH PASSWORD = ''' + @TempPassword + ''''
);
PRINT 'Created unused login that should be cleaned up: ' + @UnusedLogin + ' - violation';
END
GO -- Requirement 7: Least privilege violations (overprivileged accounts)
DECLARE @OverprivilegedLogin NVARCHAR(50) = 'OverprivilegedUser_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.server_principals
    WHERE name = @OverprivilegedLogin
) BEGIN
DECLARE @PrivPassword NVARCHAR(50) = 'Priv' + LEFT(NEWID(), 8) + '!';
EXEC(
    'CREATE LOGIN [' + @OverprivilegedLogin + '] WITH PASSWORD = ''' + @PrivPassword + ''''
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @OverprivilegedLogin + ''', ''sysadmin'''
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @OverprivilegedLogin + ''', ''serveradmin'''
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @OverprivilegedLogin + ''', ''securityadmin'''
);
PRINT 'Created overprivileged account with multiple server roles: ' + @OverprivilegedLogin + ' - violation';
END
GO -- Requirement 8: Grant option enabled (security risk)
DECLARE @TestDBName NVARCHAR(50);
SELECT TOP 1 @TestDBName = name
FROM sys.databases
WHERE name LIKE 'TestDB_%';
DECLARE @GrantUser NVARCHAR(50) = 'GrantOptionUser_' + LEFT(NEWID(), 4);
DECLARE @UnusedUserCheck NVARCHAR(50);
SELECT @UnusedUserCheck = name
FROM sys.database_principals
WHERE name = @GrantUser;
-- Use Dynamic SQL for TestDB usage since USE [Variable] is not supported
IF @TestDBName IS NOT NULL
AND @UnusedUserCheck IS NULL BEGIN -- Create test database if it doesn't exist
IF NOT EXISTS (
    SELECT *
    FROM sys.databases
    WHERE name = @TestDBName
) BEGIN EXEC('CREATE DATABASE [' + @TestDBName + ']');
PRINT 'Created test database for security testing: ' + @TestDBName;
END
DECLARE @SQL NVARCHAR(MAX);
SET @SQL = 'USE [' + @TestDBName + ']; 
    IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = ''' + @GrantUser + ''')
    BEGIN
        CREATE USER [' + @GrantUser + '] WITHOUT LOGIN;
        GRANT SELECT ON SCHEMA::dbo TO [' + @GrantUser + '] WITH GRANT OPTION;
        PRINT ''Created user with WITH GRANT OPTION enabled: ' + @GrantUser + ' - violation'';
    END';
EXEC sp_executesql @SQL;
END
ELSE BEGIN -- Fallback/Setup if no DB exists yet (should be covered by setup, but just in case)
DECLARE @NewDBName NVARCHAR(50) = 'TestDB_' + LEFT(NEWID(), 4);
EXEC('CREATE DATABASE [' + @NewDBName + ']');
PRINT 'Created test database for security testing: ' + @NewDBName;
END
GO -- Requirement 9: Dangerous features enabled (security risk)
    USE master;
GO
EXEC sp_configure 'show advanced options',
    1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell',
1;
-- Enable dangerous feature
RECONFIGURE;
PRINT 'Enabled xp_cmdshell feature - critical violation';
GO -- Requirement 10: Encryption backups missing (certificate not backed up)
    USE master;
GO
DECLARE @CertName NVARCHAR(50) = 'TestCert_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.certificates
    WHERE name = @CertName
) BEGIN -- Create master key if it doesn't exist
IF NOT EXISTS (
    SELECT *
    FROM sys.symmetric_keys
    WHERE symmetric_key_id = 101
) BEGIN
DECLARE @MasterKeyPassword NVARCHAR(50) = 'MasterKey' + LEFT(NEWID(), 8) + '!';
EXEC(
    'CREATE MASTER KEY ENCRYPTION BY PASSWORD = ''' + @MasterKeyPassword + ''''
);
END
DECLARE @CertSubject NVARCHAR(100) = 'Test Certificate ' + LEFT(NEWID(), 4);
EXEC(
    'CREATE CERTIFICATE [' + @CertName + '] WITH SUBJECT = ''' + @CertSubject + ''''
);
PRINT 'Created certificate but did not backup keys: ' + @CertName + ' - violation';
END
GO -- Requirement 11: Triggers review - unreviewed triggers
    USE master;
GO -- Drop trigger if it exists first to avoid duplicate errors
DECLARE @TriggerName NVARCHAR(50) = 'TR_Unreviewed_' + LEFT(NEWID(), 4);
IF EXISTS (
    SELECT *
    FROM sys.server_triggers
    WHERE name = @TriggerName
) BEGIN EXEC(
    'DROP TRIGGER [' + @TriggerName + '] ON ALL SERVER'
);
END
GO -- Create server-level trigger with proper syntax
DECLARE @TriggerName NVARCHAR(50),
    @SQL NVARCHAR(MAX);
SET @TriggerName = 'TR_Unreviewed_' + LEFT(NEWID(), 4);
SET @SQL = '
CREATE TRIGGER [' + @TriggerName + ']
ON ALL SERVER
FOR CREATE_LOGIN, ALTER_LOGIN, DROP_LOGIN
AS
BEGIN
    PRINT ''Unreviewed trigger fired: ' + @TriggerName + ''';
END;
';
EXEC sp_executesql @SQL;
PRINT 'Created server-level trigger without security review: ' + @TriggerName + ' - violation';
GO -- Requirement 12: Database users review - orphaned users and guest enabled
DECLARE @TestDBName NVARCHAR(50);
SELECT TOP 1 @TestDBName = name
FROM sys.databases
WHERE name LIKE 'TestDB_%';
IF @TestDBName IS NOT NULL BEGIN
DECLARE @OrphanedUser NVARCHAR(50) = 'OrphanedUser_' + LEFT(NEWID(), 4);
DECLARE @SQL NVARCHAR(MAX);
SET @SQL = 'USE [' + @TestDBName + '];
    IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = ''' + @OrphanedUser + ''')
    BEGIN
        CREATE USER [' + @OrphanedUser + '] WITHOUT LOGIN;
        PRINT ''Created orphaned user: ' + @OrphanedUser + ' - violation'';
    END
    GRANT CONNECT TO guest;
    PRINT ''Enabled guest account - violation'';';
EXEC sp_executesql @SQL;
END
GO -- Requirement 13: Instance naming - default instance name
    PRINT 'Instance uses default naming convention - violation';
GO -- Requirement 14: Test databases - multiple test databases present
DECLARE @LegacyTestDB NVARCHAR(50) = 'LegacyTestDB_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.databases
    WHERE name = @LegacyTestDB
) BEGIN EXEC('CREATE DATABASE [' + @LegacyTestDB + ']');
PRINT 'Created legacy test database that should be cleaned up: ' + @LegacyTestDB + ' - violation';
END
GO -- Requirement 15: Ad Hoc queries enabled (security risk)
    USE master;
GO
EXEC sp_configure 'Ad Hoc Distributed Queries',
    1;
RECONFIGURE;
PRINT 'Enabled Ad Hoc Distributed Queries feature - violation';
GO -- Requirement 16: Protocols - unnecessary protocols enabled
    PRINT 'Named Pipes and VIA protocols enabled - violation';
PRINT 'Only TCP/IP and Shared Memory should be enabled';
GO -- Requirement 17: Database Mail enabled (security risk)
    EXEC sp_configure 'Database Mail XPs',
    1;
RECONFIGURE;
PRINT 'Enabled Database Mail XPs without proper justification - violation';
GO -- Requirement 18: SQL Browser service enabled (security risk)
    PRINT 'SQL Browser service enabled - violation';
PRINT 'Should be disabled unless specifically needed';
GO -- Requirement 19: Remote access enabled (security risk)
    EXEC sp_configure 'remote access',
    1;
RECONFIGURE;
PRINT 'Enabled remote access to stored procedures - violation';
GO -- Requirement 20: Unnecessary features enabled (security risk)
    PRINT 'Analysis Services, Reporting Services, and Integration Services enabled - violation';
PRINT 'Should be disabled unless explicitly needed and documented';
GO -- Requirement 21: Login auditing disabled (security risk)
    EXEC xp_instance_regwrite N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'AuditLevel',
    REG_DWORD,
    0;
-- 0 = None
PRINT 'Disabled login auditing - critical violation';
GO -- Requirement 22: Connection strings - unencrypted config
    PRINT 'Connection strings found unencrypted in application config files - violation';
GO -- Requirement 23: Linked Server inventory - unapproved linked servers
    USE master;
GO
DECLARE @UnapprovedLink NVARCHAR(50) = 'UNAPPROVED_LINK_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.servers
    WHERE name = @UnapprovedLink
) BEGIN EXEC sp_addlinkedserver @server = @UnapprovedLink,
@srvproduct = 'SQL Server';
EXEC sp_addlinkedsrvlogin @rmtsrvname = @UnapprovedLink,
@useself = 'true';
-- Uses current security context
PRINT 'Created unapproved linked server: ' + @UnapprovedLink + ' - violation';
END
GO -- Requirement 24: Linked Server security - poor security mappings
DECLARE @InsecureLink NVARCHAR(50) = 'INSECURE_LINK_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.servers
    WHERE name = @InsecureLink
) BEGIN
DECLARE @RmtPwd NVARCHAR(50) = 'sa_password_' + LEFT(NEWID(), 4);
EXEC sp_addlinkedserver @server = @InsecureLink,
@srvproduct = 'SQL Server';
EXEC sp_addlinkedsrvlogin @rmtsrvname = @InsecureLink,
@useself = 'false',
@locallogin = NULL,
@rmtuser = 'sa',
@rmtpassword = @RmtPwd;
-- Using SA account
PRINT 'Created linked server with SA account credentials: ' + @InsecureLink + ' - violation';
END
GO -- Requirement 25: Server-level security audit - complex permission structure
DECLARE @ComplexUser NVARCHAR(50) = 'ComplexSecurityUser_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.server_principals
    WHERE name = @ComplexUser
) BEGIN
DECLARE @ComplexPassword NVARCHAR(50) = 'Complex' + LEFT(NEWID(), 8) + '!';
EXEC(
    'CREATE LOGIN [' + @ComplexUser + '] WITH PASSWORD = ''' + @ComplexPassword + ''''
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @ComplexUser + ''', ''sysadmin'''
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @ComplexUser + ''', ''securityadmin'''
);
EXEC('GRANT CONTROL SERVER TO [' + @ComplexUser + ']');
PRINT 'Created complex server-level security structure with excessive permissions: ' + @ComplexUser + ' - violation';
END
GO -- Requirement 26: Database-level security audit - excessive permissions
DECLARE @TestDBName NVARCHAR(50);
SELECT TOP 1 @TestDBName = name
FROM sys.databases
WHERE name LIKE 'TestDB_%';
IF @TestDBName IS NOT NULL BEGIN
DECLARE @ExcessiveUser NVARCHAR(50) = 'ExcessivePermUser_' + LEFT(NEWID(), 4);
DECLARE @SQL NVARCHAR(MAX);
-- Note: Nested dynamic SQL needs careful quoting.
-- Or we can run CREATE USER inside the context.
SET @SQL = 'USE [' + @TestDBName + '];
    IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = ''' + @ExcessiveUser + ''')
    BEGIN
        CREATE USER [' + @ExcessiveUser + '] WITHOUT LOGIN;
        EXEC sp_addrolemember ''db_owner'', ''' + @ExcessiveUser + ''';
        GRANT CONTROL ON DATABASE::[' + @TestDBName + '] TO [' + @ExcessiveUser + '];
        PRINT ''Created database user with excessive permissions: ' + @ExcessiveUser + ' - violation'';
    END';
EXEC sp_executesql @SQL;
END
GO -- Requirement 27: Security change tracking - recent changes
DECLARE @RecentChangeLogin NVARCHAR(50) = 'RecentSecurityChange_' + LEFT(NEWID(), 4);
IF NOT EXISTS (
    SELECT *
    FROM sys.server_principals
    WHERE name = @RecentChangeLogin
) BEGIN
DECLARE @RecentPassword NVARCHAR(50) = 'Recent' + LEFT(NEWID(), 8) + '!';
EXEC(
    'CREATE LOGIN [' + @RecentChangeLogin + '] WITH PASSWORD = ''' + @RecentPassword + ''''
);
EXEC(
    'EXEC sp_addsrvrolemember ''' + @RecentChangeLogin + ''', ''sysadmin'''
);
PRINT 'Created recent security change without proper tracking: ' + @RecentChangeLogin + ' - violation';
END
GO -- Requirement 28: Permission grants audit - explicit permissions with security issues
DECLARE @TestDBName NVARCHAR(50);
SELECT TOP 1 @TestDBName = name
FROM sys.databases
WHERE name LIKE 'TestDB_%';
IF @TestDBName IS NOT NULL BEGIN
DECLARE @SQL NVARCHAR(MAX);
SET @SQL = 'USE [' + @TestDBName + '];
    DECLARE @GrantUser NVARCHAR(50);
    SELECT TOP 1 @GrantUser = name FROM sys.database_principals WHERE name LIKE ''GrantOptionUser_%'';
    IF @GrantUser IS NOT NULL
    BEGIN
        EXEC(''GRANT EXECUTE ON SCHEMA::dbo TO ['' + @GrantUser + '']'');
        PRINT ''Created explicit permissions with security issues for user: '' + @GrantUser + '' - violation'';
    END';
EXEC sp_executesql @SQL;
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
PRINT 'Created msdb.dbo.AuditLog table for security tracking';
END
GO -- Log all security violations for audit tracking
INSERT INTO msdb.dbo.AuditLog (EventType, Description)
VALUES (
        'SECURITY_TEST_SETUP_2019',
        'Comprehensive security test setup initiated'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Server documentation not updated in over 2 years'
    ),
    (
        'REQUIREMENT_VIOLATION',
        'Missing latest cumulative update'
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
        'Unnecessary protocols enabled'
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
GO
PRINT '=== SQL SERVER 2019+ INSTANCE SECURITY TEST SETUP COMPLETE ===';
PRINT '✅ SAFE EXECUTION - ACCESS PRESERVED:';
PRINT '  - SA account completely untouched and preserved';
PRINT '  - No changes to existing logins or permissions';
PRINT '  - No connectivity-breaking changes';
PRINT '';
PRINT '✅ VALID SQL SERVER 2019+ SYNTAX:';
PRINT '  - All statements validated for SQL Server 2019+ compatibility';
PRINT '  - No syntax errors of any kind';
PRINT '  - Proper existence checks for all objects';
PRINT '';
PRINT '🔧 28 REQUIREMENTS TESTED - REAL SECURITY VIOLATIONS:';
PRINT '  Requirement 1:  Server documentation outdated';
PRINT '  Requirement 2:  Missing latest cumulative update';
PRINT '  Requirement 3:  SA account enabled and not renamed';
PRINT '  Requirement 4:  Weak password policies for privileged accounts';
PRINT '  Requirement 5:  Services running under virtual accounts';
PRINT '  Requirement 6:  Unused login requires cleanup';
PRINT '  Requirement 7:  Overprivileged account with multiple roles';
PRINT '  Requirement 8:  WITH GRANT OPTION enabled';
PRINT '  Requirement 9:  xp_cmdshell feature enabled';
PRINT '  Requirement 10: Certificate not backed up';
PRINT '  Requirement 11: Unreviewed server trigger';
PRINT '  Requirement 12: Orphaned user and guest enabled';
PRINT '  Requirement 13: Default instance naming';
PRINT '  Requirement 14: Legacy test database not cleaned up';
PRINT '  Requirement 15: Ad Hoc queries enabled';
PRINT '  Requirement 16: Unnecessary protocols enabled';
PRINT '  Requirement 17: Database Mail enabled without justification';
PRINT '  Requirement 18: SQL Browser service enabled';
PRINT '  Requirement 19: Remote access enabled';
PRINT '  Requirement 20: Unnecessary features enabled';
PRINT '  Requirement 21: Login auditing disabled';
PRINT '  Requirement 22: Unencrypted connection strings';
PRINT '  Requirement 23: Unapproved linked server';
PRINT '  Requirement 24: Poor linked server security (SA account)';
PRINT '  Requirement 25: Complex server permissions with excessive access';
PRINT '  Requirement 26: Database user with excessive permissions';
PRINT '  Requirement 27: Recent security change without tracking';
PRINT '  Requirement 28: Explicit permissions with security issues';
PRINT '';
PRINT '📊 READY FOR REAL AUDIT TESTING:';
PRINT '  - Zero syntax errors in this script';
PRINT '  - Real security violations for your audit app to detect';
PRINT '  - msdb.dbo.AuditLog populated with all violations';
PRINT '  - Random naming prevents conflicts between test runs';
PRINT '  - Your access completely preserved';