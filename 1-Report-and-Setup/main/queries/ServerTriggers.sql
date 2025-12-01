SELECT
    tr.name AS TriggerName,
    tr.is_disabled,
    tr.create_date
FROM sys.server_triggers tr
ORDER BY tr.name;