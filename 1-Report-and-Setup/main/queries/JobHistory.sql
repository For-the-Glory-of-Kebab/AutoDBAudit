SELECT TOP (500)
    j.name AS JobName,
    msdb.dbo.agent_datetime(h.run_date, h.run_time) AS RunDateTime,
    CASE h.run_status WHEN 0 THEN 'Failed'
                      WHEN 1 THEN 'Succeeded'
                      WHEN 2 THEN 'Retry'
                      WHEN 3 THEN 'Canceled'
                      WHEN 4 THEN 'InProgress'
         ELSE 'Unknown' END AS RunStatus,
    h.run_duration AS RunDurationHHMMSS,
    h.message
FROM msdb.dbo.sysjobhistory h
JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
WHERE h.step_id = 0
ORDER BY h.instance_id DESC;