
import json
import logging
from pathlib import Path
from datetime import datetime
from autodbaudit.application.audit_service import AuditService
from autodbaudit.infrastructure.excel import EnhancedReportWriter

logger = logging.getLogger(__name__)

class MockAuditService(AuditService):
    """
    Mock Service for E2E Testing.
    Reads findings from JSON files instead of SQL Server.
    """
    
    def __init__(self, config_dir, output_dir, finding_dir: str):
        super().__init__(config_dir, output_dir)
        self.finding_dir = Path(finding_dir)
        
    def run_audit(self, targets_file="sql_targets.json", organization=None, skip_save=False, writer=None):
        logger.info("MOCK AUDIT: Reading from %s", self.finding_dir)
        
        # Init Store
        store = self._get_history_store()
        
        # Use provided org or default
        final_org = organization or "Mock Org"
        run = store.begin_audit_run(organization=final_org)
        self._audit_run_id = run.id
        
        if writer is None:
            writer = EnhancedReportWriter()
            writer.set_audit_info(run.id, final_org, "Mock Audit", datetime.now())
            
        # Discover Findings
        if not self.finding_dir.exists():
            logger.error("Finding dir %s does not exist", self.finding_dir)
            return writer

        # Loop through files like {run_id}_{type}.json
        # Format: list of dicts. Each dict is a finding row.
        # We need to map these to: 
        # 1. Store (save_finding)
        # 2. Writer (add_X)
        
        # We also need a fake Instance/Server in DB
        # Look for first finding to get server name?
        # Or just create a default one.
        
        server = store.upsert_server("TEST-SERVER", "127.0.0.1")
        instance = store.upsert_instance(server, "MSSQLSERVER", 1433, "15.0.2000", 15, "Developer", "RTM")
        store.link_instance_to_run(run.id, instance.id)
        
        for fpath in self.finding_dir.glob("*.json"):
            logger.info("Processing mock file: %s", fpath.name)
            with open(fpath, "r") as f:
                data = json.load(f) # List of bindings
                
            # Determine type from filename (e.g. "1_logins.json" -> "logins")
            # Or assume content has it?
            # Let's use filename suffix: "logins.json"
            ftype_raw = fpath.stem.split("_")[-1]  # "logins"
            
            for item in data:
                # Ensure basics
                item["server_name"] = "TEST-SERVER"
                item["instance_name"] = "MSSQLSERVER"
                
                # 1. Save to DB (Generic)
                # finding_type needs to match what SyncService expects (e.g. "server_principals")
                # Mapper logic?
                # User's mock data must use correct finding_type key if needed.
                # Assuming 'finding_type' field is in item or we map 'ftype_raw'
                
                ftype_db = item.get("finding_type", ftype_raw)
                
                # Store expects specific columns. JSON should match.
                # Manual insertion since FindingDAO is internal
                conn = store._get_connection()
                
                # Derive status/risk usually done by Collector logic. Mock data provides it.
                status = item.get("Status", "FAIL") 
                risk = item.get("Risk", "High")
                # Map booleans to Status if missing
                if "Status" not in item:
                    # Heuristic for Logins
                    if ftype_db == "logins":
                        status = "PASS" if item.get("PasswordPolicyChecked") else "FAIL"
                
                key = self._generate_key(ftype_db, item)
                
                try:
                    conn.execute(
                        """
                        INSERT INTO findings (
                            audit_run_id, instance_id, entity_key, finding_type,
                            entity_name, status, risk_level, finding_description, details
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run.id,
                            instance.id,
                            key,
                            ftype_db,
                            item.get("LoginName") or item.get("User") or item.get("Name") or "Unknown",
                            status,
                            risk,
                            item.get("Description", "Mock Finding"),
                            json.dumps(item) # Store raw JSON in details for debugging
                        )
                    )
                    conn.commit()
                except Exception as e:
                    logger.error("DB Insert Failed for %s: %s", key, e)
                
                # 2. Add to Excel
                self._dispatch_to_writer(writer, ftype_db, item)
                
        store.complete_audit_run(run.id, "completed")
        
        if skip_save:
            return writer
        return self._save_report(writer, run.id)

    def _generate_key(self, ftype, item):
        # Naive key generator for mock
        if ftype == "logins": return item.get("LoginName")
        if ftype == "users": return f"{item.get('Database')}|{item.get('UserName')}"
        if ftype == "roles": return f"{item.get('Role')}|{item.get('Member')}"
        return str(item)

    def _dispatch_to_writer(self, writer, ftype, item):
        # Map finding types to writer methods
        # This is CRITICAL for Excel generation
        try:
            if ftype == "logins":
                writer.add_server_principal(
                    server_name=item["server_name"],
                    instance_name=item["instance_name"],
                    name=item.get("LoginName"),
                    type_desc=item.get("LoginType"),
                    is_disabled=bool(item.get("IsDisabled")),
                    password_policy=bool(item.get("PasswordPolicyChecked")),
                    default_database=item.get("DefaultDatabase", "master")
                )
            # Add more types as we add nuclear tests...
        except Exception as e:
            logger.error("Failed to write mock item to Excel: %s", e)

