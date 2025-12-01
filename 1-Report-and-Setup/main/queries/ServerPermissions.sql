SELECT
    pr.name        AS PrincipalName,
    pr.type_desc   AS PrincipalType,
    pe.class_desc,
    pe.permission_name,
    pe.state_desc,
    CASE WHEN pe.state_desc = 'GRANT_WITH_GRANT_OPTION' THEN 1 ELSE 0 END AS WithGrantOption
FROM sys.server_permissions pe
JOIN sys.server_principals pr ON pe.grantee_principal_id = pr.principal_id
WHERE pr.type IN ('S','U','G')
ORDER BY pr.name, pe.permission_name;