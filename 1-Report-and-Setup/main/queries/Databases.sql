SELECT
    d.name                                  AS [Database],
    d.database_id,
    d.state_desc,
    d.recovery_model_desc,
    suser_sname(d.owner_sid)                AS Owner,
    d.create_date,
    d.compatibility_level,
    d.collation_name,
    d.containment_desc,
    d.is_query_store_on,
    d.is_encrypted,
    d.is_read_only,
    d.is_auto_close_on,
    d.is_auto_shrink_on,
    d.is_auto_update_stats_on,
    d.is_auto_update_stats_async_on,
    d.is_parameterization_forced,
    d.page_verify_option_desc,
    (SELECT MAX(backup_finish_date)
       FROM msdb.dbo.backupset b
      WHERE b.database_name = d.name AND type='D') AS LastFullBackup,
    (SELECT MAX(backup_finish_date)
       FROM msdb.dbo.backupset b
      WHERE b.database_name = d.name AND type='I') AS LastDiffBackup,
    (SELECT MAX(backup_finish_date)
       FROM msdb.dbo.backupset b
      WHERE b.database_name = d.name AND type='L') AS LastLogBackup
FROM sys.databases d
WHERE d.database_id > 4
ORDER BY d.name;