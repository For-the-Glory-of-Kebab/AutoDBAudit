DECLARE @major int = TRY_CAST(PARSENAME(CONVERT(varchar(128), SERVERPROPERTY('ProductVersion')),4) AS int);

IF (@major IS NOT NULL AND @major >= 11)
BEGIN
    IF OBJECT_ID('sys.dm_tcp_listener_states') IS NOT NULL
    BEGIN
        SELECT DISTINCT
            ip_address,
            port
        FROM sys.dm_tcp_listener_states
        ORDER BY ip_address, port;
    END
    ELSE
    BEGIN
        SELECT CAST(NULL AS varchar(64)) AS ip_address,
               CAST(NULL AS int)         AS port;
    END
END
ELSE
BEGIN
    DECLARE @tcpPort nvarchar(50), @tcpDynamic nvarchar(50);
    EXEC master.dbo.xp_instance_regread N'HKEY_LOCAL_MACHINE',
        N'SOFTWARE\Microsoft\Microsoft SQL Server\MSSQLServer\SuperSocketNetLib\Tcp\IPAll',
        N'TcpPort', @tcpPort OUTPUT;
    EXEC master.dbo.xp_instance_regread N'HKEY_LOCAL_MACHINE',
        N'SOFTWARE\Microsoft\Microsoft SQL Server\MSSQLServer\SuperSocketNetLib\Tcp\IPAll',
        N'TcpDynamicPorts', @tcpDynamic OUTPUT;

    SELECT 
        'IPAll' AS ip_address,
        @tcpPort AS port,
        'REGISTRY' AS type_desc,
        CASE WHEN @tcpPort IS NOT NULL OR @tcpDynamic IS NOT NULL THEN 'LISTENER' ELSE 'DISABLED' END AS state_desc;
END