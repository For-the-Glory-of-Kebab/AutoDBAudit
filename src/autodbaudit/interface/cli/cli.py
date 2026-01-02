"""
CLI main entry point - Ultra-granular CLI interface.

This module provides the main entry point for the AutoDBAudit CLI,
delegating to the ultra-granular command orchestrator.
"""


def main() -> int:
    """
    Main entry point for AutoDBAudit CLI.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Import here to avoid circular imports
        from .orchestrator import app
        app()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
