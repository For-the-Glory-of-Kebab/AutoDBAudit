"""
Script Executor - Executes remediation SQL scripts against SQL Server.

Safety Features:
1. GO batch isolation - each batch executes separately
2. Credential protection - never modify the login used to connect
3. Extensive logging - every batch logged with result
4. Dry-run mode - validate without executing

Usage:
    executor = ScriptExecutor(targets_file="sql_targets.json")
    executor.execute_folder("output/remediation_scripts", dry_run=True)
    executor.execute_script("localhost_INTHEEND.sql")
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from autodbaudit.infrastructure.config_loader import ConfigLoader, SqlTarget

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of executing a single batch."""

    batch_num: int
    success: bool
    preview: str
    error: str | None = None
    rows_affected: int = 0


@dataclass
class ScriptResult:
    """Result of executing an entire script."""

    script_path: Path
    server: str
    instance: str
    total_batches: int
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    batch_results: list[BatchResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0


class ScriptExecutor:
    """
    Executes remediation SQL scripts with safety checks.

    Features:
    - GO batch isolation
    - Credential protection (won't modify connection login)
    - Dry-run mode
    - Extensive logging
    """

    def __init__(
        self,
        targets_file: str | Path = "sql_targets.json",
        db_path: str | Path = "output/audit_history.db",
    ):
        self.targets_file = Path(targets_file)
        self.db_path = Path(db_path)
        # Use config folder relative to CWD if default, or derive from file
        config_dir = (
            self.targets_file.parent
            if self.targets_file.parent.name == "config"
            else Path("config")
        )
        self.config_loader = ConfigLoader(str(config_dir))
        self._targets_cache: list[SqlTarget] | None = None

    def _load_targets(self) -> list[SqlTarget]:
        """Load SQL targets configuration."""
        if self._targets_cache is None:
            # Pass filename only, ConfigLoader handles directory
            fname = self.targets_file.name
            try:
                self._targets_cache = self.config_loader.load_sql_targets(fname)
            except Exception as e:
                logger.error("Failed to load targets: %s", e)
                # Ensure we have a list to avoid NoneType or errors later
                self._targets_cache = []
        return self._targets_cache

    def _find_target(
        self, server: str, port: int | None = None, instance: str | None = None
    ) -> SqlTarget | None:
        """
        Find target matching criteria with prioritization:
        1. Exact Match: Server + Port + Instance
        2. Server + Port
        3. Server + Instance
        4. Server + Default Port (1433/None)
        5. Server Only (First available)
        """
        targets = self._load_targets()
        server_norm = server.lower()
        instance_norm = instance.lower() if instance else None

        # Handle localhost aliases
        aliases = {server_norm}
        if server_norm in ("localhost", "127.0.0.1", "."):
            aliases = {"localhost", "127.0.0.1", "."}

        # 1. Exact Match: Server + Port + Instance (if all provided)
        if port and instance_norm is not None:
            for t in targets:
                h = t.server.lower()
                p = t.port or 1433
                i = (t.instance or "").lower()
                if h in aliases and p == port and i == instance_norm:
                    return t

        # 2. Server + Port
        if port:
            for t in targets:
                h = t.server.lower()
                p = t.port or 1433
                if h in aliases and p == port:
                    return t

        # 3. Server + Instance
        if instance_norm is not None:
            for t in targets:
                h = t.server.lower()
                i = (t.instance or "").lower()
                if h in aliases and i == instance_norm:
                    return t

        # 4. Server + Default Port (Implicit 1433)
        # If no port specified, we prefer the target on 1433 over others
        if not port:
            for t in targets:
                h = t.server.lower()
                p = t.port or 1433
                if h in aliases and p == 1433:
                    return t

        # 5. Fallback: Server partial match (FQDN) + Port/Instance logic
        if "." in server_norm:
            short_name = server_norm.split(".")[0]
            for t in targets:
                h = t.server.lower()
                if h == short_name:
                    # Apply similar logic checks if needed, or just return first FQDN match
                    # For safety, let's repeat the checks or just return it?
                    # Let's keep it simple: return if port matches or is default
                    p = t.port or 1433
                    # Same logic for port checking could apply here
                    if not port or (t.port or 1433) == port:
                        return t

        # 6. Fallback: First Server match (Lowest Priority)
        for t in targets:
            h = t.server.lower()
            if h in aliases:
                return t

        return None

    def _get_connection_for_script(
        self, script_path: Path
    ) -> tuple[str, str, str | None, int | None]:
        """
        Extract server/instance/port from script and find matching target.

        Returns: (server, instance, connection_login, port)
        """
        content = script_path.read_text(encoding="utf-8")

        # Parse server/instance/port from script header
        server_match = re.search(r"Server:\s*(.+)", content)
        instance_match = re.search(r"Instance:\s*(.+)", content)
        port_match = re.search(r"Port:\s*(\d+)", content)

        server = server_match.group(1).strip() if server_match else ""
        instance = instance_match.group(1).strip() if instance_match else ""

        port: int | None = None
        if port_match:
            try:
                port = int(port_match.group(1))
            except ValueError:
                pass

        # Handle "(Default)" or "(Default:1434)"
        # We KEEP the instance string for _find_target logic if it has info,
        # but we also want the cleaned version for the connection string later.
        # Actually, _find_target expects the REAL instance name ("" or "SQLEXPRESS").
        # So we should clean it, but extract port first.

        cleaned_instance = instance
        if instance.startswith("(Default"):
            # Try to extract port from instance label if not in header
            if not port and ":" in instance:
                try:
                    # Extract 1434 from (Default:1434)
                    inner = instance.strip("()")
                    _, p_str = inner.split(":", 1)
                    port = int(p_str)
                except (ValueError, IndexError):
                    pass

            # Default instance name is empty string
            cleaned_instance = ""

        # Find matching target with port AND instance awareness
        target = self._find_target(server, port, cleaned_instance)
        connection_login = None

        if target:
            if target.auth == "integrated":
                connection_login = "WINDOWS_AUTH"
            else:
                connection_login = target.username or "sa"

            # If we didn't have a port from script but found a target, use target's port
            if not port:
                port = target.port or 1433

        return server, cleaned_instance, connection_login, port

    def _parse_batches(self, content: str) -> list[str]:
        """Split script content into GO-separated batches."""
        # Split on GO that's on its own line
        batches = re.split(r"\n\s*GO\s*\n", content, flags=re.IGNORECASE)

        # Filter out empty batches and comment-only batches
        valid_batches = []
        for batch in batches:
            # Remove comments and check if there's actual SQL
            cleaned = re.sub(r"--.*$", "", batch, flags=re.MULTILINE)
            cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
            if cleaned.strip():
                valid_batches.append(batch.strip())

        return valid_batches

    def _check_credential_safety(
        self, batches: list[str], connection_login: str | None
    ) -> tuple[list[str], list[int]]:
        """
        Check if any batch would modify the connection login.

        Returns: (warnings, skip_batch_indices)
        """
        warnings: list[str] = []
        skip_indices: list[int] = []

        if not connection_login or connection_login == "WINDOWS_AUTH":
            return warnings, skip_indices

        # Patterns that modify logins
        alter_login_pattern = re.compile(
            r"ALTER\s+LOGIN\s+\[?" + re.escape(connection_login) + r"\]?", re.IGNORECASE
        )
        drop_login_pattern = re.compile(
            r"DROP\s+LOGIN\s+\[?" + re.escape(connection_login) + r"\]?", re.IGNORECASE
        )

        for i, batch in enumerate(batches):
            # Strip comments for safety check
            cleaned = re.sub(r"--.*$", "", batch, flags=re.MULTILINE)
            cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

            if alter_login_pattern.search(cleaned) or drop_login_pattern.search(
                cleaned
            ):
                warnings.append(
                    f"⚠️ SKIPPING batch {i+1}: Would modify connection login '{connection_login}'"
                )
                skip_indices.append(i)

        # Check for SA if connection is SA
        if connection_login.lower() == "sa":
            sa_pattern = re.compile(r"ALTER\s+LOGIN\s+\[?sa\]?", re.IGNORECASE)
            # rename_pattern = re.compile(r"WITH\s+NAME\s*=", re.IGNORECASE) # Unused var

            for i, batch in enumerate(batches):
                # Clean again or reuse cleaner logic if I refactored, but simple repeat is fine
                cleaned = re.sub(r"--.*$", "", batch, flags=re.MULTILINE)
                cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

                if sa_pattern.search(cleaned) and i not in skip_indices:
                    warnings.append(
                        f"⚠️ SKIPPING batch {i+1}: Would modify SA account (your connection login)"
                    )
                    skip_indices.append(i)

        return warnings, skip_indices

    def _get_batch_preview(self, batch: str, max_len: int = 80) -> str:
        """Get a short preview of a batch for logging."""
        # Find the first meaningful line
        for line in batch.split("\n"):
            line = line.strip()
            if line and not line.startswith("--") and not line.startswith("PRINT"):
                if len(line) > max_len:
                    return line[:max_len] + "..."
                return line
        return batch[:max_len] + "..." if len(batch) > max_len else batch

    def execute_folder(
        self,
        folder: str | Path,
        dry_run: bool = False,
        rollback: bool = False,
    ) -> list[ScriptResult]:
        """
        Execute all scripts in a folder.

        Args:
            folder: Path to folder containing .sql scripts
            dry_run: If True, only show what would be executed
            rollback: If True, execute _ROLLBACK.sql scripts instead
        """
        folder = Path(folder)
        if not folder.exists():
            logger.error("Folder not found: %s", folder)
            return []

        # Find scripts
        if rollback:
            scripts = sorted(folder.glob("*_ROLLBACK.sql"))
        else:
            scripts = sorted(
                s for s in folder.glob("*.sql") if "_ROLLBACK" not in s.name
            )

        if not scripts:
            logger.info("No scripts found in %s", folder)
            return []

        results = []
        print(f"\n{'='*60}")
        print(f"{'DRY RUN - ' if dry_run else ''}APPLY REMEDIATION")
        print(f"{'='*60}")
        print(f"Folder: {folder}")
        print(f"Scripts: {len(scripts)}")
        print(f"Mode: {'Rollback' if rollback else 'Remediation'}")
        print(f"{'='*60}\n")

        for script in scripts:
            result = self.execute_script(script, dry_run=dry_run)
            results.append(result)

        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        total_success = sum(1 for r in results if r.success)
        total_failed = len(results) - total_success
        print(
            f"Scripts: {len(results)} total, {total_success} successful, {total_failed} with errors"
        )

        for result in results:
            status = "✓" if result.success else "✗"
            print(
                f"  {status} {result.script_path.name}: {result.successful}/{result.total_batches} batches"
            )

        return results

    def execute_script(
        self,
        script_path: str | Path,
        dry_run: bool = False,
    ) -> ScriptResult:
        """
        Execute a single script.

        Args:
            script_path: Path to the .sql script
            dry_run: If True, only show what would be executed
        """
        script_path = Path(script_path)

        if not script_path.exists():
            logger.error("Script not found: %s", script_path)
            return ScriptResult(
                script_path=script_path,
                server="",
                instance="",
                total_batches=0,
                warnings=["Script file not found"],
            )

        print(f"\n--- Processing: {script_path.name} ---")

        # Read and parse script
        content = script_path.read_text(encoding="utf-8")
        batches = self._parse_batches(content)

        # Get connection info
        server, instance, connection_login, port = self._get_connection_for_script(
            script_path
        )

        print(f"Server: {server}")
        print(f"Port: {port or 1433}")
        print(f"Instance: {instance or '(Default)'}")
        print(f"Connection: {connection_login or 'Unknown'}")
        print(f"Batches: {len(batches)}")

        result = ScriptResult(
            script_path=script_path,
            server=server,
            instance=instance,
            total_batches=len(batches),
        )

        # Check credential safety
        warnings, skip_indices = self._check_credential_safety(
            batches, connection_login
        )
        result.warnings = warnings

        for warning in warnings:
            print(warning)

        if dry_run:
            print("\n[DRY RUN] Would execute the following batches:")
            for i, batch in enumerate(batches):
                if i in skip_indices:
                    print(f"  [{i+1:2d}] SKIP: {self._get_batch_preview(batch)}")
                    result.skipped += 1
                else:
                    print(f"  [{i+1:2d}] EXEC: {self._get_batch_preview(batch)}")
                    result.successful += 1  # Would succeed in dry-run
            return result

        # Actually execute
        try:
            conn = self._connect(server, instance, port)
        except Exception as e:
            logger.error("Failed to connect: %s", e)
            result.warnings.append(f"Connection failed: {e}")
            return result

        print("\nExecuting...")

        for i, batch in enumerate(batches):
            if i in skip_indices:
                result.skipped += 1
                result.batch_results.append(
                    BatchResult(
                        batch_num=i + 1,
                        success=True,
                        preview=self._get_batch_preview(batch),
                        error="SKIPPED: Would modify connection login",
                    )
                )
                print(f"  [{i+1:2d}] SKIP")
                continue

            try:
                cursor = conn.cursor()
                cursor.execute(batch)
                rows = cursor.rowcount
                # conn.commit() - AutoCommit is ON

                result.successful += 1
                result.batch_results.append(
                    BatchResult(
                        batch_num=i + 1,
                        success=True,
                        preview=self._get_batch_preview(batch),
                        rows_affected=rows,
                    )
                )
                print(f"  [{i+1:2d}] ✓ OK")

            except Exception as e:
                result.failed += 1
                error_msg = str(e)
                result.batch_results.append(
                    BatchResult(
                        batch_num=i + 1,
                        success=False,
                        preview=self._get_batch_preview(batch),
                        error=error_msg,
                    )
                )
                print(f"  [{i+1:2d}] ✗ FAILED: {error_msg[:60]}")
                logger.error("Batch %d failed: %s", i + 1, error_msg)

        conn.close()

        print(
            f"\nResult: {result.successful} succeeded, {result.failed} failed, {result.skipped} skipped"
        )

        return result

    def _connect(self, server: str, instance: str, port: int | None = None):
        """Create connection to SQL Server."""
        import pyodbc

        # Find matching target
        target = self._find_target(server, port)

        if not target:
            # Fallback if no target found but we have explicit info?
            # For safety, require target config
            raise ValueError(
                f"No target found for server: {server}"
                + (f" port {port}" if port else "")
            )

        # Build connection string
        host = target.server
        # Use target port if defined, otherwise passed port, otherwise 1433
        target_port = target.port or port or 1433

        if instance:
            server_str = f"{host}\\{instance}"
        else:
            server_str = f"{host},{target_port}"

        if target.auth == "integrated":
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_str};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
        else:
            username = target.username or "sa"
            password = target.password or ""
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_str};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
            )

        return pyodbc.connect(conn_str, autocommit=True)


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Execute remediation scripts")
    parser.add_argument("--folder", type=str, help="Folder containing scripts")
    parser.add_argument("--script", type=str, help="Single script to execute")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would execute"
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Execute rollback scripts"
    )
    parser.add_argument("--targets", default="sql_targets.json", help="Targets file")

    args = parser.parse_args()

    executor = ScriptExecutor(targets_file=args.targets)

    if args.folder:
        executor.execute_folder(
            args.folder, dry_run=args.dry_run, rollback=args.rollback
        )
    elif args.script:
        executor.execute_script(args.script, dry_run=args.dry_run)
    else:
        print("Specify --folder or --script")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
