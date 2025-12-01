SET NOCOUNT ON;
DECLARE @coll sysname = N'SQL_Latin1_General_CP1_CI_AS';
IF OBJECT_ID('tempdb..#DbUsers') IS NOT NULL DROP TABLE #DbUsers;
CREATE TABLE #DbUsers (
    [Database] sysname NULL,
    UserName sysname NULL,
    UserType nvarchar(60) NULL,
    AuthType nvarchar(60) NULL,
    DefaultSchema sysname NULL,
    LoginName sysname NULL
);
DECLARE @db sysname, @sql nvarchar(max);
DECLARE dbs CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc='ONLINE';
OPEN dbs; FETCH NEXT FROM dbs INTO @db;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'SELECT ' + QUOTENAME(@db,'''') + N' COLLATE '+@coll+N' AS [Database],' +
               N' dp.name COLLATE '+@coll+N' AS UserName,' +
               N' dp.type_desc COLLATE '+@coll+N' AS UserType,' +
               N' dp.authentication_type_desc COLLATE '+@coll+N' AS AuthType,' +
               N' dp.default_schema_name COLLATE '+@coll+N' AS DefaultSchema,' +
               N' sp.name COLLATE '+@coll+N' AS LoginName' +
               N' FROM '+QUOTENAME(@db)+N'.sys.database_principals dp' +
               N' LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid' +
               N' WHERE dp.type NOT IN (''A'',''R'') AND dp.sid IS NOT NULL' +
               N' AND dp.name NOT IN (''dbo'',''guest'',''sys'',''INFORMATION_SCHEMA'')';
    INSERT INTO #DbUsers EXEC (@sql);
    FETCH NEXT FROM dbs INTO @db;
END
CLOSE dbs; DEALLOCATE dbs;
SELECT * FROM #DbUsers ORDER BY [Database], UserName;