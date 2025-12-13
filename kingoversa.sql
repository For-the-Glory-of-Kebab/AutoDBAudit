/*===============================================================
    Create login [king] and grant sysadmin
===============================================================*/
USE [master];
GO

DECLARE @passwd NVARCHAR(128) = N'Kavand24'; -- TODO: change this

IF NOT EXISTS (
    SELECT 1
    FROM sys.server_principals
    WHERE name = N'king'
)
BEGIN
    CREATE LOGIN [king]
        WITH PASSWORD       = 'Kavand24',
             CHECK_POLICY   = ON,
             DEFAULT_DATABASE = [master];
END;
GO

-- SQL Server 2012+:
IF EXISTS (
    SELECT 1
    FROM sys.server_principals
    WHERE name = N'king'
)
AND EXISTS (
    SELECT 1
    FROM sys.server_principals
    WHERE name = N'sysadmin'
)
AND NOT EXISTS (
    SELECT 1
    FROM sys.server_role_members rm
    JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
    JOIN sys.server_principals m ON rm.member_principal_id = m.principal_id
    WHERE r.name = N'sysadmin'
      AND m.name = N'king'
)
BEGIN
    BEGIN TRY
        ALTER SERVER ROLE [sysadmin] ADD MEMBER [king]; -- 2012+
    END TRY
    BEGIN CATCH
        -- SQL Server 2008 / fallback:
        IF ERROR_NUMBER() IN (15151, 15530, 15517, 15405, 15410) -- role syntax errors etc.
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM sys.syslogins sl
                JOIN sys.sysmembers sm ON sl.sid = sm.memberuid
                JOIN sys.sysusers su ON sm.groupuid = su.uid
                WHERE sl.name = N'king'
                  AND su.name = N'sysadmin'
            )
            BEGIN
                EXEC sp_addsrvrolemember
                    @loginame = N'king',
                    @rolename = N'sysadmin';
            END;
        END;
    END CATCH;
END;
GO


/*===============================================================
    Create [king] as a user in all databases where [sa] has a user
===============================================================*/
DECLARE @sql NVARCHAR(MAX) = N'';

SELECT @sql = @sql + '
USE ' + QUOTENAME(d.name) + ';
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N''sa'')
    AND NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N''king'')
BEGIN
    CREATE USER [king] FOR LOGIN [king];
END;
'
FROM sys.databases AS d
WHERE d.state_desc = 'ONLINE'
  -- include system DBs if you want explicit users there too:
  -- AND d.database_id > 4
  AND d.name NOT IN ('tempdb'); -- no point in tempdb

PRINT @sql;
EXEC sp_executesql @sql;
GO


/*===============================================================
    Transfer database ownership from [sa] to [king]
    (SQL Server 2008-compatible using sysdatabases)
===============================================================*/
SET NOCOUNT ON;

DECLARE @sql2 NVARCHAR(MAX) = N'';

SELECT @sql2 = @sql2 + '
IF (SELECT SUSER_SNAME(sd.sid)
    FROM master.dbo.sysdatabases AS sd
    WHERE sd.name = N''' + d.name + ''') = N''sa''
BEGIN
    PRINT ''Changing owner of ' + d.name + ' from [sa] to [king]'';
    ALTER AUTHORIZATION ON DATABASE::' + QUOTENAME(d.name) + ' TO [king];
END;
'
FROM master.dbo.sysdatabases AS d
WHERE d.name NOT IN ('tempdb'); -- tempdb owner cannot be changed

PRINT @sql2;
EXEC sp_executesql @sql2;
GO


/*===============================================================
    Transfer schema ownership from [sa] to [king] (per database)
    Run this in each db where you want to move schema ownership.
    Below: do it for all online databases (except tempdb).
===============================================================*/
DECLARE @db     SYSNAME;
DECLARE @cmd    NVARCHAR(MAX);

DECLARE db_cursor CURSOR FAST_FORWARD FOR
    SELECT name
    FROM sys.databases
    WHERE state_desc = 'ONLINE'
      AND name NOT IN ('tempdb');  -- adjust if you want to skip others

OPEN db_cursor;

FETCH NEXT FROM db_cursor INTO @db;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @cmd = N'
USE ' + QUOTENAME(@db) + ';

DECLARE @sql NVARCHAR(MAX) = N''''; 

;WITH sa_schemas AS (
    SELECT
        s.name AS schema_name,
        USER_NAME(s.principal_id) AS owner_name
    FROM sys.schemas AS s
    WHERE USER_NAME(s.principal_id) = N''sa''
)
SELECT @sql = @sql + ''
ALTER AUTHORIZATION ON SCHEMA::'' + QUOTENAME(schema_name) + '' TO [king];
''
FROM sa_schemas;

IF LEN(@sql) > 0
BEGIN
    PRINT ''Transferring schema ownership from [sa] to [king] in database ' + @db + ''';
    PRINT @sql;
    EXEC sp_executesql @sql;
END;
';

    PRINT '--- Processing database: ' + @db;
    EXEC sp_executesql @cmd;

    FETCH NEXT FROM db_cursor INTO @db;
END;

CLOSE db_cursor;
DEALLOCATE db_cursor;
GO


/*===============================================================
    Optional: Template to transfer explicit database permissions
    from [sa] to [king] inside one database.
    Uncomment and run per DB if you really need it.
===============================================================*/
-- USE [SomeDatabase];
-- GO
-- DECLARE @permSql NVARCHAR(MAX) = N'';
--
-- SELECT @permSql = @permSql +
--     CASE dp.state
--         WHEN 'G' THEN 'GRANT '
--         WHEN 'D' THEN 'DENY '
--         WHEN 'R' THEN 'REVOKE '
--         ELSE ''
--     END +
--     dp.permission_name + ' ON ' +
--     CASE
--         WHEN dp.major_id = 0 THEN 'DATABASE::[' + DB_NAME() + ']'
--         ELSE
--             CASE o.type
--                 WHEN 'OBJECT' THEN QUOTENAME(OBJECT_SCHEMA_NAME(dp.major_id)) + '.' + QUOTENAME(OBJECT_NAME(dp.major_id))
--                 ELSE 'OBJECT::' + QUOTENAME(OBJECT_SCHEMA_NAME(dp.major_id)) + '.' + QUOTENAME(OBJECT_NAME(dp.major_id))
--             END
--     END +
--     ' TO [king];' + CHAR(13) + CHAR(10)
-- FROM sys.database_permissions AS dp
-- JOIN sys.database_principals AS p
--     ON dp.grantee_principal_id = p.principal_id
-- LEFT JOIN sys.objects AS o
--     ON dp.major_id = o.object_id
-- WHERE p.name = N'sa';
--
-- PRINT @permSql;
-- -- EXEC sp_executesql @permSql; -- only if you're sure