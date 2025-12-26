"""
CLI Runner - Execute CLI commands with output parsing.

Uses wrapper scripts per no-prompts.md workflow.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CLIResult:
    """Parsed CLI command result."""

    exit_code: int
    stdout: str
    stderr: str
    command: list[str] = field(default_factory=list)
    audit_id: int | None = None
    stats: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Combined output."""
        return self.stdout + self.stderr


class CLIRunner:
    """
    Execute CLI commands via wrapper scripts.

    Follows no-prompts.md:
    - Uses scripts/run.ps1 for CLI
    - No pipes, no semicolons
    - No python -c or python -m
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.run_script = project_root / "scripts" / "run.ps1"

    def run(self, *args: str, timeout: int = 300) -> CLIResult:
        """
        Run CLI command.

        Args:
            *args: CLI arguments (e.g., "audit", "sync", "--audit-id", "1")
            timeout: Maximum seconds to wait

        Returns:
            CLIResult with parsed output
        """
        cmd = ["powershell", "-File", str(self.run_script)] + list(args)

        result = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        cli_result = CLIResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=cmd,
        )

        # Parse audit ID
        cli_result.audit_id = self._parse_audit_id(result.stdout)

        # Parse stats
        cli_result.stats = self._parse_stats(result.stdout)

        return cli_result

    def audit(self) -> CLIResult:
        """Run audit command."""
        return self.run("audit")

    def sync(self, audit_id: int) -> CLIResult:
        """Run sync command."""
        return self.run("sync", "--audit-id", str(audit_id))

    def finalize(self, audit_id: int, persian: bool = False) -> CLIResult:
        """Run finalize command."""
        args = ["finalize", "--audit-id", str(audit_id)]
        if persian:
            args.append("--persian")
        return self.run(*args)

    def definalize(self, audit_id: int) -> CLIResult:
        """Run definalize command."""
        return self.run("definalize", "--audit-id", str(audit_id))

    def status(self) -> CLIResult:
        """Run status command."""
        return self.run("status")

    def _parse_audit_id(self, output: str) -> int | None:
        """Extract audit ID from output."""
        match = re.search(r"Audit ID:\s*(\d+)", output)
        return int(match.group(1)) if match else None

    def _parse_stats(self, output: str) -> dict:
        """Parse statistics from sync output."""
        stats = {}
        patterns = {
            "fixed": r"Fixed:\s*(\d+)",
            "regressions": r"Regressions?:\s*(\d+)",
            "new_issues": r"New Issues?:\s*(\d+)",
            "exceptions": r"Exceptions?:\s*(\d+)",
            "active_issues": r"Active Issues?:\s*(\d+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                stats[key] = int(match.group(1))

        return stats
