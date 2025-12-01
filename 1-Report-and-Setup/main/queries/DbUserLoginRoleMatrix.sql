SET NOCOUNT ON;
DECLARE @coll sysname = N'SQL_Latin1_General_CP1_CI_AS';
IF OBJECT_ID('tempdb..#DbRoleMatrix') IS NOT NULL DROP TABLE #DbRoleMatrix;
CREATE TABLE #DbRoleMatrix(
    [Database] sysname NULL,
    UserName sysname NULL,
    LoginName sysname NULL,
    db_owner bit NULL,
    db_datareader bit NULL,
    db_datawriter bit NULL,
    db_ddladmin bit NULL,
    db_securityadmin bit NULL,
    db_backupoperator bit NULL,
    db_accessadmin bit NULL,
    db_denydatareader bit NULL,
    db_denydatawriter bit NULL
);
DECLARE @db sysname, @sql nvarchar(max), @dbLit nvarchar(258), @dbStr nvarchar(258);
DECLARE c CURSOR LOCAL FAST_FORWARD FOR SELECT name FROM sys.databases WHERE database_id>4 AND state_desc='ONLINE';
OPEN c; FETCH NEXT FROM c INTO @db;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @dbLit = QUOTENAME(@db,'"'); -- "DbName"
    -- Build a safe single-quoted string literal 'DbName' (QUOTENAME cannot use single quote this way)
    SET @dbStr = N'''' + REPLACE(@db,'''','''''') + N'''';
    SET @sql = N'SELECT '+@dbStr+N' COLLATE '+@coll+N' AS [Database],' +
               N' dp.name COLLATE '+@coll+N' AS UserName,' +
               N' sp.name COLLATE '+@coll+N' AS LoginName,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_owner'',dp.name)) AS db_owner,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_datareader'',dp.name)) AS db_datareader,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_datawriter'',dp.name)) AS db_datawriter,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_ddladmin'',dp.name)) AS db_ddladmin,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_securityadmin'',dp.name)) AS db_securityadmin,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_backupoperator'',dp.name)) AS db_backupoperator,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_accessadmin'',dp.name)) AS db_accessadmin,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_denydatareader'',dp.name)) AS db_denydatareader,' +
               N' CONVERT(bit,IS_ROLEMEMBER(''db_denydatawriter'',dp.name)) AS db_denydatawriter' +
               N' FROM '+@dbLit+N'.sys.database_principals dp LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid WHERE dp.type NOT IN (''A'',''R'') AND dp.sid IS NOT NULL AND dp.name NOT IN (''guest'',''sys'',''INFORMATION_SCHEMA'')';
    INSERT INTO #DbRoleMatrix EXEC(@sql);
    FETCH NEXT FROM c INTO @db;
END
CLOSE c; DEALLOCATE c;
SELECT * FROM #DbRoleMatrix ORDER BY [Database], UserName;
