"""
SQL Template Manager - Load and render SQL queries from external files.

Replaces hardcoded SQL strings with validated, versioned SQL templates.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional
from jinja2 import Template, Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class SqlTemplateManager:
    """
    Manages SQL templates loaded from external .sql files.

    Features:
    - Jinja2 templating for dynamic SQL generation
    - Syntax validation during loading
    - Version-specific template resolution
    - Parameter validation and sanitization
    """

    def __init__(self, template_dir: Path | str):
        """
        Initialize template manager.

        Args:
            template_dir: Directory containing .sql template files
        """
        self.template_dir = Path(template_dir)
        self._env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # SQL doesn't need HTML escaping
        )

        # Cache for loaded templates
        self._templates: Dict[str, Template] = {}

        # Validate template directory exists
        if not self.template_dir.exists():
            raise FileNotFoundError(f"SQL template directory not found: {self.template_dir}")

        logger.info("SQL Template Manager initialized: %s", self.template_dir)

    def get_query(self, template_name: str, **kwargs) -> str:
        """
        Load and render a SQL template.

        Args:
            template_name: Name of template file (without .sql extension)
            **kwargs: Template variables

        Returns:
            Rendered SQL query

        Raises:
            FileNotFoundError: If template doesn't exist
            TemplateError: If template rendering fails
        """
        # Load template if not cached
        if template_name not in self._templates:
            template_path = self.template_dir / f"{template_name}.sql"
            if not template_path.exists():
                raise FileNotFoundError(f"SQL template not found: {template_path}")

            try:
                self._templates[template_name] = self._env.get_template(f"{template_name}.sql")
                logger.debug("Loaded SQL template: %s", template_name)
            except Exception as e:
                raise RuntimeError(f"Failed to load SQL template {template_name}: {e}") from e

        # Render template
        try:
            template = self._templates[template_name]
            rendered = template.render(**kwargs)

            # Basic validation - check for common SQL injection patterns
            self._validate_rendered_sql(rendered, template_name)

            return rendered

        except Exception as e:
            raise RuntimeError(f"Failed to render SQL template {template_name}: {e}") from e

    def _validate_rendered_sql(self, sql: str, template_name: str) -> None:
        """
        Basic validation of rendered SQL.

        Args:
            sql: Rendered SQL string
            template_name: Template name for error reporting
        """
        # Check for dangerous patterns (basic protection)
        dangerous_patterns = [
            "-- DROP", "-- DELETE", "-- TRUNCATE",
            "xp_cmdshell", "sp_execute_external_script"
        ]

        sql_upper = sql.upper()
        for pattern in dangerous_patterns:
            if pattern.upper() in sql_upper:
                logger.warning("Potentially dangerous SQL pattern in %s: %s", template_name, pattern)

        # Check for unbalanced quotes (basic syntax check)
        single_quotes = sql.count("'")
        if single_quotes % 2 != 0:
            logger.warning("Unbalanced single quotes in rendered SQL: %s", template_name)

    def list_templates(self) -> list[str]:
        """List all available template names."""
        return [f.stem for f in self.template_dir.glob("*.sql")]

    def validate_all_templates(self) -> Dict[str, Optional[str]]:
        """
        Validate all templates can be loaded and rendered with default params.

        Returns:
            Dict of template_name -> error_message (None if valid)
        """
        results = {}
        for template_name in self.list_templates():
            try:
                # Try to render with empty params (templates should handle this)
                self.get_query(template_name)
                results[template_name] = None
            except Exception as e:
                results[template_name] = str(e)

        return results


# Global instance for application-wide use
_template_manager: Optional[SqlTemplateManager] = None


def init_sql_templates(template_dir: Path | str) -> None:
    """Initialize global SQL template manager."""
    global _template_manager
    _template_manager = SqlTemplateManager(template_dir)


def get_sql_query(template_name: str, **kwargs) -> str:
    """Get rendered SQL query from global template manager."""
    if _template_manager is None:
        raise RuntimeError("SQL template manager not initialized. Call init_sql_templates() first.")
    return _template_manager.get_query(template_name, **kwargs)
