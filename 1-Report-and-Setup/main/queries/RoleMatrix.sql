SELECT
    sp.name AS LoginName,
    sp.type_desc AS LoginType,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('sysadmin',    sp.name),0)) AS sysadmin,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('serveradmin', sp.name),0)) AS serveradmin,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('securityadmin', sp.name),0)) AS securityadmin,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('processadmin', sp.name),0)) AS processadmin,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('setupadmin', sp.name),0)) AS setupadmin,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('diskadmin', sp.name),0)) AS diskadmin,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('dbcreator', sp.name),0)) AS dbcreator,
    CONVERT(bit, ISNULL(IS_SRVROLEMEMBER('bulkadmin', sp.name),0)) AS bulkadmin
FROM sys.server_principals sp
WHERE sp.type IN ('S','U','G')
ORDER BY sp.name;