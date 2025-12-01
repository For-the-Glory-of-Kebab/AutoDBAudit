1. db documentation should be gathered frequently and at least every 6 months
    - server name
    - instancee name 
    - IP address
    - Version (including edition, build, sp and etc.)
    - Usernames of Logins of Groups Sysadmin, Serveradmin, SecurityAdmin and other important groups
    - History of updates
    - History of Revisions and Important changes or necessary actions taken (events)

2. using sql servers other than 2019 and up is prohibited (with exceptions)

3. check if latest update has been installed 
    using 'ProductVersion', 'ProductLevel', 'Edition', 'EngineEdition' and any other available properties

4. the default user 'sa' should be both disabled and renamed (usually to "$@")

5. the password of all users that are members of 'sysadmin', 'serveradmin', 'securityadmin' and other important groups should :
    - follow complexity standards 
    - be non-empty
    - be not the same as the username
    - windows usernames should follow domain policy

6. service account requirements: 
    using virtual accounts for sql server services will cause issues such as obeservability and logging and should be avoided. all sql services that are active should use a domain/local account meaning that it should not be one of these : 
    - LocalService
    - NetworkService
    - LocalSystem

7. Unused Logins should be disabled or removed and should be checked at least periodically (6months):
    logins that are not member of any group (Server Role) and have no mapped database users
    (public group is the default group for all logins and doesn't count as an active group)

8. Users that are members of 'sysadmin', 'serveradmin', 'securityadmin' and other important groups should periodically be checked to follow Least Privilege Principle and Need to know Principle 

9. the user accesses should not have "With Grant" enabled at all 

10. disabling unnecessary and unused features i.e.-> shell ('xp_cmdshell') (this requirement list is old so if there are novel features that are specific to new versions of sql server, they should be added to this list)

11. IF we have encryption on the database, we should have a regular backups of it and its logs and status. 

12. Triggers on various levels (service, db etc.) should be reviewed periodically.

13. users of the database should be reviewed periodically => users without logins (orphaned users) should be removed and also guest user should be disabled.

14. no Sql service/instance should have the Default instance name! 

15. test instances, databases, and unnessesary ones should be deleted or at least detached ( detached ones documented ) => should check for common names with regexes like Adventureworks or test or pubs or northwind and other known ones to make sure

16. Ad Hoc Query feature should be disabled strictly.

17. unnecessary protocols (protocols are stuff like Shared-memory Tcp/ip Named-pipes Via etc.) should be disabled. for most cases only tcp/ip and shared memory should be enabled. 

18. Database mail Xps should be disabled (in rare cases that it might be needed, well documented)

19. SQL server browser should in most cases be disabled (only a few exceptions rarely need this enabled)

20. Remote access => meaning remote execution of SPs and stuff should be disabled (almost no exceptions)

21. Uncessary Sql server Features should be disabled => stuff like Database services, analysis services, reporting, integration services, etc. should be disabled (unless explicitly needed and documented)

22. Auditing of Succussful and unsuccessful logins should be enabled and should be checked periodically 

***

#### software specific requirements , may not be checked in the database-only audit

23. connection strings / credentials etc. should be kept encrypted for sofwares that connect to databases 






    

