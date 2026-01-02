"""
Collector for Server Configuration (sp_configure).
"""

from __future__ import annotations

import logging
from autodbaudit.application.collectors.base import BaseCollector
from autodbaudit.application.common.constants import SECURITY_SETTINGS
from autodbaudit.infrastructure.sqlite.schema import save_config_setting

logger = logging.getLogger(__name__)


class ConfigurationCollector(BaseCollector):
    """
    Collects sp_configure settings and audits them against security best practices.
    """

    def collect(self) -> int:
        """Collect sp_configure settings."""
        try:
            configs = self.conn.execute_query(self.prov.get_sp_configure())
            count = 0
            for cfg in configs:
                count += self._process_config_setting(cfg)
            return count
        except Exception as e:
            logger.warning("Config failed: %s", e)
            return 0

    def _process_config_setting(self, cfg: dict) -> int:  # pylint: disable=too-many-locals
        """Process a single configuration setting."""
        setting_name = cfg.get("SettingName", "")
        setting_key = setting_name.lower()

        # Match against security settings from extracted constants
        for key, (required, default_risk) in SECURITY_SETTINGS.items():
            if key.lower() == setting_key:
                current = cfg.get("RunningValue", 0) or 0
                configured = cfg.get("ConfiguredValue", 0) or 0
                is_dynamic = bool(cfg.get("IsDynamic", 0))

                is_compliant = int(current) == required
                is_config_compliant = int(configured) == required

                status = "PASS"
                risk = None
                desc = f"{setting_name}={current} (required: {required})"
                rec = None

                if not is_compliant:
                    if is_config_compliant:
                        # Config changed but value not active
                        status = "WARN"
                        risk = "medium"
                        if not is_dynamic:
                            desc += " [Pending SQL Restart]"
                            rec = "Restart SQL Server service to apply changes"
                        else:
                            desc += " [Pending RECONFIGURE]"
                            rec = "Run RECONFIGURE statement to apply changes"
                    else:
                        # Neither compliant nor configured
                        status = "FAIL"
                        risk = default_risk
                        rec = f"Set {setting_name} to {required}"

                self.writer.add_config_setting(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    setting_name=setting_name,
                    current_value=int(current),
                    required_value=required,
                    risk_level=(risk if status != "PASS" else "low"),
                )

                # Persist to SQLite (optional)
                if self.ctx.db_conn and self.ctx.instance_id:
                    try:
                        save_config_setting(
                            connection=self.ctx.db_conn,
                            instance_id=self.ctx.instance_id,
                            audit_run_id=self.ctx.audit_run_id,
                            setting_name=setting_name,
                            configured_value=int(configured),
                            running_value=int(current),
                            required_value=required,
                            status=status,
                            risk_level=risk,
                        )
                    except Exception:
                        pass

                # Save finding
                self.save_finding(
                    finding_type="config",
                    entity_name=setting_name,
                    status=status,
                    risk_level=risk,
                    description=desc,
                    recommendation=rec,
                )
                return 1
        return 0
