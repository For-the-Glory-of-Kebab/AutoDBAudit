/* ================================================================================================
   Workspace Discrepancy Simulator - APPLY (SQL Server 2019+)
   ------------------------------------------------------------------------------------------------
   Reliability-first version (NO result sets, NO server-side log tables, PRINT-only).
   Fixes previous compile error cause: never uses EXEC(<expression>); always builds dynamic SQL
   into @sql then EXEC sys.sp_executesql @sql.

   Run as sysadmin.

   ================================================================================================ */

USE [master];
SET NOCOUNT ON;

DECLARE @RunId uniqueidentifier = NEWID();
DECLARE @Tag   sysname = SUBSTRING(REPLACE(CONVERT(varchar(36), NEWID()), '-', ''), 1, 8);

DECLARE @UnusedLoginCount int = 1 + ABS(CHECKSUM(NEWID())) % 3; -- 1..3
DECLARE @CommonDbCount    int = 1 + ABS(CHECKSUM(NEWID())) % 2; -- 1..2

DECLARE @StrongPwd nvarchar(128) = N'W0rkspace!' + @Tag + N'#' + RIGHT(CONVERT(varchar(10), ABS(CHECKSUM(NEWID()))), 4);
DECLARE @sql nvarchar(max);

PRINT '=== WS APPLY 2019+ START ===';
PRINT 'RunId=' + CONVERT(varchar(36), @RunId) + ' Tag=' + @Tag;
PRINT 'UnusedLoginCount=' + CONVERT(varchar(12), @UnusedLoginCount) + ' CommonDbCount=' + CONVERT(varchar(12), @CommonDbCount);

--------------------------------------------------------------------------------
-- STEP 1: Discrepancy - built-in SID 0x01 login must be "sa" and enabled
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @SaCurrentName sysname;
    SELECT @SaCurrentName = name
    FROM sys.server_principals
    WHERE sid = 0x01 AND type_desc = 'SQL_LOGIN';

    IF @SaCurrentName IS NULL
        THROW 51000, 'Built-in sa login (SID 0x01) not found.', 1;

    IF @SaCurrentName <> N'sa'
    BEGIN
        IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'sa')
            THROW 51001, 'Cannot rename SID 0x01 login to sa because name "sa" already exists.', 1;

        SET @sql = N'ALTER LOGIN ' + QUOTENAME(@SaCurrentName) + N' WITH NAME=[sa];';
        EXEC sys.sp_executesql @sql;
    END

    SET @sql = N'ALTER LOGIN [sa] ENABLE;';
    EXEC sys.sp_executesql @sql;

    IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name=N'sa' AND is_disabled=0)
        THROW 51002, 'Failed to verify: sa enabled.', 1;

    PRINT 'OK: sa discrepancy set (sa enabled, named sa).';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: sa discrepancy step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 2: Discrepancy - unsafe server configs enabled (and reconfigured)
--------------------------------------------------------------------------------
BEGIN TRY
    EXEC sp_configure 'show advanced options', 1;
    RECONFIGURE;

    EXEC sp_configure 'xp_cmdshell', 1;
    RECONFIGURE;

    EXEC sp_configure 'Ad Hoc Distributed Queries', 1;
    RECONFIGURE;

    EXEC sp_configure 'Database Mail XPs', 1;
    RECONFIGURE;

    EXEC sp_configure 'remote access', 1;
    RECONFIGURE;

    IF EXISTS (
        SELECT 1 FROM sys.configurations
        WHERE name IN (N'xp_cmdshell',N'Ad Hoc Distributed Queries',N'Database Mail XPs',N'remote access')
          AND value_in_use <> 1
    )
        THROW 51003, 'One or more configurations did not take effect (value_in_use <> 1).', 1;

    EXEC sp_configure 'show advanced options', 0;
    RECONFIGURE;

    PRINT 'OK: unsafe configs enabled and verified.';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: config step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 3: Discrepancy - disable login auditing (AuditLevel=0) (WARN-only if blocked)
--------------------------------------------------------------------------------
BEGIN TRY
    EXEC xp_instance_regwrite
        N'HKEY_LOCAL_MACHINE',
        N'Software\Microsoft\MSSQLServer\MSSQLServer',
        N'AuditLevel',
        REG_DWORD,
        0;

    DECLARE @Reg TABLE (Value sql_variant NULL);
    INSERT INTO @Reg(Value)
    EXEC xp_instance_regread
        N'HKEY_LOCAL_MACHINE',
        N'Software\Microsoft\MSSQLServer\MSSQLServer',
        N'AuditLevel';

    DECLARE @AuditLevel int = TRY_CONVERT(int, (SELECT TOP(1) Value FROM @Reg));

    IF @AuditLevel <> 0
        THROW 51004, 'AuditLevel verification failed (not 0).', 1;

    PRINT 'OK: AuditLevel set to 0 (login auditing disabled).';
END TRY
BEGIN CATCH
    PRINT 'WARN: registry audit setting not applied/verified (continuing): ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 4: Discrepancy - stale documentation extended property
--------------------------------------------------------------------------------
BEGIN TRY
    IF EXISTS (SELECT 1 FROM sys.extended_properties WHERE class=0 AND name=N'DocumentationLastReviewed')
        EXEC sp_updateextendedproperty @name=N'DocumentationLastReviewed', @value=N'2023-01-15';
    ELSE
        EXEC sp_addextendedproperty @name=N'DocumentationLastReviewed', @value=N'2023-01-15';

    IF NOT EXISTS (
        SELECT 1 FROM sys.extended_properties
        WHERE class=0 AND name=N'DocumentationLastReviewed' AND CONVERT(nvarchar(100), value)=N'2023-01-15'
    )
        THROW 51005, 'DocumentationLastReviewed not verified.', 1;

    PRINT 'OK: DocumentationLastReviewed set to stale date.';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: DocumentationLastReviewed step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 5: Discrepancies - randomized logins/roles/perms
--------------------------------------------------------------------------------
DECLARE @LoginWeak    sysname = N'WeakPolicyAdmin_' + @Tag;
DECLARE @LoginOver    sysname = N'OverprivilegedUser_' + @Tag;
DECLARE @LoginComplex sysname = N'ComplexSecurityUser_' + @Tag;
DECLARE @LoginRecent  sysname = N'RecentSecurityChange_' + @Tag;

BEGIN TRY
    -- Weak privileged sysadmin (policy off, password=username)
    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@LoginWeak)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@LoginWeak)
                 + N' WITH PASSWORD=''' + REPLACE(CONVERT(nvarchar(256),@LoginWeak),'''','''''')
                 + N''', CHECK_POLICY=OFF, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'ALTER SERVER ROLE [sysadmin] ADD MEMBER ' + QUOTENAME(@LoginWeak) + N';';
        EXEC sys.sp_executesql @sql;
    END

    -- Unused logins
    DECLARE @i int = 1;
    WHILE @i <= @UnusedLoginCount
    BEGIN
        DECLARE @Unused sysname = N'UnusedLogin_' + @Tag + N'_' + RIGHT(N'0' + CONVERT(varchar(2),@i),2);
        IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@Unused)
        BEGIN
            SET @sql = N'CREATE LOGIN ' + QUOTENAME(@Unused)
                     + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                     + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
            EXEC sys.sp_executesql @sql;
        END
        SET @i += 1;
    END

    -- Overprivileged login in multiple roles
    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@LoginOver)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@LoginOver)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''')
                 + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'ALTER SERVER ROLE [securityadmin] ADD MEMBER ' + QUOTENAME(@LoginOver) + N';';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'ALTER SERVER ROLE [serveradmin] ADD MEMBER ' + QUOTENAME(@LoginOver) + N';';
        EXEC sys.sp_executesql @sql;

        SET @sql = N'ALTER SERVER ROLE [bulkadmin] ADD MEMBER ' + QUOTENAME(@LoginOver) + N';';
        EXEC sys.sp_executesql @sql;
    END

    -- Complex server-level grants
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

    -- Recent login marker
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
    DECLARE @Cert sysname = N'TestCert_' + @Tag;
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
    DECLARE @SrvTrig sysname = N'TR_Unreviewed_Server_' + @Tag;
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
    DECLARE @LS1 sysname = N'UNAPPROVED_LINK_' + @Tag;
    DECLARE @LS2 sysname = N'INSECURE_LINK_' + @Tag;

    IF NOT EXISTS (SELECT 1 FROM sys.servers WHERE name=@LS1)
    BEGIN
        EXEC sp_addlinkedserver @server=@LS1, @srvproduct=N'SQL Server';
        EXEC sp_addlinkedsrvlogin @rmtsrvname=@LS1, @useself=N'true';
    END

    IF NOT EXISTS (SELECT 1 FROM sys.servers WHERE name=@LS2)
    BEGIN
        DECLARE @RmtPwd nvarchar(64) = N'sa_password_' + @Tag;
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
    DECLARE @LegacyDb sysname = N'LegacyTestDB_' + @Tag;
    DECLARE @TargetDb sysname = N'TestDB_' + @Tag;

    DECLARE @GrantLogin sysname = N'GrantOptionLogin_' + @Tag;
    DECLARE @GrantUser  sysname = N'GrantOptionUser_' + @Tag;

    DECLARE @ExcessLogin sysname = N'ExcessivePermLogin_' + @Tag;
    DECLARE @ExcessUser  sysname = N'ExcessivePermUser_' + @Tag;

    DECLARE @OrphanUser  sysname = N'OrphanUser_' + @Tag;
    DECLARE @DbTrig      sysname = N'TR_Unreviewed_DB_' + @Tag;

    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@GrantLogin)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@GrantLogin)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''') + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
        EXEC sys.sp_executesql @sql;
    END

    IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name=@ExcessLogin)
    BEGIN
        SET @sql = N'CREATE LOGIN ' + QUOTENAME(@ExcessLogin)
                 + N' WITH PASSWORD=''' + REPLACE(@StrongPwd,'''','''''') + N''', CHECK_POLICY=ON, CHECK_EXPIRATION=OFF;';
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

    DECLARE @n int = 1;
    WHILE @n <= @CommonDbCount
    BEGIN
        DECLARE @CommonDb sysname = CASE WHEN @n=1 THEN N'AdventureWorks_' + @Tag ELSE N'Northwind_' + @Tag END;
        IF DB_ID(@CommonDb) IS NULL
        BEGIN
            SET @sql = N'CREATE DATABASE ' + QUOTENAME(@CommonDb) + N';';
            EXEC sys.sp_executesql @sql;
        END
        SET @n += 1;
    END

    -- DB-level work
    SET @sql = N'
    USE ' + QUOTENAME(@TargetDb) + N';

    IF OBJECT_ID(N''dbo.SampleData'', N''U'') IS NULL
    BEGIN
        CREATE TABLE dbo.SampleData
        (
            Id int IDENTITY(1,1) NOT NULL CONSTRAINT PK_SampleData PRIMARY KEY,
            CreatedAt datetime2(0) NOT NULL CONSTRAINT DF_SampleData_CreatedAt DEFAULT (SYSDATETIME()),
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

PRINT '=== WS APPLY 2019+ END ===';
