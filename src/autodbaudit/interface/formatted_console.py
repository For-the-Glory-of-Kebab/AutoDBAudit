"""
Formatted Console Output - Rich Renderer for CLI.

This module provides a centralized way to render rich, colorful, and
consistent output for the CLI. It abstracts away ANSI codes and formatting details.
"""

from typing import Any
import os


class Colors:
    """ANSI Color Codes."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Text
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # Backgrounds
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


class Icons:
    """UTF-8 Icons."""

    CHECK = "✅"
    CROSS = "❌"
    WARN = "⚠️"
    INFO = "ℹ️"
    DOC = "📋"
    CHART = "📊"
    SERVER = "🖥️"
    DB = "🗄️"
    GEAR = "⚙️"
    LOCK = "🔒"
    USER = "👤"

    # Spinners / Status
    DOT = "●"
    ARROW = "➜"


class ConsoleRenderer:
    """Renders formatted output to the console."""

    def __init__(self, use_color: bool = True):
        self.use_color = use_color
        # Disable color if NO_COLOR env var is set or if not a TTY (optional logic)
        if os.environ.get("NO_COLOR"):
            self.use_color = False

    def _c(self, color_code: str) -> str:
        """Apply color if enabled."""
        return color_code if self.use_color else ""

    def header(self, title: str):
        """Render a major section header."""
        border = "━" * 60
        print(
            f"\n{self._c(Colors.CYAN)}{self._c(Colors.BOLD)}{title}{self._c(Colors.RESET)}"
        )
        print(f"{self._c(Colors.DIM)}{border}{self._c(Colors.RESET)}")

    def subheader(self, title: str):
        """Render a subsection header."""
        print(f"\n{self._c(Colors.BOLD)}{title}{self._c(Colors.RESET)}")
        print(f"{self._c(Colors.DIM)}{'-' * 40}{self._c(Colors.RESET)}")

    def info(self, message: str):
        """Render an info message."""
        print(f"{self._c(Colors.BLUE)}{Icons.INFO} {message}{self._c(Colors.RESET)}")

    def success(self, message: str):
        """Render a success message."""
        print(f"{self._c(Colors.GREEN)}{Icons.CHECK} {message}{self._c(Colors.RESET)}")

    def warning(self, message: str):
        """Render a warning message."""
        print(f"{self._c(Colors.YELLOW)}{Icons.WARN} {message}{self._c(Colors.RESET)}")

    def error(self, message: str):
        """Render an error message."""
        print(f"{self._c(Colors.RED)}{Icons.CROSS} {message}{self._c(Colors.RESET)}")

    def step(self, message: str):
        """Render a step in a process."""
        print(f"{self._c(Colors.CYAN)}{Icons.ARROW} {message}{self._c(Colors.RESET)}")

    def render_stats_card(self, stats: Any):
        """
        Render a beautiful statistics card.

        Args:
            stats: SyncStats object
        """
        # We perform a runtime check for attributes to handle SyncStats safely
        # Just in case an older version is passed.

        # Current State
        active = getattr(stats, "active_issues", 0)
        exceptions = getattr(stats, "documented_exceptions", 0)
        compliant = getattr(stats, "compliant_items", 0)
        # total variable removed (unused)

        # Changes Since Baseline
        fixed = getattr(stats, "fixed_since_baseline", 0)
        regressions = getattr(stats, "regressions_since_baseline", 0)
        new_issues = getattr(stats, "new_issues_since_baseline", 0)

        # Granular Exception Changes (Since Last)
        exc_added = getattr(stats, "exceptions_added_since_last", 0)
        exc_removed = getattr(stats, "exceptions_removed_since_last", 0)
        exc_updated = getattr(stats, "exceptions_updated_since_last", 0)

        # Granular Doc Changes (Since Last)
        docs_added = getattr(stats, "docs_added_since_last", 0)
        docs_updated = getattr(stats, "docs_updated_since_last", 0)
        docs_removed = getattr(stats, "docs_removed_since_last", 0)

        c = self._c
        colors = Colors

        self.header(f"{Icons.CHART} Audit Statistics Summary")

        # ROW 1: High Level Status
        print(f"{c(colors.BOLD)}Current Compliance State:{c(colors.RESET)}")
        print(
            f"  {Icons.CROSS} Active Issues:      {c(colors.RED)}{active:>5}{c(colors.RESET)}"
        )
        print(
            f"  {Icons.CHECK} Exceptions:         {c(colors.GREEN)}{exceptions:>5}{c(colors.RESET)}"
        )
        print(
            f"  {Icons.LOCK} Compliant Items:    {c(colors.GREEN)}{compliant:>5}{c(colors.RESET)}"
        )

        # ROW 2: Changes vs Baseline
        print(f"\n{c(colors.BOLD)}Since Baseline:{c(colors.RESET)}")
        print(
            f"  {Icons.CHECK} Fixed:              {c(colors.GREEN)}{fixed:>5}{c(colors.RESET)}"
        )
        if regressions > 0:
            print(
                f"  {Icons.CROSS} Regressions:        {c(colors.BG_RED)}{c(colors.WHITE)} {regressions:>3} {c(colors.RESET)}"
            )
        else:
            print(
                f"  {Icons.CROSS} Regressions:        {c(colors.DIM)}{0:>5}{c(colors.RESET)}"
            )

        if new_issues > 0:
            print(
                f"  {Icons.WARN} New Issues:         {c(colors.YELLOW)}{new_issues:>5}{c(colors.RESET)}"
            )
        else:
            print(
                f"  {Icons.WARN} New Issues:         {c(colors.DIM)}{0:>5}{c(colors.RESET)}"
            )

        # ROW 3: Recent Activity (Granular)
        # Only show this section if there's actually recent activity
        has_recent = (
            sum(
                [
                    exc_added,
                    exc_removed,
                    exc_updated,
                    docs_added,
                    docs_updated,
                    docs_removed,
                ]
            )
            > 0
        )

        if has_recent:
            print(
                f"\n{c(colors.BOLD)}{Icons.DOC} Recent Documentation Activity:{c(colors.RESET)}"
            )

            # Exceptions
            if exc_added > 0:
                print(
                    f"  + New Exceptions:     {c(colors.GREEN)}{exc_added}{c(colors.RESET)}"
                )
            if exc_removed > 0:
                print(
                    f"  - Exceptions Fixed:   {c(colors.CYAN)}{exc_removed}{c(colors.RESET)}"
                )
            if exc_updated > 0:
                print(
                    f"  ~ Exceptions Updated: {c(colors.YELLOW)}{exc_updated}{c(colors.RESET)}"
                )

            # Docs
            if docs_added > 0:
                print(
                    f"  + Notes Added:        {c(colors.GREEN)}{docs_added}{c(colors.RESET)}"
                )
            if docs_updated > 0:
                print(
                    f"  ~ Notes Updated:      {c(colors.YELLOW)}{docs_updated}{c(colors.RESET)}"
                )
            if docs_removed > 0:
                print(
                    f"  - Notes Removed:      {c(colors.RED)}{docs_removed}{c(colors.RESET)}"
                )
        else:
            print(
                f"\n{c(colors.DIM)}No recent documentation or exception changes detected.{c(colors.RESET)}"
            )

        print("")
