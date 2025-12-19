"""
Collector for Security Policies (Audit, Encryption).
"""

from __future__ import annotations

import logging
from autodbaudit.application.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class SecurityPolicyCollector(BaseCollector):
    """
    Collects high-level security policies:
    - SQL Audits (Server & Database specifications)
    - Encryption hierarchy (SMK, DMK, TDE)
    """

    def collect(self) -> dict[str, int]:
        """
        Collect security policy data.
        Returns dict with counts.
        """
        return {
            "audit": self._collect_audit_settings(),
            "encryption": self._collect_encryption(),
        }

    def _collect_audit_settings(self) -> int:
        """Collect SQL Audit configurations."""
        try:
            audits = self.conn.execute_query(self.prov.get_audit_settings())
            for aud in audits:
                # Query returns SettingName, CurrentValue, RecommendedValue, Status
                setting_name = aud.get("SettingName", "")
                current_value = aud.get("CurrentValue", "")
                recommended = aud.get("RecommendedValue", "")
                status = aud.get("Status", "PASS")

                self.writer.add_audit_setting(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    setting_name=setting_name,
                    current_value=current_value,
                    recommended_value=recommended,
                )

                if status.upper() == "FAIL":
                    self.save_finding(
                        finding_type="audit",
                        entity_name=setting_name,
                        status="FAIL",
                        risk_level="medium",
                        description=f"Audit setting '{setting_name}' is non-compliant: {current_value}",
                        recommendation=f"Set to {recommended}",
                    )
            return len(audits)
        except Exception as e:
            logger.warning("Audit settings failed: %s", e)
            return 0

    def _collect_encryption(self) -> int:
        """Collect encryption settings."""
        try:
            keys = self.conn.execute_query(self.prov.get_encryption_keys())
            for key in keys:
                db_name = key.get("DatabaseName", "")
                key_name = key.get("KeyName", "")
                key_type = key.get("KeyType", "")
                algo = key.get("Algorithm", "")

                self.writer.add_encryption_row(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    database_name=db_name,
                    key_type=key_type,
                    key_name=key_name,
                    algorithm=algo,
                    created_date=key.get("CreateDate"),
                    backup_status="N/A",  # Query doesn't yet support backup status check
                    status=(
                        "WARN"
                        if algo
                        in ("DES", "RC2", "RC4", "RC4_128", "DESX", "TRIPLE_DES_3KEY")
                        else "PASS"
                    ),
                )

                # Check for weak algorithms
                if algo in ("DES", "RC2", "RC4", "RC4_128", "DESX", "TRIPLE_DES_3KEY"):
                    self.save_finding(
                        finding_type="encryption",
                        entity_name=f"{db_name}|{key_name}",
                        status="FAIL",
                        risk_level="high",
                        description=f"Weak encryption algorithm '{algo}' used in '{db_name}'",
                        recommendation="Migrate to AES_128, AES_192, or AES_256",
                    )
            return len(keys)
        except Exception as e:
            logger.warning("Encryption failed: %s", e)
            return 0
