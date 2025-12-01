USE master;

IF OBJECT_ID('sys.server_network_protocols') IS NOT NULL
BEGIN
    SELECT protocol_desc,
           type_desc,
           [order],
           is_enabled,
           is_hidden
    FROM sys.server_network_protocols
    ORDER BY [order];
END
ELSE
BEGIN
    SELECT 'Unavailable' AS protocol_desc,
           NULL AS type_desc,
           NULL AS [order],
           NULL AS is_enabled,
           NULL AS is_hidden;
END