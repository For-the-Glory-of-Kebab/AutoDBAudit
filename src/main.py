"""
AutoDBAudit - SQL Server Security Audit and Remediation Tool

A self-contained, offline-capable tool for SQL Server security compliance auditing,
discrepancy analysis, remediation script generation, and centralized hotfix deployment.
"""

import sys
from autodbaudit.interface.cli import main


if __name__ == "__main__":
    sys.exit(main())
