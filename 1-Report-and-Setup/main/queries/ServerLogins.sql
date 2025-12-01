SELECT
    sp.name                    AS LoginName,
    sp.type_desc               AS LoginType,
    sp.is_disabled             AS IsDisabled,
    sp.default_database_name   AS DefaultDatabase,
    sp.default_language_name   AS DefaultLanguage,
    sp.create_date,
    sp.modify_date,
    sl.is_policy_checked       AS EnforcePasswordPolicy,
    sl.is_expiration_checked   AS EnforcePasswordExpiration,
    CASE WHEN sp.is_disabled = 0 THEN 1 ELSE 0 END AS HasAccess,
    CASE WHEN sp.is_disabled = 1 THEN 1 ELSE 0 END AS IsDisabledLogin
FROM sys.server_principals sp
LEFT JOIN sys.sql_logins sl ON sp.principal_id = sl.principal_id
WHERE sp.type IN ('S','U','G')
ORDER BY sp.name;