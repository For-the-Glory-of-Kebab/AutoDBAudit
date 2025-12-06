"""
AutoDBAudit - SQL Server Security Audit Tool.

A self-contained, offline-capable tool for auditing SQL Server instances
against security compliance requirements.

Features:
- Audit SQL Server 2008 R2 through 2022+ against 22+ security requirements
- Generate professional Excel reports with trends and formatting
- Track audit history in SQLite for year-over-year comparison
- Generate remediation scripts for identified issues
- Orchestrate SQL Server hotfix deployments across multiple servers

Usage:
    from autodbaudit.application.audit_service import AuditService
    
    service = AuditService()
    report_path = service.run_audit("config/audit_config.json", "config/sql_targets.json")
"""

__version__ = "0.1.0"
__author__ = "AutoDBAudit Team"

# Expose main entry points for convenience
from autodbaudit.application.audit_service import AuditService

__all__ = ["AuditService", "__version__"]
