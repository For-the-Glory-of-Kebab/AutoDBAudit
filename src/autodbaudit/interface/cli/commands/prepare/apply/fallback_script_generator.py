"""
Fallback script generator - Ultra-granular fallback script generation logic.

This module provides specialized functionality for generating PowerShell
fallback scripts when target preparation fails.
"""

import logging
from pathlib import Path
from typing import List

from autodbaudit.interface.cli.utils.powershell_generator import PowerShellScriptGenerator

logger = logging.getLogger(__name__)


class FallbackScriptGenerator:
    """Ultra-granular fallback script generation logic."""

    def __init__(self, script_generator: PowerShellScriptGenerator):
        self.script_generator = script_generator

    def generate_for_failures(self, results: List) -> None:
        """Generate fallback scripts for failed targets."""
        failed_targets = [r for r in results if not r.success]

        if not failed_targets:
            return

        print(f"\n[yellow]⚠️  {len(failed_targets)} target(s) failed preparation[/yellow]")
        print("[blue]📄 Generating PowerShell fallback scripts...[/blue]")

        scripts_dir = Path.cwd() / "generated_scripts"
        scripts_dir.mkdir(exist_ok=True)

        for result in failed_targets:
            try:
                script_path = self.script_generator.save_script_to_file(
                    result.target,
                    scripts_dir
                )
                self.script_generator.display_script_info(result.target, script_path)
            except Exception as e:
                logger.error("Failed to generate script for %s: %s", result.target.name, e)
                print(f"[red]❌ Failed to generate script for {result.target.name}: {e}[/red]")
