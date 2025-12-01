SET NOCOUNT ON;
DECLARE @coll sysname = N'SQL_Latin1_General_CP1_CI_AS';
IF OBJECT_ID('tempdb..#DbTriggers') IS NOT NULL DROP TABLE #DbTriggers;
CREATE TABLE #DbTriggers(
    [Database] sysname NULL,
    TriggerName sysname NULL,
    ParentSchema sysname NULL,
    ParentObject sysname NULL,
    is_disabled bit NULL,
    is_instead_of_trigger bit NULL,
    create_date datetime NULL
);
DECLARE @dbT sysname, @sqlT nvarchar(max);
DECLARE cT CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.databases WHERE database_id > 4 AND state_desc='ONLINE';
OPEN cT; FETCH NEXT FROM cT INTO @dbT;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sqlT = N'SELECT ' + QUOTENAME(@dbT,'''') + N' COLLATE '+@coll+N' AS [Database],' +
                N' tr.name COLLATE '+@coll+N' AS TriggerName,' +
                N' OBJECT_SCHEMA_NAME(tr.parent_id, DB_ID(''' + REPLACE(@dbT,'''','''''') + N''')) COLLATE '+@coll+N' AS ParentSchema,' +
                N' OBJECT_NAME(tr.parent_id, DB_ID(''' + REPLACE(@dbT,'''','''''') + N''')) COLLATE '+@coll+N' AS ParentObject,' +
                N' tr.is_disabled, tr.is_instead_of_trigger, tr.create_date' +
                N' FROM '+QUOTENAME(@dbT)+N'.sys.triggers tr WHERE tr.parent_class_desc = ''OBJECT_OR_COLUMN''';
    INSERT INTO #DbTriggers EXEC (@sqlT);
    FETCH NEXT FROM cT INTO @dbT;
END
CLOSE cT; DEALLOCATE cT;
SELECT * FROM #DbTriggers ORDER BY [Database], TriggerName;