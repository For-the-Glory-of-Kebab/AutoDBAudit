from typing import List, Optional, Dict
from pathlib import Path
import logging
from datetime import datetime

from autodbaudit.infrastructure.config.manager import ConfigManager
from autodbaudit.infrastructure.config.credential_manager import CredentialManager
from autodbaudit.application.prepare_service import PrepareService
from autodbaudit.domain.config import SqlTarget
from autodbaudit.infrastructure.psremoting.facade import ParallelRunner

logger = logging.getLogger(__name__)


class ApplyService:
    """Service for applying audit preparation to targets."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.credential_manager = CredentialManager(self.config_manager.repository)
        self.prepare_service = PrepareService(self.config_manager)

    def apply_targets(
        self,
        targets: Optional[List[str]] = None,
        config_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        parallel: bool = True,
        timeout: int = 300,
        dry_run: bool = False
    ) -> str:
        """
        Apply audit preparation to specified targets.

        Args:
            targets: List of target server names
            config_file: Path to configuration file
            credentials_file: Path to credentials file
            parallel: Whether to process in parallel
            timeout: Timeout per target in seconds
            dry_run: Whether to simulate without executing

        Returns:
            Success message or error message
        """
        try:
            # Load configuration
            if config_file:
                config_path = Path(config_file)
                if not config_path.exists():
                    return f"Configuration file not found: {config_file}"

                # Load config from file (simplified for now)
                self.config_manager.load_audit_config(force_reload=True)

            # Load credentials
            if credentials_file:
                creds_path = Path(credentials_file)
                if not creds_path.exists():
                    return f"Credentials file not found: {credentials_file}"

                # Load credentials from file (simplified for now)
                # self.credential_manager.load_from_file(creds_path)

            # Get SQL targets for the specified target names
            if targets is None:
                # Use all enabled targets from config
                all_targets = self.config_manager.get_enabled_targets()
                selected_targets = all_targets
                target_names = [t.name for t in selected_targets]
            else:
                # Use specified targets
                all_targets = self.config_manager.get_enabled_targets()
                selected_targets = [t for t in all_targets if t.name in targets]
                target_names = targets

            if not selected_targets:
                if targets is None:
                    return "No enabled targets found in sql_targets.json"
                else:
                    return f"No matching targets found for: {targets}"

            # Group targets by server for PS remoting (multiple instances on same server = 1 PS target)
            server_groups = self._group_targets_by_server(selected_targets)
            logger.info("Consolidated %d SQL targets into %d unique servers for PS remoting", len(selected_targets), len(server_groups))

            # Apply preparation using the prepare service (server-based, not target-based)
            results = []
            if parallel:
                runner = ParallelRunner(log_dir="output/prepare_logs")

                def _make_work(name: str, targets_on_server: List[SqlTarget]):
                    return (
                        name,
                        lambda facade: self._prepare_single(
                            name,
                            targets_on_server,
                            config_file,
                            credentials_file,
                            timeout,
                            dry_run,
                        ),
                    )

                work_items = [_make_work(server_name, targets) for server_name, targets in server_groups.items()]
                results = runner.run(work_items)
            else:
                for server_name, server_targets in server_groups.items():
                    server_result = self._prepare_single(
                        server_name,
                        server_targets,
                        config_file,
                        credentials_file,
                        timeout,
                        dry_run,
                    )
                    results.append(server_result)

            successful = sum(1 for r in results if r.success)
            total = len(results)

            if successful == total:
                return f"Successfully prepared {successful}/{total} servers"
            else:
                failed_servers = [f"{r.server_name}: {r.error_message}" for r in results if not r.success]
                return f"Prepared {successful}/{total} servers. Failed: {failed_servers}"

        except Exception as e:
            return f"Unexpected error during apply: {str(e)}"

    def _emit_result_log(self, result) -> None:
        """
        Write per-server log file for prepare run and log error details to console.
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        log_dir = Path("output") / "prepare_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        logfile = log_dir / f"{result.server_name}_{timestamp}.log"
        lines = result.logs if hasattr(result, "logs") else []
        try:
            with open(logfile, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
                if not result.success and result.error_message:
                    handle.write(f"\nERROR: {result.error_message}\n")
        except OSError as exc:
            logger.warning("Failed to write log for %s: %s", result.server_name, exc)

        if not result.success and result.error_message:
            logger.error("Prepare failed for %s: %s", result.server_name, result.error_message)
        elif result.success:
            logger.info("Prepare succeeded for %s", result.server_name)

    def _prepare_single(
        self,
        server_name: str,
        sql_targets: List[SqlTarget],
        config_file: Optional[str],
        credentials_file: Optional[str],
        timeout: int,
        dry_run: bool,
    ):
        result = self.prepare_service.prepare_server(
            server_name=server_name,
            sql_targets=sql_targets,
            config_file=config_file,
            credentials_file=credentials_file,
            timeout=timeout,
            dry_run=dry_run,
        )
        self._emit_result_log(result)
        return result

    def _group_targets_by_server(self, targets: List[SqlTarget]) -> Dict[str, List[SqlTarget]]:
        """
        Group SQL targets by server hostname/IP for PS remoting consolidation.

        Multiple SQL instances on the same server are treated as one PS remoting target
        since WinRM setup applies to the entire server, not individual instances.

        Args:
            targets: List of SQL targets

        Returns:
            Dictionary mapping server names to lists of targets on that server
        """
        from collections import defaultdict

        server_groups = defaultdict(list)

        for target in targets:
            # Use server hostname/IP as the key for grouping
            server_key = target.server
            server_groups[server_key].append(target)

        logger.debug("Grouped %d targets into %d server groups", len(targets), len(server_groups))
        for server, targets_on_server in server_groups.items():
            logger.debug("Server '%s': %d SQL targets", server, len(targets_on_server))

        return dict(server_groups)

