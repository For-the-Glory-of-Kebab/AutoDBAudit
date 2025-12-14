/* ============================================================
   REVERT - SQL Server 2019+ discrepancy cleanup
   ============================================================ */

USE master;
GO

/* 1) Revert instance configuration changes */
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

EXEC sp_configure 'xp_cmdshell', 0;
RECONFIGURE;

EXEC sp_configure 'Ad Hoc Distributed Queries', 0;
RECONFIGURE;

EXEC sp_configure 'Database Mail XPs', 0;
RECONFIGURE;

EXEC sp_configure 'remote access', 0;
RECONFIGURE;

/* Optional: hide advanced options again */
EXEC sp_configure 'show advanced options', 0;
RECONFIGURE;
GO

/* Login auditing registry revert (script sets AuditLevel=0). :contentReference[oaicite:7]{index=7} */
DECLARE @AuditLevelTarget INT = 2; -- adjust to your baseline if needed
EXEC xp_instance_regwrite
    N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'AuditLevel',
    REG_DWORD,
    @AuditLevelTarget;
GO

/* 2a) Drop LegacyTestDB (Aggressive Cleanup - unique to this script) */
DECLARE @legacydb SYSNAME;
DECLARE @sql NVARCHAR(MAX);

DECLARE legacy_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name FROM sys.databases WHERE name LIKE 'LegacyTestDB[_]%' ESCAPE '_';

OPEN legacy_cur;
FETCH NEXT FROM legacy_cur INTO @legacydb;

WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        EXEC('ALTER DATABASE [' + @legacydb + '] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;');
        EXEC('DROP DATABASE [' + @legacydb + '];');
        PRINT 'Dropped legacy database (Force): ' + @legacydb;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not drop legacy database ' + @legacydb + ' : ' + ERROR_MESSAGE();
    END CATCH
    FETCH NEXT FROM legacy_cur INTO @legacydb;
END
CLOSE legacy_cur;
DEALLOCATE legacy_cur;

/* 2b) Drop TestDB (Conditional Cleanup - check for markers) */
DECLARE @testdb SYSNAME;
DECLARE @hasMarker INT;

DECLARE test_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name FROM sys.databases WHERE name LIKE 'TestDB[_]%' ESCAPE '_';

OPEN test_cur;
FETCH NEXT FROM test_cur INTO @testdb;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @hasMarker = 0;
    SET @sql = N'USE [' + @testdb + N'];
    SELECT @hasMarkerOUT = CASE WHEN EXISTS (
        SELECT 1 FROM sys.database_principals
        WHERE name LIKE ''GrantOptionUser[_]%'' ESCAPE ''_''
           OR name LIKE ''OrphanedUser[_]%''    ESCAPE ''_''
           OR name LIKE ''ExcessivePermUser[_]%'' ESCAPE ''_''
    ) THEN 1 ELSE 0 END;';
    
    BEGIN TRY
        EXEC sp_executesql @sql, N'@hasMarkerOUT INT OUTPUT', @hasMarkerOUT=@hasMarker OUTPUT;
    END TRY
    BEGIN CATCH
        SET @hasMarker = 0;
    END CATCH;

    IF @hasMarker = 1
    BEGIN
        BEGIN TRY
            EXEC('ALTER DATABASE [' + @testdb + '] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;');
            EXEC('DROP DATABASE [' + @testdb + '];');
            PRINT 'Dropped test database: ' + @testdb;
        END TRY
        BEGIN CATCH
             PRINT 'WARN: could not drop database ' + @testdb + ' : ' + ERROR_MESSAGE();
        END CATCH
    END
    FETCH NEXT FROM test_cur INTO @testdb;
END
CLOSE test_cur;
DEALLOCATE test_cur;
GO

/* 3) Drop linked servers created by the script */
DECLARE @ls SYSNAME;

DECLARE ls_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name
FROM sys.servers
WHERE name LIKE 'UNAPPROVED[_]LINK[_]%' ESCAPE '_'
   OR name LIKE 'INSECURE[_]LINK[_]%'   ESCAPE '_';

OPEN ls_cur;
FETCH NEXT FROM ls_cur INTO @ls;

WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        EXEC sp_dropserver @server = @ls, @droplogins = 'droplogins';
        PRINT 'Dropped linked server: ' + @ls;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not drop linked server ' + ISNULL(@ls,'(null)') + ' : ' + ERROR_MESSAGE();
    END CATCH;

    FETCH NEXT FROM ls_cur INTO @ls;
END

CLOSE ls_cur;
DEALLOCATE ls_cur;
GO

/* 4) Drop server triggers created by the script */
DECLARE @tr SYSNAME;
DECLARE @sql NVARCHAR(MAX);

DECLARE tr_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name
FROM sys.server_triggers
WHERE name LIKE 'TR[_]Unreviewed[_]%' ESCAPE '_';

OPEN tr_cur;
FETCH NEXT FROM tr_cur INTO @tr;

WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        SET @sql = N'DROP TRIGGER [' + @tr + N'] ON ALL SERVER;';
        EXEC sp_executesql @sql;
        PRINT 'Dropped server trigger: ' + @tr;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not drop trigger ' + ISNULL(@tr,'(null)') + ' : ' + ERROR_MESSAGE();
    END CATCH;

    FETCH NEXT FROM tr_cur INTO @tr;
END

CLOSE tr_cur;
DEALLOCATE tr_cur;
GO

/* 5) Drop certificates created by the script (TestCert_*) */
DECLARE @cert SYSNAME;
DECLARE @sql NVARCHAR(MAX);

DECLARE cert_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name
FROM sys.certificates
WHERE name LIKE 'TestCert[_]%' ESCAPE '_';

OPEN cert_cur;
FETCH NEXT FROM cert_cur INTO @cert;

WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        SET @sql = N'DROP CERTIFICATE [' + @cert + N'];';
        EXEC sp_executesql @sql;
        PRINT 'Dropped certificate: ' + @cert;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not drop certificate ' + ISNULL(@cert,'(null)') + ' : ' + ERROR_MESSAGE();
    END CATCH;

    FETCH NEXT FROM cert_cur INTO @cert;
END

CLOSE cert_cur;
DEALLOCATE cert_cur;
GO

/* 6) Drop server logins created by the script */
DECLARE @login SYSNAME;
DECLARE @sql NVARCHAR(MAX);

DECLARE login_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name
FROM sys.server_principals
WHERE type_desc = 'SQL_LOGIN'
  AND (
        name LIKE 'WeakPolicyAdmin[_]%'       ESCAPE '_'
     OR name LIKE 'UnusedLogin[_]%'           ESCAPE '_'
     OR name LIKE 'OverprivilegedUser[_]%'    ESCAPE '_'
     OR name LIKE 'ComplexSecurityUser[_]%'   ESCAPE '_'
     OR name LIKE 'RecentSecurityChange[_]%'  ESCAPE '_'
  );

OPEN login_cur;
FETCH NEXT FROM login_cur INTO @login;

WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        SET @sql = N'DROP LOGIN [' + @login + N'];';
        EXEC sp_executesql @sql;
        PRINT 'Dropped login: ' + @login;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not drop login ' + ISNULL(@login,'(null)') + ' : ' + ERROR_MESSAGE();
    END CATCH;

    FETCH NEXT FROM login_cur INTO @login;
END

CLOSE login_cur;
DEALLOCATE login_cur;
GO

/* 7) Clean DB-level residue (users + guest connect) */
DECLARE @db SYSNAME;
DECLARE @sql NVARCHAR(MAX);

DECLARE db_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name
FROM sys.databases
WHERE state_desc = 'ONLINE'
  AND name NOT IN ('master','model','msdb','tempdb');

OPEN db_cur;
FETCH NEXT FROM db_cur INTO @db;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'
USE [' + @db + N'];

BEGIN TRY
    REVOKE CONNECT FROM guest;
END TRY
BEGIN CATCH
END CATCH;

DECLARE @u SYSNAME;
DECLARE u_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT name
FROM sys.database_principals
WHERE (
        name LIKE ''GrantOptionUser[_]%''   ESCAPE ''_''
     OR name LIKE ''OrphanedUser[_]%''      ESCAPE ''_''
     OR name LIKE ''ExcessivePermUser[_]%'' ESCAPE ''_''
);

OPEN u_cur;
FETCH NEXT FROM u_cur INTO @u;

WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        EXEC (''DROP USER ['' + @u + '']'');
        PRINT ''Dropped user '' + @u + '' in ' + @db + ''';
    END TRY
    BEGIN CATCH
        PRINT ''WARN: could not drop user '' + ISNULL(@u,''(null)'') + '' in ' + @db + ': '' + ERROR_MESSAGE();
    END CATCH;

    FETCH NEXT FROM u_cur INTO @u;
END

CLOSE u_cur;
DEALLOCATE u_cur;
';
    BEGIN TRY
        EXEC sp_executesql @sql;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: DB cleanup failed in ' + @db + ' : ' + ERROR_MESSAGE();
    END CATCH;

    FETCH NEXT FROM db_cur INTO @db;
END

CLOSE db_cur;
DEALLOCATE db_cur;
GO

/* 8) Drop Extended Property (DocumentationLastReviewed) */
BEGIN TRY
    EXEC sp_dropextendedproperty @name = N'DocumentationLastReviewed';
    PRINT 'Dropped extended property: DocumentationLastReviewed';
END TRY
BEGIN CATCH
    -- Ignore if not exists (error 15135)
END CATCH;
GO

/* 9) Drop Cleanup Audit Log Table */
BEGIN TRY
    IF EXISTS (SELECT * FROM msdb.sys.tables WHERE name = 'AuditLog')
    BEGIN
        DROP TABLE msdb.dbo.AuditLog;
        PRINT 'Dropped table: msdb.dbo.AuditLog';
    END
END TRY
BEGIN CATCH
    PRINT 'WARN: Could not drop msdb.dbo.AuditLog: ' + ERROR_MESSAGE();
END CATCH;
GO

PRINT '=== REVERT COMPLETE (2019+) ===';
GO
