# Triggers E2E Test Package
"""
E2E tests for Triggers sheet Action Log.

Validates that the extensible test framework works with
a completely different sheet structure.
"""

from .harness import TriggersTestHarness

__all__ = ["TriggersTestHarness"]
