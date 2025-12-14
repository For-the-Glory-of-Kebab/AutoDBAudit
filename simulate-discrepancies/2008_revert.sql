/* ================================================================================================
   Workspace Discrepancy Simulator - REVERT (SQL Server 2008)
   ------------------------------------------------------------------------------------------------
   Goal: Remove EVERYTHING created by WS_2008_APPLY_FINAL_v2 so you can:
         APPLY => test audit/fixes => REVERT => APPLY => repeat

   What this script cleans:
     - Databases:        LegacyTestDB_*, TestDB_*, AdventureWorks_*, Northwind_*
     - Linked servers:   UNAPPROVED_LINK_*, INSECURE_LINK_*
     - Server triggers:  TR_Unreviewed_Server_*
     - Certificates:     TestCert_*
     - Logins:           WeakPolicyAdmin_*, OverprivilegedUser_*, ComplexSecurityUser_*,
                        RecentSecurityChange_*, UnusedLogin_*,
                        GrantOptionLogin_*, ExcessivePermLogin_*

   SA restore requirement:
     - If the built-in login (SID 0x01) was renamed to "$@" by your audit fix, this script renames it
       back to "sa" AND enables it.
     - Also, if the SID 0x01 login is disabled for any reason, it is enabled.

   Reliability rules:
     - PRINT-only messages, no result sets required, no server-side log tables.
     - Each major step wrapped in TRY/CATCH; failures are PRINTed and the script continues.

   SQL Server 2008 compatibility notes:
     - Uses RAISERROR (no THROW).
     - Uses sys.sp_executesql for dynamic SQL.
     - Uses SQL Server 2008 catalog views (sys.server_triggers etc. exist).
     - Uses CURSOR LOCAL FAST_FORWARD patterns that are supported.

   Run as sysadmin.

   ================================================================================================ */

USE [master];
SET NOCOUNT ON;

DECLARE @sql nvarchar(max);
DECLARE @name sysname;

PRINT '=== WS REVERT 2008 START ===';
PRINT 'Host=' + @@SERVERNAME + '  Time=' + CONVERT(varchar(19), GETDATE(), 120);

--------------------------------------------------------------------------------
-- STEP 0: Restore built-in sa (SID 0x01): rename to sa if needed, and ENABLE
--------------------------------------------------------------------------------
BEGIN TRY
    DECLARE @Sid01Name sysname;

    SELECT @Sid01Name = sp.name
    FROM sys.server_principals sp
    WHERE sp.sid = 0x01 AND sp.type_desc = 'SQL_LOGIN';

    IF @Sid01Name IS NULL
    BEGIN
        PRINT 'WARN: Built-in login SID 0x01 not found; cannot restore sa.';
    END
    ELSE
    BEGIN
        IF @Sid01Name <> N'sa'
        BEGIN
            IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'sa')
            BEGIN
                PRINT 'WARN: Cannot rename SID 0x01 login to sa because a login named sa already exists.';
                PRINT '      Current SID 0x01 name = ' + @Sid01Name;
            END
            ELSE
            BEGIN
                SET @sql = N'ALTER LOGIN ' + QUOTENAME(@Sid01Name) + N' WITH NAME = [sa];';
                EXEC sys.sp_executesql @sql;
                PRINT 'OK: Renamed SID 0x01 login from ' + @Sid01Name + ' to sa.';
            END
        END

        SET @sql = N'ALTER LOGIN [sa] ENABLE;';
        EXEC sys.sp_executesql @sql;

        IF EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = N'sa' AND is_disabled = 0)
            PRINT 'OK: sa is enabled.';
        ELSE
            PRINT 'WARN: sa enable could not be verified.';
    END
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: sa restore step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 1: Drop WS-created databases
--------------------------------------------------------------------------------
BEGIN TRY
    PRINT '--- Dropping WS databases (if present) ---';

    DECLARE db_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT d.name
        FROM sys.databases d
        WHERE d.database_id > 4
          AND (
                d.name LIKE N'LegacyTestDB[_]%' ESCAPE N'\'
             OR d.name LIKE N'TestDB[_]%'     ESCAPE N'\'
             OR d.name LIKE N'AdventureWorks[_]%' ESCAPE N'\'
             OR d.name LIKE N'Northwind[_]%'  ESCAPE N'\'
          );

    OPEN db_cursor;
    FETCH NEXT FROM db_cursor INTO @name;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            PRINT 'Dropping database: ' + @name;

            SET @sql = N'ALTER DATABASE ' + QUOTENAME(@name) + N' SET SINGLE_USER WITH ROLLBACK IMMEDIATE;';
            EXEC sys.sp_executesql @sql;

            SET @sql = N'DROP DATABASE ' + QUOTENAME(@name) + N';';
            EXEC sys.sp_executesql @sql;

            PRINT 'OK: Dropped database ' + @name;
        END TRY
        BEGIN CATCH
            PRINT 'WARN/ERR: Failed to drop database ' + @name + ': ' + ERROR_MESSAGE();

            -- Best-effort internal cleanup (users + DB trigger) if DB can't be dropped
            BEGIN TRY
                SET @sql = N'
                USE ' + QUOTENAME(@name) + N';
                DECLARE @u sysname;
                DECLARE @s nvarchar(max);

                -- Drop WS DB triggers
                DECLARE tr CURSOR LOCAL FAST_FORWARD FOR
                    SELECT name FROM sys.triggers WHERE parent_class_desc = ''DATABASE'' AND name LIKE N''TR_Unreviewed_DB[_]%'';
                OPEN tr;
                FETCH NEXT FROM tr INTO @u;
                WHILE @@FETCH_STATUS = 0
                BEGIN
                    SET @s = N''DROP TRIGGER '' + QUOTENAME(@u) + N'';'';
                    BEGIN TRY EXEC sys.sp_executesql @s; END TRY BEGIN CATCH END CATCH;
                    FETCH NEXT FROM tr INTO @u;
                END
                CLOSE tr; DEALLOCATE tr;

                -- Drop WS users
                DECLARE us CURSOR LOCAL FAST_FORWARD FOR
                    SELECT name FROM sys.database_principals
                    WHERE type_desc IN (''SQL_USER'',''WINDOWS_USER'')
                      AND (
                           name LIKE N''OrphanUser[_]%''
                        OR name LIKE N''GrantOptionUser[_]%''
                        OR name LIKE N''ExcessivePermUser[_]%''
                      );
                OPEN us;
                FETCH NEXT FROM us INTO @u;
                WHILE @@FETCH_STATUS = 0
                BEGIN
                    SET @s = N''DROP USER '' + QUOTENAME(@u) + N'';'';
                    BEGIN TRY EXEC sys.sp_executesql @s; END TRY BEGIN CATCH END CATCH;
                    FETCH NEXT FROM us INTO @u;
                END
                CLOSE us; DEALLOCATE us;
                ';
                EXEC sys.sp_executesql @sql;
                PRINT 'OK: Best-effort cleanup inside ' + @name + ' completed.';
            END TRY
            BEGIN CATCH
                PRINT 'WARN: Best-effort internal cleanup failed for ' + @name + ': ' + ERROR_MESSAGE();
            END CATCH;
        END CATCH;

        FETCH NEXT FROM db_cursor INTO @name;
    END

    CLOSE db_cursor;
    DEALLOCATE db_cursor;

    PRINT '--- Database cleanup done ---';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: Database cleanup step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 2: Drop WS-created server triggers
--------------------------------------------------------------------------------
BEGIN TRY
    PRINT '--- Dropping WS server triggers ---';

    DECLARE trg_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT name FROM sys.server_triggers
        WHERE name LIKE N'TR_Unreviewed_Server[_]%' ESCAPE N'\';

    OPEN trg_cursor;
    FETCH NEXT FROM trg_cursor INTO @name;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            PRINT 'Dropping server trigger: ' + @name;
            SET @sql = N'DROP TRIGGER ' + QUOTENAME(@name) + N' ON ALL SERVER;';
            EXEC sys.sp_executesql @sql;
            PRINT 'OK: Dropped server trigger ' + @name;
        END TRY
        BEGIN CATCH
            PRINT 'WARN/ERR: Failed to drop server trigger ' + @name + ': ' + ERROR_MESSAGE();
        END CATCH;

        FETCH NEXT FROM trg_cursor INTO @name;
    END

    CLOSE trg_cursor;
    DEALLOCATE trg_cursor;

    PRINT '--- Server trigger cleanup done ---';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: Server trigger cleanup step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 3: Drop WS-created linked servers
--------------------------------------------------------------------------------
BEGIN TRY
    PRINT '--- Dropping WS linked servers ---';

    DECLARE ls_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT name FROM sys.servers
        WHERE is_linked = 1
          AND (
                name LIKE N'UNAPPROVED_LINK[_]%' ESCAPE N'\'
             OR name LIKE N'INSECURE_LINK[_]%'   ESCAPE N'\'
          );

    OPEN ls_cursor;
    FETCH NEXT FROM ls_cursor INTO @name;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            PRINT 'Dropping linked server: ' + @name;
            EXEC master.dbo.sp_dropserver @server=@name, @droplogins='droplogins';
            PRINT 'OK: Dropped linked server ' + @name;
        END TRY
        BEGIN CATCH
            PRINT 'WARN/ERR: Failed to drop linked server ' + @name + ': ' + ERROR_MESSAGE();
        END CATCH;

        FETCH NEXT FROM ls_cursor INTO @name;
    END

    CLOSE ls_cursor;
    DEALLOCATE ls_cursor;

    PRINT '--- Linked server cleanup done ---';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: Linked server cleanup step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 4: Drop WS-created certificates
--------------------------------------------------------------------------------
BEGIN TRY
    PRINT '--- Dropping WS certificates ---';

    DECLARE cert_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT name FROM sys.certificates
        WHERE name LIKE N'TestCert[_]%' ESCAPE N'\';

    OPEN cert_cursor;
    FETCH NEXT FROM cert_cursor INTO @name;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            PRINT 'Dropping certificate: ' + @name;
            SET @sql = N'DROP CERTIFICATE ' + QUOTENAME(@name) + N';';
            EXEC sys.sp_executesql @sql;
            PRINT 'OK: Dropped certificate ' + @name;
        END TRY
        BEGIN CATCH
            PRINT 'WARN/ERR: Failed to drop certificate ' + @name + ': ' + ERROR_MESSAGE();
        END CATCH;

        FETCH NEXT FROM cert_cursor INTO @name;
    END

    CLOSE cert_cursor;
    DEALLOCATE cert_cursor;

    PRINT '--- Certificate cleanup done ---';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: Certificate cleanup step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 5: Drop WS-created logins (created by APPLY)
--         We intentionally do NOT touch 'sa' beyond rename/enable already done.
--------------------------------------------------------------------------------
BEGIN TRY
    PRINT '--- Dropping WS logins ---';

    DECLARE login_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT sp.name
        FROM sys.server_principals sp
        WHERE sp.type_desc = 'SQL_LOGIN'
          AND sp.name NOT IN (N'sa')
          AND (
                sp.name LIKE N'WeakPolicyAdmin[_]%' ESCAPE N'\'
             OR sp.name LIKE N'OverprivilegedUser[_]%' ESCAPE N'\'
             OR sp.name LIKE N'ComplexSecurityUser[_]%' ESCAPE N'\'
             OR sp.name LIKE N'RecentSecurityChange[_]%' ESCAPE N'\'
             OR sp.name LIKE N'UnusedLogin[_]%' ESCAPE N'\'
             OR sp.name LIKE N'GrantOptionLogin[_]%' ESCAPE N'\'
             OR sp.name LIKE N'ExcessivePermLogin[_]%' ESCAPE N'\'
          );

    OPEN login_cursor;
    FETCH NEXT FROM login_cursor INTO @name;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            PRINT 'Dropping login: ' + @name;
            SET @sql = N'DROP LOGIN ' + QUOTENAME(@name) + N';';
            EXEC sys.sp_executesql @sql;
            PRINT 'OK: Dropped login ' + @name;
        END TRY
        BEGIN CATCH
            PRINT 'WARN/ERR: Failed to drop login ' + @name + ': ' + ERROR_MESSAGE();
        END CATCH;

        FETCH NEXT FROM login_cursor INTO @name;
    END

    CLOSE login_cursor;
    DEALLOCATE login_cursor;

    PRINT '--- Login cleanup done ---';
END TRY
BEGIN CATCH
    PRINT 'WARN/ERR: Login cleanup step failed: ' + ERROR_MESSAGE();
END CATCH;

--------------------------------------------------------------------------------
-- STEP 6: Best-effort: reset advanced options visibility (optional)
--------------------------------------------------------------------------------
BEGIN TRY
    EXEC sp_configure 'show advanced options', 0;
    RECONFIGURE;
END TRY
BEGIN CATCH
    -- ignore
END CATCH;

PRINT '=== WS REVERT 2008 END ===';
