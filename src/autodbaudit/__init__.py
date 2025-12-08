"""
AutoDBAudit - SQL Server Security Audit Tool.

Generates 17-sheet Excel reports for SQL Server security compliance auditing.
Supports SQL Server 2008 R2 through 2025+.

Usage:
    # CLI (recommended)
    python main.py --audit
    
    # Programmatic
    from autodbaudit.application.audit_service import AuditService
    
    service = AuditService()
    report_path = service.run_audit("config/audit_config.json", "config/sql_targets.json")
"""

__version__ = "0.1.0"
__author__ = "AutoDBAudit Team"

from autodbaudit.application.audit_service import AuditService

__all__ = ["AuditService", "__version__"]
