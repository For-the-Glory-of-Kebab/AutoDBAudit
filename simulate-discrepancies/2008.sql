/* ================================================================================================
   Workspace Discrepancy Simulator - APPLY (SQL Server 2008)
   ------------------------------------------------------------------------------------------------
   Purpose: Create randomized discrepancies for audit/fix testing.
   Flow: APPLY => run audit/fixes => REVERT => APPLY again...

   Reliability-first rules:
     - Pure T-SQL only.
     - PRINT-only messages (no result sets required, no server-side log tables).
     - Each step is wrapped in TRY/CATCH; failures are PRINTed and the script continues.
     - For anything not enforceable via T-SQL: this script does NOTHING.

   SQL Server 2008 compatibility notes:
     - Uses RAISERROR instead of THROW.
     - Uses sp_addsrvrolemember / sp_dropsrvrolemember (no ALTER SERVER ROLE ... ADD MEMBER).
     - Uses datetime/GETDATE in sample table (instead of datetime2/SYSDATETIME).

   Run as sysadmin for best coverage.

   ================================================================================================ */

USE [master];
SET NOCOUNT ON;

DECLARE @RunId uniqueidentifier = NEWID();
DECLARE @Tag   sysname = SUBSTRING(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 1, 8);

DECLARE @UnusedLoginCount int = 1 + ABS(CHECKSUM(NEWID())) % 3; -- 1..3
DECLARE @CommonDbCount    int = 1 + ABS(CHECKSUM(NEWID())) % 2; -- 1..2

DECLARE @StrongPwd nvarchar(128) =
    N'W0rkspace!' + @Tag + N'#' + RIGHT(CONVERT(varchar(10), ABS(CHECKSUM(NEWID()))), 4);

DECLARE @sql nvarchar(max);

PRINT '=== WS APPLY 2008 START ===';
PRINT 'RunId=' + CONVERT(varchar(36), @RunId) + ' Tag=' + @Tag;
PRINT 'UnusedLoginCount=' + CONVERT(varchar(12), @UnusedLoginCount) + ' CommonDbCount=' + CONVERT(varchar(12), @CommonDbCount);

--------------------------------------------------------------------------------
-- STEP 1: Discrepancy - ensure built-in SID 0x01 login is named "sa" and ENABLED
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @SaCurrentName sysname;

    SELECT @SaCurrentName = name
    FROM sys.server_principals
    WHERE sid = 0x01 AND type_desc = 'SQL_LOGIN';

    IF @SaCurrentName IS NULL
        RAISERROR('Built-in sa login (SID 0x01) not found.', 16, 1);

    IF @SaCurrentName <> N'sa'
    BEGIN
        IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'sa')
            RAISERROR('Cannot rename SID 0x01 login to sa because name "sa" already exists.', 16, 1);

        SET @sql = N'ALTER LOGIN ' + QUOTENAME(@SaCurrentName) + N' WITH NAME=[sa];';
        EXEC sys.sp_executesql @sql;
    END

    SET @sql = N'ALTER LOGIN [sa] ENABLE;';
    EXEC sys.sp_executesql @sql;

    IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name=N'sa' AND is_disabled=0)
        RAISERROR('Failed to verify: sa enabled.', 16, 1);

    PRINT 'OK: sa discrepancy set (sa enabled, named sa).';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: sa discrepancy step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 2: Discrepancy - unsafe server configs enabled (RECONFIGURE each)
--         If an option doesn't exist or can't be changed, we WARN and continue.
--------------------------------------------------------------------------------
BEGIN TRY
    -- show advanced options
    BEGIN TRY
        EXEC sp_configure 'show advanced options', 1;
        RECONFIGURE;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not enable show advanced options: ' + ERROR_MESSAGE();
    END CATCH;

    -- xp_cmdshell
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = N'xp_cmdshell')
        BEGIN
            EXEC sp_configure 'xp_cmdshell', 1;
            RECONFIGURE;
        END
        ELSE
            PRINT 'WARN: xp_cmdshell option not present on this instance.';
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not enable xp_cmdshell: ' + ERROR_MESSAGE();
    END CATCH;

    -- Ad Hoc Distributed Queries
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = N'Ad Hoc Distributed Queries')
        BEGIN
            EXEC sp_configure 'Ad Hoc Distributed Queries', 1;
            RECONFIGURE;
        END
        ELSE
            PRINT 'WARN: Ad Hoc Distributed Queries option not present on this instance.';
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not enable Ad Hoc Distributed Queries: ' + ERROR_MESSAGE();
    END CATCH;

    -- Database Mail XPs
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = N'Database Mail XPs')
        BEGIN
            EXEC sp_configure 'Database Mail XPs', 1;
            RECONFIGURE;
        END
        ELSE
            PRINT 'WARN: Database Mail XPs option not present on this instance.';
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not enable Database Mail XPs: ' + ERROR_MESSAGE();
    END CATCH;

    -- remote access
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = N'remote access')
        BEGIN
            EXEC sp_configure 'remote access', 1;
            RECONFIGURE;
        END
        ELSE
            PRINT 'WARN: remote access option not present on this instance.';
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not enable remote access: ' + ERROR_MESSAGE();
    END CATCH;

    -- close advanced options (best effort)
    BEGIN TRY
        EXEC sp_configure 'show advanced options', 0;
        RECONFIGURE;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: could not disable show advanced options: ' + ERROR_MESSAGE();
    END CATCH;

    PRINT 'OK/WARN: config step completed (some options may have been skipped).';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: config step wrapper failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 3: Discrepancy - disable login auditing (AuditLevel=0)
--         This is registry-based; if blocked, WARN and continue.
--         Robust capture of xp_instance_regread output.
--------------------------------------------------------------------------------
BEGIN TRY
    BEGIN TRY
        EXEC xp_instance_regwrite
            N'HKEY_LOCAL_MACHINE',
            N'Software\Microsoft\MSSQLServer\MSSQLServer',
            N'AuditLevel',
            REG_DWORD,
            0;
    END TRY
    BEGIN CATCH
        PRINT 'WARN: registry write blocked: ' + ERROR_MESSAGE();
    END CATCH;

    BEGIN TRY
        DECLARE @Reg TABLE (ValueName nvarchar(255) NULL, Data sql_variant NULL);
        INSERT INTO @Reg(ValueName, Data)
        EXEC xp_instance_regread
            N'HKEY_LOCAL_MACHINE',
            N'Software\Microsoft\MSSQLServer\MSSQLServer',
            N'AuditLevel';

        DECLARE @AuditLevel int;
        SELECT TOP(1) @AuditLevel = CONVERT(int, Data) FROM @Reg;

        IF @AuditLevel = 0
            PRINT 'OK: AuditLevel verified as 0 (login auditing disabled).';
        ELSE
            PRINT 'WARN: AuditLevel could not be verified as 0 (value=' + COALESCE(CONVERT(varchar(32), @AuditLevel), 'NULL') + ').';
    END TRY
    BEGIN CATCH
        PRINT 'WARN: registry read/verify blocked: ' + ERROR_MESSAGE();
    END CATCH;
END TRY
BEGIN CATCH
    PRINT 'WARN: registry audit step wrapper failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 4: Discrepancy - stale documentation extended property
--------------------------------------------------------------------------------
BEGIN TRY
    IF EXISTS (SELECT 1 FROM sys.extended_properties WHERE class=0 AND name=N'DocumentationLastReviewed')
        EXEC sp_updateextendedproperty @name=N'DocumentationLastReviewed', @value=N'2023-01-15';
    ELSE
        EXEC sp_addextendedproperty @name=N'DocumentationLastReviewed', @value=N'2023-01-15';

    IF EXISTS (
        SELECT 1 FROM sys.extended_properties
        WHERE class=0 AND name=N'DocumentationLastReviewed' AND CONVERT(nvarchar(100), value)=N'2023-01-15'
    )
        PRINT 'OK: DocumentationLastReviewed set to stale date.';
    ELSE
        RAISERROR('DocumentationLastReviewed not verified.', 16, 1);
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: DocumentationLastReviewed step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 5: Discrepancies - randomized logins/roles/perms (2008-style)
--   - Weak privileged sysadmin (policy off, password=username)
--   - 1..3 unused logins (no roles, no users)
--   - Overprivileged login in multiple roles (securityadmin/serveradmin/bulkadmin if present)
--   - Complex server-level grants
--   - RecentSecurityChange marker login
--------------------------------------------------------------------------------
DECLARE @LoginWeak    sysname = N'WeakPolicyAdmin_' + @Tag;
DECLARE @LoginOver    sysname = N'OverprivilegedUser_' + @Tag;
DECLARE @LoginComplex sysname = N'ComplexSecurityUser_' + @Tag;
DECLARE @LoginRecent  sysname = N'RecentSecurityChange_' + @Tag;

BEGIN TRY
    -- Weak privileged sysadmin
    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@LoginWeak)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@LoginWeak)
                 + N' WITH PASSWORD=''' + REPLACE(CONVERT(nvarchar(256),@LoginWeak),'''','''''')
                 + N''', CHECK_POLICY=OFF, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;

        EXEC sp_addsrvrolemember @loginame=@LoginWeak, @rolename=N'sysadmin';
    END

    -- Unused logins
    DECLARE @i int;
    SET @i = 1;
    WHILE @i <= @UnusedLoginCount
    BEGIN
        DECLARE @Unused sysname;
        SET @Unused = N'UnusedLogin_' + @Tag + N'_' + RIGHT(N'0' + CONVERT(varchar(2),@i),2);

        IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@Unused)
        BEGIN
            SET @sql = N'CREATE LOGIN ' + QUOTENAME(@Unused)
                     + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                     + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
            EXEC sys.sp_executesql @sql;
        END

        SET @i = @i + 1;
    END

    -- Overprivileged login
    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@LoginOver)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@LoginOver)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                 + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;

        EXEC sp_addsrvrolemember @loginame=@LoginOver, @rolename=N'securityadmin';
        EXEC sp_addsrvrolemember @loginame=@LoginOver, @rolename=N'serveradmin';

        -- bulkadmin exists in SQL Server 2008; still guard just in case a hardened build removed it.
        IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'bulkadmin' AND type_desc='SERVER_ROLE')
            EXEC sp_addsrvrolemember @loginame=@LoginOver, @rolename=N'bulkadmin';
        ELSE
            PRINT 'WARN: server role bulkadmin not present; skipping that role.';
    END

    -- Complex perms
    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@LoginComplex)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@LoginComplex)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                 + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'GRANT CONTROL SERVER TO ' + QUOTENAME(@LoginComplex) + N';';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'GRANT ALTER ANY LOGIN TO ' + QUOTENAME(@LoginComplex) + N';';
        EXEC sys.sp_executesql @sql;
    END

    -- Recent marker login
    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@LoginRecent)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@LoginRecent)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                 + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;
    END

    PRINT 'OK: login/role/perm discrepancies created (Tag=' + @Tag + ').';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: login/role/perm step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 6: Discrepancy - certificate created (not backed up)
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @Cert sysname;
    SET @Cert = N'TestCert_' + @Tag;

    IF NOT EXISTS (SELECT 1 FROM sys.certificates WHERE name=@Cert)
    BEGIN
        SET @sql = N'CREATE CERTIFICATE ' + QUOTENAME(@Cert)
                 + N' WITH SUBJECT=''Test cert not backed up (' + @Tag + N')'';';
        EXEC sys.sp_executesql @sql;
    END

    PRINT 'OK: certificate created: ' + @Cert;
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: certificate step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 7: Discrepancy - unreviewed server trigger (fires on CREATE_LOGIN)
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @SrvTrig sysname;
    SET @SrvTrig = N'TR_Unreviewed_Server_' + @Tag;

    IF NOT EXISTS (SELECT 1 FROM sys.server_triggers WHERE name=@SrvTrig)
    BEGIN
        SET @sql = N'CREATE TRIGGER ' + QUOTENAME(@SrvTrig) + N'
                    ON ALL SERVER
                    FOR CREATE_LOGIN
                    AS
                    BEGIN
                        PRINT ''Unreviewed server trigger fired (test).''; 
                    END;';
        EXEC sys.sp_executesql @sql;
    END

    PRINT 'OK: server trigger created: ' + @SrvTrig;
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: server trigger step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 8: Discrepancies - linked servers (metadata-only) and insecure mapping
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @LS1 sysname;
    DECLARE @LS2 sysname;
    DECLARE @RmtPwd nvarchar(64);

    SET @LS1 = N'UNAPPROVED_LINK_' + @Tag;
    SET @LS2 = N'INSECURE_LINK_' + @Tag;
    SET @RmtPwd = N'sa_password_' + @Tag;

    IF NOT EXISTS (SELECT 1 FROM sys.servers WHERE name=@LS1)
    BEGIN
        EXEC sp_addlinkedserver @server=@LS1, @srvproduct=N'SQL Server';
        EXEC sp_addlinkedsrvlogin @rmtsrvname=@LS1, @useself=N'true';
    END

    IF NOT EXISTS (SELECT 1 FROM sys.servers WHERE name=@LS2)
    BEGIN
        EXEC sp_addlinkedserver @server=@LS2, @srvproduct=N'SQL Server';
        EXEC sp_addlinkedsrvlogin
            @rmtsrvname=@LS2, @useself=N'false', @locallogin=NULL, @rmtuser=N'sa', @rmtpassword=@RmtPwd;
    END

    PRINT 'OK: linked server discrepancies created: ' + @LS1 + ' and ' + @LS2;
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: linked server step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 9: Discrepancies - randomized test DBs + DB-level users/perms + DB trigger
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @LegacyDb sysname;
    DECLARE @TargetDb sysname;

    DECLARE @GrantLogin sysname;
    DECLARE @GrantUser  sysname;

    DECLARE @ExcessLogin sysname;
    DECLARE @ExcessUser  sysname;

    DECLARE @OrphanUser sysname;
    DECLARE @DbTrig     sysname;

    SET @LegacyDb  = N'LegacyTestDB_' + @Tag;
    SET @TargetDb  = N'TestDB_' + @Tag;
    SET @GrantLogin= N'GrantOptionLogin_' + @Tag;
    SET @GrantUser = N'GrantOptionUser_' + @Tag;
    SET @ExcessLogin= N'ExcessivePermLogin_' + @Tag;
    SET @ExcessUser = N'ExcessivePermUser_' + @Tag;
    SET @OrphanUser = N'OrphanUser_' + @Tag;
    SET @DbTrig     = N'TR_Unreviewed_DB_' + @Tag;

    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@GrantLogin)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@GrantLogin)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                 + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;
    END

    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@ExcessLogin)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@ExcessLogin)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                 + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;
    END

    IF DB_ID(@LegacyDb) IS NULL
    BEGIN
        SET @sql = N'CREATE DATABASE ' + QUOTENAME(@LegacyDb) + N';';
        EXEC sys.sp_executesql @sql;
    END

    IF DB_ID(@TargetDb) IS NULL
    BEGIN
        SET @sql = N'CREATE DATABASE ' + QUOTENAME(@TargetDb) + N';';
        EXEC sys.sp_executesql @sql;
    END

    DECLARE @n int;
    SET @n = 1;
    WHILE @n <= @CommonDbCount
    BEGIN
        DECLARE @CommonDb sysname;
        SET @CommonDb = CASE WHEN @n=1 THEN N'AdventureWorks_' + @Tag ELSE N'Northwind_' + @Tag END;

        IF DB_ID(@CommonDb) IS NULL
        BEGIN
            SET @sql = N'CREATE DATABASE ' + QUOTENAME(@CommonDb) + N';';
            EXEC sys.sp_executesql @sql;
        END

        SET @n = @n + 1;
    END

    -- DB-level work (2008-safe types)
    SET @sql = N'
    USE ' + QUOTENAME(@TargetDb) + N';

    IF OBJECT_ID(N''dbo.SampleData'', N''U'') IS NULL
    BEGIN
        CREATE TABLE dbo.SampleData
        (
            Id int IDENTITY(1,1) NOT NULL CONSTRAINT PK_SampleData PRIMARY KEY,
            CreatedAt datetime NOT NULL CONSTRAINT DF_SampleData_CreatedAt DEFAULT (GETDATE()),
            Secret nvarchar(200) NOT NULL
        );
        INSERT dbo.SampleData(Secret) VALUES (N''alpha''),(N''beta''),(N''gamma'');
    END

    BEGIN TRY GRANT CONNECT TO guest; END TRY BEGIN CATCH END CATCH;

    IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N''' + REPLACE(@OrphanUser,'''','''''') + N''')
        CREATE USER ' + QUOTENAME(@OrphanUser) + N' WITHOUT LOGIN;

    IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N''' + REPLACE(@GrantUser,'''','''''') + N''')
        CREATE USER ' + QUOTENAME(@GrantUser) + N' FOR LOGIN ' + QUOTENAME(@GrantLogin) + N';

    GRANT SELECT ON dbo.SampleData TO ' + QUOTENAME(@GrantUser) + N' WITH GRANT OPTION;

    IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N''' + REPLACE(@ExcessUser,'''','''''') + N''')
        CREATE USER ' + QUOTENAME(@ExcessUser) + N' FOR LOGIN ' + QUOTENAME(@ExcessLogin) + N';

    EXEC sp_addrolemember N''db_owner'', N''' + REPLACE(@ExcessUser,'''','''''') + N''';

    GRANT EXECUTE ON SCHEMA::dbo TO ' + QUOTENAME(@ExcessUser) + N';
    GRANT ALTER ANY SCHEMA TO ' + QUOTENAME(@ExcessUser) + N';

    IF NOT EXISTS (SELECT 1 FROM sys.triggers WHERE name = N''' + REPLACE(@DbTrig,'''','''''') + N''')
    BEGIN
        EXEC (N''CREATE TRIGGER ' + QUOTENAME(@DbTrig) + N'
              ON DATABASE
              FOR CREATE_TABLE
              AS
              BEGIN
                  PRINT ''''Unreviewed DB trigger fired (test).'''';
              END;'');
    END
    ';
    EXEC sys.sp_executesql @sql;

    PRINT 'OK: DB/user/perm discrepancies created in ' + @TargetDb + ' (and extra DBs created).';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: DB/user/perm step failed: ' + ERROR_MESSAGE();
END CATCH;

PRINT '=== WS APPLY 2008 END ===';
