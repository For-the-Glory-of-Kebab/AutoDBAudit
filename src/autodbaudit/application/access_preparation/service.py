"""
Access Preparation Service.

Orchestrates remote access preparation for all targets using
8-layer fallback strategy:
1. WinRM (existing)
2. WMI
3. PsExec
4. schtasks
5. SC.exe
6. reg.exe
7. PowerShell Direct
8. Manual script generation

Provides capability flags for sync/remediation integration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from autodbaudit.infrastructure.sqlite.store import HistoryStore
    from autodbaudit.infrastructure.config_loader import SqlTarget

logger = logging.getLogger(__name__)


@dataclass
class AccessStatus:
    """Access status for a single target with capability flags."""

    target_id: str
    hostname: str
    os_type: Literal["windows", "linux", "unknown"] = "unknown"

    # Access configuration
    access_method: Literal["winrm", "wmi", "psexec", "ssh", "sql_only", "none"] = "none"
    access_status: Literal["ready", "partial", "failed", "manual", "unknown"] = (
        "unknown"
    )
    access_error: str | None = None

    # Capability flags for sync/remediation
    can_pull_os_data: bool = False  # Can query WMI, services, registry
    can_push_os_fixes: bool = False  # Can apply service/config changes
    available_methods: list[str] = field(default_factory=list)

    # Layer results
    layer_results: list[dict] = field(default_factory=list)

    # State for revert
    original_snapshot: dict = field(default_factory=dict)
    changes_made: list[dict] = field(default_factory=list)

    # Timestamps
    prepared_at: datetime | None = None
    last_verified_at: datetime | None = None

    # Manual handling
    manual_override: bool = False
    override_reason: str | None = None
    manual_script_path: str | None = None


class AccessPreparationService:
    """
    Service for preparing remote access to SQL Server targets.

    Usage:
        service = AccessPreparationService(store, output_dir)
        results = service.prepare_all(targets)
        service.show_status()
        service.revert_all()

    After preparation, access status is available for sync/remediation:
        status = service.get_status(target_id)
        if status.can_pull_os_data:
            # Pull client protocols, IPs, service info
        if status.can_push_os_fixes:
            # Apply service-level fixes
    """

    def __init__(
        self,
        store: HistoryStore,
        output_dir: Path | None = None,
    ):
        """
        Initialize access preparation service.

        Args:
            store: History store for persisting access status
            output_dir: Directory for manual scripts (default: output/)
        """
        self.store = store
        self.output_dir = output_dir or Path("output")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure access_status table exists."""
        from autodbaudit.infrastructure.sqlite.access_schema import ACCESS_SCHEMA

        conn = self.store._get_connection()
        conn.executescript(ACCESS_SCHEMA)
        conn.commit()
        logger.info("Access schema initialized")

    def prepare_all(self, targets: list[SqlTarget]) -> list[AccessStatus]:
        """
        Prepare access for all targets using 8-layer strategy.

        Args:
            targets: List of SQL targets to prepare

        Returns:
            List of AccessStatus results
        """
        results = []

        for target in targets:
            if not target.enabled:
                logger.info("Skipping disabled target: %s", target.id)
                continue

            logger.info("Preparing access for: %s", target.display_name)
            status = self._prepare_target(target)
            results.append(status)
            self._save_status(status)

        return results

    def _prepare_target(self, target: SqlTarget) -> AccessStatus:
        """
        Prepare access for a single target.

        Uses 8-layer fallback strategy, capturing state before changes.
        """
        status = AccessStatus(
            target_id=target.id,
            hostname=target.server,
            prepared_at=datetime.now(timezone.utc),
        )

        # Check if already marked as manual/ready
        existing = self.get_status(target.id)
        if existing and existing.access_status in ("ready", "manual"):
            # Re-verify it still works
            if self._verify_access(target):
                logger.info("Target %s already accessible, verified", target.id)
                existing.last_verified_at = datetime.now(timezone.utc)
                return existing
            else:
                logger.warning(
                    "Target %s marked ready but verification failed", target.id
                )

        # Detect OS type
        status.os_type = self._detect_os_type(target)
        logger.info("Detected OS type: %s for %s", status.os_type, target.id)

        if status.os_type == "linux":
            # Linux - SQL only for now
            status.access_method = "sql_only"
            status.access_status = "ready"
            status.can_pull_os_data = False
            status.can_push_os_fixes = False
            logger.info("Linux target - using SQL-only access")

        elif status.os_type == "windows":
            # Windows - try all layers
            status = self._prepare_windows_multilayer(target, status)

        else:
            # Unknown OS
            status.access_method = "sql_only"
            status.access_status = "partial"
            status.access_error = "Could not determine OS type"

        status.last_verified_at = datetime.now(timezone.utc)
        return status

    def _prepare_windows_multilayer(
        self, target: SqlTarget, status: AccessStatus
    ) -> AccessStatus:
        """
        Prepare Windows target using 8-layer strategy.
        """
        from autodbaudit.application.access_preparation.state_snapshot import (
            StateSnapshotCapture,
        )
        from autodbaudit.application.access_preparation.access_layers import (
            AccessLayerOrchestrator,
        )
        from autodbaudit.application.access_preparation.manual_script import (
            ManualScriptGenerator,
        )

        # Get OS credentials
        os_user, os_pass = self._get_os_credentials(target)

        # Capture state before any changes
        logger.info("Capturing original state for %s", target.id)
        capturer = StateSnapshotCapture(target.id, target.server)

        # Try WMI state capture first (if accessible)
        machine_state = capturer.capture_remote_via_wmi(os_user, os_pass)
        if machine_state:
            status.original_snapshot = json.loads(machine_state.to_json())
        else:
            # Capture what we can from local perspective
            status.original_snapshot = {"capture_failed": True}

        # Try all automated layers
        orchestrator = AccessLayerOrchestrator(target.server, os_user, os_pass)

        success, layer_results = orchestrator.try_all_layers()
        status.layer_results = [r.__dict__ for r in layer_results]

        if success:
            # Determine which layer worked
            working_layer = next(
                (r.layer for r in layer_results if r.success), "unknown"
            )
            status.access_method = "winrm"
            status.access_status = "ready"
            status.can_pull_os_data = True
            status.can_push_os_fixes = True
            status.available_methods = [working_layer]

            # Record changes made
            for r in layer_results:
                if r.success and r.changes_made:
                    status.changes_made.extend(r.changes_made)

            logger.info("✅ Access enabled via %s for %s", working_layer, target.id)

        else:
            # All automated layers failed - generate manual script
            logger.warning(
                "All automated layers failed for %s, generating manual script",
                target.id,
            )

            generator = ManualScriptGenerator(self.output_dir)
            script_path = generator.generate_enable_script(target)

            status.access_method = "none"
            status.access_status = "failed"
            status.can_pull_os_data = False
            status.can_push_os_fixes = False
            status.manual_script_path = str(script_path)

            # Compile error summary
            errors = [r.error_message for r in layer_results if r.error_message]
            status.access_error = (
                "; ".join(errors[:3]) if errors else "All layers failed"
            )

        return status

    def _get_os_credentials(self, target: SqlTarget) -> tuple[str | None, str | None]:
        """
        Get OS credentials for target.

        Checks for os_username attribute, falls back to SQL credentials
        if applicable, or None for integrated auth (current user).
        """
        # Check for explicit OS credentials
        os_username = getattr(target, "os_username", None)
        os_credential_file = getattr(target, "os_credential_file", None)

        if os_credential_file:
            # Load from credential file
            try:
                from autodbaudit.infrastructure.config_loader import ConfigLoader

                creds = ConfigLoader()._load_credential_file(Path(os_credential_file))
                return creds.get("username"), creds.get("password")
            except Exception as e:
                logger.warning("Failed to load OS credentials: %s", e)

        if os_username:
            # OS username specified, look for password
            os_password = getattr(target, "os_password", None)
            return os_username, os_password

        # Fall back to SQL credentials if using SQL auth
        if target.auth == "sql" and target.username and target.password:
            return target.username, target.password

        # Integrated auth - use current user (None, None)
        return None, None

    def _detect_os_type(
        self, target: SqlTarget
    ) -> Literal["windows", "linux", "unknown"]:
        """Detect the OS type of a target via T-SQL."""
        import pyodbc

        try:
            conn_str = self._build_connection_string(target)
            with pyodbc.connect(conn_str, timeout=target.connect_timeout) as conn:
                cursor = conn.execute("SELECT host_platform FROM sys.dm_os_host_info")
                row = cursor.fetchone()
                if row:
                    platform = row[0].lower()
                    if "windows" in platform:
                        return "windows"
                    if "linux" in platform:
                        return "linux"
        except Exception as e:
            # Check for 'Invalid object name' (Error 208/42S02) - typical for older SQL versions
            error_str = str(e)
            if "Invalid object name" in error_str or "42S02" in error_str:
                logger.debug(
                    "sys.dm_os_host_info not available (likely pre-2017 SQL): %s", e
                )
            else:
                logger.warning(
                    "Could not detect OS via dm_os_host_info for %s: %s", target.id, e
                )
            # Fallback: @@VERSION
            try:
                with pyodbc.connect(conn_str, timeout=target.connect_timeout) as conn:
                    cursor = conn.execute("SELECT @@VERSION")
                    row = cursor.fetchone()
                    if row:
                        version = row[0].lower()
                        if "windows" in version:
                            return "windows"
                        if "linux" in version:
                            return "linux"
            except Exception:
                pass

        return "unknown"

    def _verify_access(self, target: SqlTarget) -> bool:
        """Verify WinRM access to target."""
        from autodbaudit.application.access_preparation.access_layers import (
            Layer1_WinRM,
        )

        os_user, os_pass = self._get_os_credentials(target)
        layer = Layer1_WinRM(target.server, os_user, os_pass)
        return layer.test_access()

    def _build_connection_string(self, target: SqlTarget) -> str:
        """Build ODBC connection string for target."""
        parts = [
            "DRIVER={ODBC Driver 17 for SQL Server}",
            f"SERVER={target.server_instance}",
            f"Timeout={target.connect_timeout}",
        ]

        if target.auth == "sql":
            parts.extend(
                [
                    f"UID={target.username}",
                    f"PWD={target.password}",
                ]
            )
        else:
            parts.append("Trusted_Connection=yes")

        return ";".join(parts)

    def _save_status(self, status: AccessStatus) -> None:
        """Save access status to database."""
        conn = self.store._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO access_status (
                target_id, hostname, os_type, access_method, access_status,
                access_error, original_snapshot, changes_made,
                prepared_at, last_verified_at, manual_override, override_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                status.target_id,
                status.hostname,
                status.os_type,
                status.access_method,
                status.access_status,
                status.access_error,
                json.dumps(status.original_snapshot),
                json.dumps(status.changes_made),
                status.prepared_at.isoformat() if status.prepared_at else None,
                (
                    status.last_verified_at.isoformat()
                    if status.last_verified_at
                    else None
                ),
                1 if status.manual_override else 0,
                status.override_reason,
            ),
        )
        conn.commit()

    def get_status(self, target_id: str) -> AccessStatus | None:
        """Get access status for a target."""
        conn = self.store._get_connection()
        cursor = conn.execute(
            "SELECT * FROM access_status WHERE target_id = ?",
            (target_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return AccessStatus(
            target_id=row[1],
            hostname=row[2],
            os_type=row[3],
            access_method=row[4],
            access_status=row[5],
            access_error=row[6],
            original_snapshot=json.loads(row[7]) if row[7] else {},
            changes_made=json.loads(row[8]) if row[8] else [],
            prepared_at=datetime.fromisoformat(row[9]) if row[9] else None,
            last_verified_at=datetime.fromisoformat(row[10]) if row[10] else None,
            manual_override=bool(row[11]),
            override_reason=row[12],
            # Capability flags derived from access_status
            can_pull_os_data=row[5] in ("ready", "manual"),
            can_push_os_fixes=row[5] == "ready",
        )

    def get_all_status(self) -> list[AccessStatus]:
        """Get access status for all targets."""
        conn = self.store._get_connection()
        cursor = conn.execute("SELECT target_id FROM access_status")
        return [
            status
            for row in cursor.fetchall()
            if (status := self.get_status(row[0])) is not None
        ]

    def mark_accessible(self, target_id: str, reason: str) -> None:
        """
        Manually mark a target as accessible.

        Use when user has manually run the enable script on target.
        """
        conn = self.store._get_connection()
        conn.execute(
            """
            UPDATE access_status
            SET access_status = 'manual', 
                access_method = 'winrm',
                manual_override = 1, 
                override_reason = ?,
                last_verified_at = ?
            WHERE target_id = ?
            """,
            (reason, datetime.now(timezone.utc).isoformat(), target_id),
        )
        conn.commit()
        logger.info("Marked %s as manually accessible: %s", target_id, reason)

    def detect_manual_completion(self, target_id: str) -> bool:
        """
        Detect if manual script was run successfully on target.

        Tries WinRM access and updates status if successful.
        """
        status = self.get_status(target_id)
        if not status:
            return False

        # Try WinRM
        from autodbaudit.application.access_preparation.access_layers import (
            Layer1_WinRM,
        )

        layer = Layer1_WinRM(status.hostname, None, None)

        if layer.test_access():
            # Manual script worked! Update status
            self.mark_accessible(target_id, "Manual script verified working")
            return True

        return False

    def revert_all(self, targets: list[SqlTarget] | None = None) -> int:
        """
        Revert all access changes to original state.

        Args:
            targets: Optional list of targets (for credential lookup)

        Returns:
            Number of targets reverted
        """
        from autodbaudit.application.access_preparation.state_snapshot import (
            FullMachineState,
            StateRestorer,
        )

        statuses = self.get_all_status()
        reverted = 0

        for status in statuses:
            if not status.changes_made:
                logger.debug("No changes to revert for %s", status.target_id)
                continue

            logger.info("Reverting changes for %s", status.target_id)

            try:
                # Load saved state
                if status.original_snapshot and not status.original_snapshot.get(
                    "capture_failed"
                ):
                    machine_state = FullMachineState.from_json(
                        json.dumps(status.original_snapshot)
                    )
                    restorer = StateRestorer(machine_state)
                    actions = restorer.restore_local()
                    logger.info(
                        "Reverted %d actions for %s", len(actions), status.target_id
                    )
                    reverted += 1
                else:
                    logger.warning("No valid state to restore for %s", status.target_id)

            except Exception as e:
                logger.error("Failed to revert %s: %s", status.target_id, e)

        return reverted
