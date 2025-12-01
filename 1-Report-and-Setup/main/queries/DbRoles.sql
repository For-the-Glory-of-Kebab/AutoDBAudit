SET NOCOUNT ON;
DECLARE @coll sysname = N'SQL_Latin1_General_CP1_CI_AS';
IF OBJECT_ID('tempdb..#DbRoles') IS NOT NULL DROP TABLE #DbRoles;
CREATE TABLE #DbRoles(
    [Database] sysname NULL,
    RoleName sysname NULL,
    MemberName sysname NULL,
    MemberType nvarchar(60) NULL
);
DECLARE @dbR sysname, @sqlR nvarchar(max);
DECLARE dbcur CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc='ONLINE';
OPEN dbcur; FETCH NEXT FROM dbcur INTO @dbR;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sqlR = N'SELECT ' + QUOTENAME(@dbR,'''') + N' COLLATE '+@coll+N' AS [Database],' +
                N' r.name COLLATE '+@coll+N' AS RoleName,' +
                N' m.name COLLATE '+@coll+N' AS MemberName,' +
                N' m.type_desc COLLATE '+@coll+N' AS MemberType' +
                N' FROM '+QUOTENAME(@dbR)+N'.sys.database_principals r' +
                N' JOIN '+QUOTENAME(@dbR)+N'.sys.database_role_members rm ON r.principal_id = rm.role_principal_id' +
                N' JOIN '+QUOTENAME(@dbR)+N'.sys.database_principals m ON rm.member_principal_id = m.principal_id' +
                N' WHERE r.type = ''R'' AND m.name NOT IN (''dbo'',''guest'',''sys'',''INFORMATION_SCHEMA'')';
    INSERT INTO #DbRoles EXEC (@sqlR);
    FETCH NEXT FROM dbcur INTO @dbR;
END
CLOSE dbcur; DEALLOCATE dbcur;
SELECT * FROM #DbRoles ORDER BY [Database], RoleName, MemberName;