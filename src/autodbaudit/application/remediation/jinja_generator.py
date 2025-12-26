"""
Jinja2-based Script Generator for Remediation.

Generates T-SQL and PowerShell remediation scripts using templates.
Supports:
- Aggressiveness levels (1=commented, 2=warning, 3=all active)
- Table variable approach for batch operations
- Exception-aware commenting with visual indicators
- Lockout prevention (never touch connecting user)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Template directory relative to this file
TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class RemediationItem:
    """Single remediation item for template rendering."""

    entity_name: str
    finding_type: str
    status: str
    description: str
    recommendation: str
    is_exceptionalized: bool = False
    justification: str = ""
    fix_sql: str = ""
    rollback_sql: str = ""
    risk_level: str = "medium"
    category: Literal["SAFE", "CAUTION", "REVIEW", "INFO"] = "SAFE"


@dataclass
class ScriptContext:
    """Context for script generation."""

    server_name: str
    instance_name: str
    port: int = 1433
    connecting_user: str | None = None
    aggressiveness: int = 1
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Grouped items by type
    items_by_type: dict[str, list[RemediationItem]] = field(default_factory=dict)

    def add_item(self, item: RemediationItem) -> None:
        """Add item to appropriate type group."""
        if item.finding_type not in self.items_by_type:
            self.items_by_type[item.finding_type] = []
        self.items_by_type[item.finding_type].append(item)

    @property
    def instance_label(self) -> str:
        """Get display label for instance."""
        if self.instance_name:
            return f"{self.server_name}\\{self.instance_name}"
        return f"{self.server_name}:{self.port}"


class JinjaScriptGenerator:
    """
    Jinja2-based script generator for remediation.

    Uses templates in templates/tsql/ and templates/powershell/.
    Implements table variable approach for batch operations.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize with template directory."""
        self.template_dir = template_dir or TEMPLATE_DIR

        # Ensure template directories exist
        (self.template_dir / "tsql").mkdir(parents=True, exist_ok=True)
        (self.template_dir / "powershell").mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["comment_sql"] = self._comment_sql
        self.env.filters["comment_ps"] = self._comment_ps
        self.env.filters["exception_wrap"] = self._exception_wrap

    def _comment_sql(self, text: str) -> str:
        """Comment out T-SQL code."""
        lines = text.split("\n")
        return "\n".join(f"-- {line}" if line.strip() else line for line in lines)

    def _comment_ps(self, text: str) -> str:
        """Comment out PowerShell code."""
        lines = text.split("\n")
        return "\n".join(f"# {line}" if line.strip() else line for line in lines)

    def _exception_wrap(
        self, item: RemediationItem, aggressiveness: int, for_ps: bool = False
    ) -> tuple[str, str]:
        """
        Get prefix/suffix for exception-aware wrapping.

        Returns (prefix, suffix) to wrap the fix code.
        """
        if not item.is_exceptionalized:
            return "", ""

        cmt = "#" if for_ps else "--"

        if aggressiveness >= 3:
            # Level 3: Just indicator, no commenting
            prefix = f"""
{cmt} ⚠️ EXCEPTIONALIZED: {item.entity_name}
{cmt} Justification: "{item.justification}"
"""
            return prefix, ""

        # Levels 1-2: Full commented block with visual markers
        prefix = f"""
{cmt} ╔══════════════════════════════════════════════════════════════════════════╗
{cmt} ║ ⚠️❌ EXCEPTIONALIZED: {item.entity_name}
{cmt} ╠══════════════════════════════════════════════════════════════════════════╣
{cmt} ║ ❌ COMMENTED OUT - This item has a documented exception!
{cmt} ║ ❌ Justification: "{item.justification[:60]}"
{cmt} ║ ❌ To apply anyway, uncomment the lines below:
{cmt} ╚══════════════════════════════════════════════════════════════════════════╝
"""
        return prefix, ""

    def generate_tsql_script(
        self,
        context: ScriptContext,
        output_path: Path,
    ) -> Path:
        """
        Generate main T-SQL remediation script.

        Uses table variable approach for batch operations.
        """
        template = self.env.get_template("tsql/main_script.sql.j2")

        content = template.render(
            ctx=context,
            aggressiveness=context.aggressiveness,
            connecting_user=context.connecting_user,
            generated_at=context.generated_at.isoformat(),
        )

        output_path.write_text(content, encoding="utf-8")
        logger.info("Generated T-SQL script: %s", output_path)
        return output_path

    def generate_ps_script(
        self,
        context: ScriptContext,
        output_path: Path,
    ) -> Path:
        """Generate PowerShell remediation script for OS-level fixes."""
        template = self.env.get_template("powershell/os_fixes.ps1.j2")

        content = template.render(
            ctx=context,
            aggressiveness=context.aggressiveness,
            generated_at=context.generated_at.isoformat(),
        )

        output_path.write_text(content, encoding="utf-8")
        logger.info("Generated PowerShell script: %s", output_path)
        return output_path
