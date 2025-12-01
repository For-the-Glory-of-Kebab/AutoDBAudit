SELECT
    @@SERVERNAME                               AS InstanceDisplayName,
    SERVERPROPERTY('ServerName')               AS ServerName,
    SERVERPROPERTY('MachineName')              AS MachineName,
    SERVERPROPERTY('InstanceName')             AS InstanceName,
    SERVERPROPERTY('Edition')                  AS Edition,
    SERVERPROPERTY('ProductVersion')           AS ProductVersion,
    SERVERPROPERTY('ProductLevel')             AS ProductLevel,
    SERVERPROPERTY('ResourceVersion')          AS ResourceVersion,
    SERVERPROPERTY('Collation')                AS Collation,
    SERVERPROPERTY('IsClustered')              AS IsClustered,
    SERVERPROPERTY('IsHadrEnabled')            AS IsHadrEnabled,
    SERVERPROPERTY('ProcessID')                AS ProcessID,
    (SELECT STRING_AGG(CAST(port AS varchar(10)), ',')
       FROM (SELECT DISTINCT local_tcp_port AS port
             FROM sys.dm_exec_connections
             WHERE local_tcp_port IS NOT NULL) p) AS ListeningPorts,
    (SELECT STRING_AGG(ip_address, ',')
       FROM (SELECT DISTINCT ip_address
             FROM sys.dm_tcp_listener_states
             WHERE ip_address NOT IN ('::','0.0.0.0')) a) AS IPAddresses;