"""
Remediation service for generating T-SQL fix scripts.

Generates granular, per-entity remediation scripts from audit findings.
Only generates scripts for items that CAN be fixed via T-SQL:
- SA account: Disable
- Config settings: sp_configure changes
- Logins: Disable/drop, enable password policy
- Database properties: Trustworthy off, etc.
- DB users: Drop orphaned users, disable guest

Does NOT generate scripts for:
- Backups (manual process)
- Version/patches (external tool)
- Linked servers (requires investigation)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# TSQL templates for each finding type
REMEDIATION_TEMPLATES = {
    "sa_account": {
        "title": "SA Account",
        "risk": "critical",
        "script": """
-- Disable SA account
ALTER LOGIN [sa] DISABLE;
GO
""",
    },
    "config": {
        "title": "Configuration Setting",
        "risk": "varies",
        "script_template": """
-- Set {setting_name} to {required}
EXEC sp_configure '{setting_name}', {required};
RECONFIGURE;
GO
""",
    },
    "login": {
        "title": "SQL Login",
        "risk": "medium",
        "script_disable": """
-- Disable login {login_name}
ALTER LOGIN [{login_name}] DISABLE;
GO
""",
        "script_policy": """
-- Enable password policy for {login_name}
ALTER LOGIN [{login_name}] WITH CHECK_POLICY = ON;
GO
""",
    },
    "database": {
        "title": "Database Property",
        "risk": "high",
        "script_trustworthy": """
-- Disable TRUSTWORTHY for {db_name}
ALTER DATABASE [{db_name}] SET TRUSTWORTHY OFF;
GO
""",
    },
    "db_user": {
        "title": "Database User",
        "risk": "medium",
        "script_orphan": """
-- Remove orphaned user {user_name} from {db_name}
USE [{db_name}];
DROP USER IF EXISTS [{user_name}];
GO
""",
        "script_guest": """
-- Revoke guest access in {db_name}
USE [{db_name}];
REVOKE CONNECT FROM guest;
GO
""",
    },
}


class RemediationService:
    """
    Service for generating T-SQL remediation scripts.
    
    Workflow:
    1. generate_scripts(audit_run_id) - Creates per-entity .sql files
    2. User reviews/runs in SSMS
    3. --finalize detects what was fixed vs excepted
    """
    
    def __init__(
        self,
        db_path: str | Path = "output/audit_history.db",
        output_dir: str | Path = "output/remediation_scripts",
    ):
        """
        Initialize remediation service.
        
        Args:
            db_path: Path to SQLite audit database
            output_dir: Directory for generated scripts
        """
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        logger.info("RemediationService initialized")
    
    def generate_scripts(self, audit_run_id: int | None = None) -> list[Path]:
        """
        Generate remediation scripts for failed findings.
        
        Args:
            audit_run_id: Audit run to generate scripts for (latest if None)
            
        Returns:
            List of paths to generated script files
        """
        import sqlite3
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get audit run ID if not specified
        if audit_run_id is None:
            row = conn.execute(
                "SELECT id FROM audit_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                logger.warning("No audit runs found")
                return []
            audit_run_id = row["id"]
        
        # Get all FAIL/WARN findings for this run
        findings = conn.execute("""
            SELECT f.*, i.instance_name, s.hostname
            FROM findings f
            JOIN instances i ON f.instance_id = i.id
            JOIN servers s ON i.server_id = s.id
            WHERE f.audit_run_id = ? 
            AND f.status IN ('FAIL', 'WARN')
            ORDER BY f.finding_type, f.entity_name
        """, (audit_run_id,)).fetchall()
        
        conn.close()
        
        if not findings:
            logger.info("No findings to remediate for run %d", audit_run_id)
            return []
        
        # Group by server/instance
        by_instance: dict[str, list[dict]] = {}
        for f in findings:
            key = f"{f['hostname']}_{f['instance_name'] or 'default'}".replace("\\", "_")
            if key not in by_instance:
                by_instance[key] = []
            by_instance[key].append(dict(f))
        
        generated = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for instance_key, instance_findings in by_instance.items():
            script_path = self.output_dir / f"remediate_{instance_key}_{timestamp}.sql"
            content = self._generate_instance_script(instance_key, instance_findings)
            
            if content.strip():
                script_path.write_text(content, encoding="utf-8")
                generated.append(script_path)
                logger.info("Generated: %s (%d items)", script_path.name, len(instance_findings))
        
        return generated
    
    def _generate_instance_script(self, instance_key: str, findings: list[dict]) -> str:
        """Generate combined script for one instance."""
        lines = [
            f"-- ============================================================",
            f"-- REMEDIATION SCRIPT",
            f"-- Instance: {instance_key}",
            f"-- Generated: {datetime.now().isoformat()}",
            f"-- Findings: {len(findings)}",
            f"-- ============================================================",
            f"-- ",
            f"-- INSTRUCTIONS:",
            f"-- 1. Review each section below",
            f"-- 2. UNCOMMENT fixes you want to apply",
            f"-- 3. Leave commented = will be marked as exception",
            f"-- 4. Run in SSMS or via --finalize",
            f"-- ============================================================",
            f"",
        ]
        
        # Group by finding type
        by_type: dict[str, list[dict]] = {}
        for f in findings:
            ft = f["finding_type"]
            if ft not in by_type:
                by_type[ft] = []
            by_type[ft].append(f)
        
        for finding_type, type_findings in by_type.items():
            template = REMEDIATION_TEMPLATES.get(finding_type)
            if not template:
                continue  # Non-scriptable type
            
            lines.append(f"-- ============================================================")
            lines.append(f"-- {template['title'].upper()}")
            lines.append(f"-- ============================================================")
            lines.append("")
            
            for f in type_findings:
                script = self._get_script_for_finding(f, template)
                if script:
                    lines.append(f"-- === {f['entity_name']} ===")
                    lines.append(f"-- Entity Key: {f['entity_key']}")
                    lines.append(f"-- Status: {f['status']} | Risk: {f['risk_level'] or 'N/A'}")
                    lines.append(f"-- Description: {f['finding_description'] or 'N/A'}")
                    lines.append(f"-- Recommendation: {f['recommendation'] or 'N/A'}")
                    lines.append(f"--")
                    # Comment out the actual fix
                    for line in script.strip().split("\n"):
                        lines.append(f"-- {line}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def _get_script_for_finding(self, finding: dict, template: dict) -> str | None:
        """Get the appropriate script for a finding."""
        ft = finding["finding_type"]
        entity = finding["entity_name"]
        desc = finding["finding_description"] or ""
        
        if ft == "sa_account":
            return template["script"]
        
        elif ft == "config":
            # Parse required value from description
            # Format: "setting_name=current (required: X)"
            if "required:" in desc:
                try:
                    required = desc.split("required:")[-1].strip().rstrip(")")
                    return template["script_template"].format(
                        setting_name=entity,
                        required=required
                    )
                except Exception:
                    pass
        
        elif ft == "login":
            if "password policy" in desc.lower():
                return template["script_policy"].format(login_name=entity)
            else:
                return template["script_disable"].format(login_name=entity)
        
        elif ft == "database":
            if "trustworthy" in desc.lower():
                return template["script_trustworthy"].format(db_name=entity)
        
        elif ft == "db_user":
            # Entity format: "db_name|user_name"
            parts = entity.split("|")
            if len(parts) == 2:
                db_name, user_name = parts
                if "orphan" in desc.lower():
                    return template["script_orphan"].format(db_name=db_name, user_name=user_name)
                elif "guest" in desc.lower():
                    return template["script_guest"].format(db_name=db_name)
        
        return None


def main():
    """CLI entry point for remediation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate remediation scripts")
    parser.add_argument("--db", default="output/audit_history.db", help="Audit database path")
    parser.add_argument("--output", default="output/remediation_scripts", help="Output directory")
    parser.add_argument("--run-id", type=int, help="Audit run ID (latest if not specified)")
    
    args = parser.parse_args()
    
    service = RemediationService(db_path=args.db, output_dir=args.output)
    scripts = service.generate_scripts(audit_run_id=args.run_id)
    
    print(f"Generated {len(scripts)} script(s):")
    for s in scripts:
        print(f"  {s}")


if __name__ == "__main__":
    main()
