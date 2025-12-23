
"""
Mappings of Sheet Names to Column Headers as per EXCEL_COLUMNS.md
Used for robust E2E assertions.
"""

class SheetSpec:
    def __init__(self, name, **cols):
        self.name = name
        self.cols = cols
        for k, v in cols.items():
            setattr(self, k, v)

# 2. Instances
INSTANCES = SheetSpec("Instances",
    SERVER="Server",
    INSTANCE="Instance",
    VERSION_STATUS="Version Status",
    LAST_REVISED="Last Revised"
)

# 3. SA Account
SA_ACCOUNT = SheetSpec("SA Account",
    STATUS="Status",
    IS_DISABLED="Is Disabled",
    IS_RENAMED="Is Renamed",
    REVIEW_STATUS="Review Status",
    NOTES="Notes"
)

# 4. Configuration
CONFIGURATION = SheetSpec("Configuration",
    SETTING="Setting",
    CURRENT="Current",
    REQUIRED="Required",
    STATUS="Status",
    REVIEW_STATUS="Review Status",
    EXCEPTION_REASON="Exception Reason"
)

# 5. Server Logins
LOGINS = SheetSpec("Server Logins",
    LOGIN_NAME="Login Name",
    ENABLED="Enabled",
    PASSWORD_POLICY="Password Policy", 
    REVIEW_STATUS="Review Status",
    NOTES="Notes"
)

# 7. Services
SERVICES = SheetSpec("Services",
    SERVICE_NAME="Service Name",
    STATUS="Status",
    STARTUP="Startup",
    COMPLIANT="Compliant",
    REVIEW_STATUS="Review Status"
)

# 12. Permission Grants
PERMISSIONS = SheetSpec("Permission Grants",
    GRANTEE="Grantee",
    PERMISSION="Permission",
    STATE="State",
    RISK="Risk",
    REVIEW_STATUS="Review Status"
)

# 15. Triggers
TRIGGERS = SheetSpec("Triggers",
    TRIGGER_NAME="Trigger Name",
    SCOPE="Scope",
    ENABLED="Enabled",
    REVIEW_STATUS="Review Status",
    NOTES="Notes"
)

# 17. Client Protocols
PROTOCOLS = SheetSpec("Client Protocols",
    PROTOCOL="Protocol",
    ENABLED="Enabled",
    STATUS="Status",
    REVIEW_STATUS="Review Status",
    NOTES="Notes"
)
