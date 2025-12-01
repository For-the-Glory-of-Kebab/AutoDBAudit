SELECT
    j.name AS JobName,
    j.enabled AS JobEnabled,
    sch.name AS ScheduleName,
    sch.enabled AS ScheduleEnabled,
    CASE sch.freq_type
         WHEN 1 THEN 'Once'
         WHEN 4 THEN 'Daily'
         WHEN 8 THEN 'Weekly'
         WHEN 16 THEN 'Monthly'
         WHEN 32 THEN 'MonthlyRelative'
         WHEN 64 THEN 'WhenSQLStarts'
         WHEN 128 THEN 'WhenCPUIdle'
         WHEN 256 THEN 'OnIdleSchedule'
         ELSE CONCAT('Type_', sch.freq_type)
    END AS FrequencyType,
    sch.freq_interval,
    sch.freq_subday_type,
    sch.freq_subday_interval,
    sch.active_start_date,
    sch.active_start_time,
    msdb.dbo.agent_datetime(jh.run_date, jh.run_time) AS LastRunDateTime,
    CASE jh.run_status WHEN 0 THEN 'Failed'
                       WHEN 1 THEN 'Succeeded'
                       WHEN 2 THEN 'Retry'
                       WHEN 3 THEN 'Canceled'
                       WHEN 4 THEN 'InProgress'
         ELSE 'Unknown' END AS LastRunStatus,
    jh.run_duration AS LastRunDurationHHMMSS,
    j.date_created AS JobCreated
FROM msdb.dbo.sysjobs j
LEFT JOIN msdb.dbo.sysjobschedules js ON j.job_id = js.job_id
LEFT JOIN msdb.dbo.sysschedules sch ON js.schedule_id = sch.schedule_id
OUTER APPLY (
    SELECT TOP (1) h.run_status, h.run_date, h.run_time, h.run_duration
    FROM msdb.dbo.sysjobhistory h
    WHERE h.job_id = j.job_id AND h.step_id = 0
    ORDER BY h.instance_id DESC
) jh
ORDER BY j.name;