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
        Render a comprehensive statistics card.

        Shows:
        1. Current Compliance State
        2. Changes Since Baseline (initial audit)
        3. Changes Since Last Sync
        4. Sheet-by-Sheet Breakdown
        5. Recent Documentation Activity

        Args:
            stats: SyncStats object
        """
        # Current State
        active = getattr(stats, "active_issues", 0)
        exceptions = getattr(stats, "documented_exceptions", 0)
        compliant = getattr(stats, "compliant_items", 0)
        total = getattr(stats, "total_findings", 0)

        # Changes Since Baseline
        fixed_baseline = getattr(stats, "fixed_since_baseline", 0)
        regressions_baseline = getattr(stats, "regressions_since_baseline", 0)
        new_issues_baseline = getattr(stats, "new_issues_since_baseline", 0)
        exc_added_baseline = getattr(stats, "exceptions_added_since_baseline", 0)

        # Changes Since Last Sync
        fixed_last = getattr(stats, "fixed_since_last", 0)
        regressions_last = getattr(stats, "regressions_since_last", 0)
        new_issues_last = getattr(stats, "new_issues_since_last", 0)
        exc_added_last = getattr(stats, "exceptions_added_since_last", 0)
        exc_removed_last = getattr(stats, "exceptions_removed_since_last", 0)
        exc_updated_last = getattr(stats, "exceptions_updated_since_last", 0)

        # Granular Doc Changes (Since Last)
        docs_added = getattr(stats, "docs_added_since_last", 0)
        docs_updated = getattr(stats, "docs_updated_since_last", 0)
        docs_removed = getattr(stats, "docs_removed_since_last", 0)

        # Sheet-by-sheet breakdown
        sheet_stats = getattr(stats, "sheet_stats", {})

        c = self._c
        colors = Colors

        self.header(f"{Icons.CHART} Audit Statistics Summary")

        # ═══════════════════════════════════════════════════════════════
        # SECTION 1: Current Compliance State
        # ═══════════════════════════════════════════════════════════════
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
        if total > 0:
            print(f"  {c(colors.DIM)}Total Findings:      {total:>5}{c(colors.RESET)}")

        # ═══════════════════════════════════════════════════════════════
        # SECTION 2: Changes Since Baseline
        # ═══════════════════════════════════════════════════════════════
        print(f"\n{c(colors.BOLD)}📊 Since Baseline (Initial Audit):{c(colors.RESET)}")
        has_baseline_changes = (
            fixed_baseline > 0
            or regressions_baseline > 0
            or new_issues_baseline > 0
            or exc_added_baseline > 0
        )

        if has_baseline_changes:
            if fixed_baseline > 0:
                print(
                    f"  {Icons.CHECK} Fixed:              "
                    f"{c(colors.GREEN)}{fixed_baseline:>5}{c(colors.RESET)}"
                )
            if regressions_baseline > 0:
                print(
                    f"  {Icons.CROSS} Regressions:        "
                    f"{c(colors.BG_RED)}{c(colors.WHITE)} {regressions_baseline:>3} {c(colors.RESET)}"
                )
            if new_issues_baseline > 0:
                print(
                    f"  {Icons.WARN} New Issues:         "
                    f"{c(colors.YELLOW)}{new_issues_baseline:>5}{c(colors.RESET)}"
                )
            if exc_added_baseline > 0:
                print(
                    f"  {Icons.DOC} Exceptions Added:   "
                    f"{c(colors.CYAN)}{exc_added_baseline:>5}{c(colors.RESET)}"
                )
        else:
            print(f"  {c(colors.DIM)}No changes from baseline{c(colors.RESET)}")

        # ═══════════════════════════════════════════════════════════════
        # SECTION 3: Changes Since Last Sync
        # ═══════════════════════════════════════════════════════════════
        print(f"\n{c(colors.BOLD)}📈 Since Last Sync:{c(colors.RESET)}")
        has_last_changes = (
            fixed_last > 0
            or regressions_last > 0
            or new_issues_last > 0
            or exc_added_last > 0
            or exc_removed_last > 0
            or exc_updated_last > 0
        )

        if has_last_changes:
            if fixed_last > 0:
                print(
                    f"  {Icons.CHECK} Fixed:              "
                    f"{c(colors.GREEN)}{fixed_last:>5}{c(colors.RESET)}"
                )
            if regressions_last > 0:
                print(
                    f"  {Icons.CROSS} Regressions:        "
                    f"{c(colors.BG_RED)}{c(colors.WHITE)} {regressions_last:>3} {c(colors.RESET)}"
                )
            if new_issues_last > 0:
                print(
                    f"  {Icons.WARN} New Issues:         "
                    f"{c(colors.YELLOW)}{new_issues_last:>5}{c(colors.RESET)}"
                )
            if exc_added_last > 0:
                print(
                    f"  + Exceptions Added:   "
                    f"{c(colors.CYAN)}{exc_added_last:>5}{c(colors.RESET)}"
                )
            if exc_removed_last > 0:
                print(
                    f"  - Exceptions Removed: "
                    f"{c(colors.MAGENTA)}{exc_removed_last:>5}{c(colors.RESET)}"
                )
            if exc_updated_last > 0:
                print(
                    f"  ~ Exceptions Updated: "
                    f"{c(colors.YELLOW)}{exc_updated_last:>5}{c(colors.RESET)}"
                )
        else:
            print(f"  {c(colors.DIM)}No changes since last sync{c(colors.RESET)}")

        # ═══════════════════════════════════════════════════════════════
        # SECTION 4: Sheet-by-Sheet Breakdown (if any)
        # ═══════════════════════════════════════════════════════════════
        if sheet_stats:
            print(f"\n{c(colors.BOLD)}📋 By Sheet:{c(colors.RESET)}")
            for sheet_name, sheet_counts in sorted(sheet_stats.items()):
                # Get all stats for this sheet
                active = sheet_counts.get("active", 0)
                exceptions = sheet_counts.get("exceptions", 0)
                compliant = sheet_counts.get("compliant", 0)
                new_issues = sheet_counts.get("new_issues", 0)
                regressions = sheet_counts.get("regressions", 0)
                fixed = sheet_counts.get("fixed", 0)

                # Skip sheets with nothing interesting
                total_issues = active + exceptions + new_issues + regressions
                if total_issues == 0 and fixed == 0:
                    continue

                parts = []
                # Priority order: active issues first (bad), then exceptions, then changes
                if active > 0:
                    parts.append(f"{c(colors.RED)}{active} ⚠ active{c(colors.RESET)}")
                if exceptions > 0:
                    parts.append(
                        f"{c(colors.CYAN)}{exceptions} 📝 exc{c(colors.RESET)}"
                    )
                if regressions > 0:
                    parts.append(
                        f"{c(colors.RED)}{regressions} ↩ regress{c(colors.RESET)}"
                    )
                if new_issues > 0:
                    parts.append(
                        f"{c(colors.YELLOW)}{new_issues} 🆕 new{c(colors.RESET)}"
                    )
                if fixed > 0:
                    parts.append(f"{c(colors.GREEN)}{fixed} ✓ fixed{c(colors.RESET)}")
                # Only show compliant if there are no other interesting stats
                if compliant > 0 and len(parts) == 0:
                    parts.append(f"{c(colors.GREEN)}{compliant} ✓ ok{c(colors.RESET)}")

                if parts:
                    summary = ", ".join(parts)
                    print(f"  {Icons.DOC} {sheet_name}: {summary}")

        # ═══════════════════════════════════════════════════════════════
        # SECTION 5: Documentation Activity (Notes/Dates)
        # ═══════════════════════════════════════════════════════════════
        has_docs = docs_added > 0 or docs_updated > 0 or docs_removed > 0
        if has_docs:
            print(
                f"\n{c(colors.BOLD)}{Icons.DOC} Documentation Changes:{c(colors.RESET)}"
            )
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

        print("")
