SELECT
    ls.name          AS LinkedServer,
    ls.provider      AS Provider,
    ls.product       AS Product,
    ls.data_source   AS DataSource,
    ls.location      AS Location,
    ls.catalog       AS Catalog,
    ls.is_linked     AS IsLinked,
    ls.is_remote_login_enabled AS IsRemoteLoginEnabled,
    sp.remote_name   AS RemoteUser
FROM sys.servers ls
LEFT JOIN sys.linked_logins sp ON ls.server_id = sp.server_id
WHERE ls.is_linked = 1
ORDER BY ls.name;