SET NOCOUNT ON;
DECLARE @coll sysname = N'SQL_Latin1_General_CP1_CI_AS';
IF OBJECT_ID('tempdb..#DbULM') IS NOT NULL DROP TABLE #DbULM;
CREATE TABLE #DbULM(
    [Database] sysname NULL,
    UserName sysname NULL,
    LoginName sysname NULL,
    DefaultSchema sysname NULL,
    RoleMembership nvarchar(max) NULL,
    Permissions nvarchar(max) NULL,
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
DECLARE @dbU sysname, @sqlU nvarchar(max);
DECLARE cU CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc='ONLINE';
OPEN cU; FETCH NEXT FROM cU INTO @dbU;
WHILE @@FETCH_STATUS = 0
BEGIN
    DECLARE @dbLit nvarchar(258) = QUOTENAME(@dbU,'"'); -- identifier in cross-db references ("DbName")
    -- Properly build a single-quoted string literal for the database name. QUOTENAME with a single quote
    -- delimiter is invalid T-SQL (previous version caused Unclosed quotation mark). Use manual doubling instead.
    DECLARE @dbStr nvarchar(258) = N'''' + REPLACE(@dbU,'''','''''') + N''''; -- 'DbName'
    SET @sqlU = N'SELECT ' + @dbStr + N' COLLATE '+@coll+N' AS [Database],' +
                N' dp.name COLLATE '+@coll+N' AS UserName,' +
                N' sp.name COLLATE '+@coll+N' AS LoginName,' +
                N' dp.default_schema_name COLLATE '+@coll+N' AS DefaultSchema,' +
                N' (SELECT STRING_AGG(rp.name,'','') FROM '+QUOTENAME(@dbU)+N'.sys.database_role_members drm JOIN '+QUOTENAME(@dbU)+N'.sys.database_principals rp ON drm.role_principal_id = rp.principal_id WHERE drm.member_principal_id = dp.principal_id) AS RoleMembership,' +
                N' (SELECT STRING_AGG(p.permission_name + CASE WHEN p.state_desc <> ''GRANT'' THEN '' (''+p.state_desc+'')'' ELSE '''' END + CASE WHEN p.state_desc = ''GRANT_WITH_GRANT_OPTION'' THEN '' WITH GRANT'' ELSE '''' END, ''; '') FROM '+@dbLit+N'.sys.database_permissions p WHERE p.grantee_principal_id = dp.principal_id) AS Permissions,' +
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
    INSERT INTO #DbULM EXEC (@sqlU);
    FETCH NEXT FROM cU INTO @dbU;
END
CLOSE cU; DEALLOCATE cU;
SELECT * FROM #DbULM ORDER BY [Database], UserName;