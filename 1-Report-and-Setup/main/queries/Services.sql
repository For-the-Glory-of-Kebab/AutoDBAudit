IF OBJECT_ID('sys.dm_server_services') IS NOT NULL
BEGIN
    SELECT
        servicename                       AS ServiceName,
        startup_type_desc                 AS StartupType,
        status_desc                       AS Status,
        last_startup_time                 AS LastStartupTime,
        filename                          AS ExecutablePath,
        is_clustered                      AS IsClustered,
        instant_file_initialization_enabled AS IFIEnabled
    FROM sys.dm_server_services
    ORDER BY servicename;
END
ELSE
BEGIN
    SELECT 'Unavailable' AS ServiceName,
           NULL AS StartupType,
           NULL AS Status,
           NULL AS LastStartupTime,
           NULL AS ExecutablePath,
           NULL AS IsClustered,
           NULL AS IFIEnabled;
END