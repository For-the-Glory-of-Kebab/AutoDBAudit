# Linked Servers E2E Test Package
"""
Ultra-comprehensive E2E tests for Linked Servers Action Log.

This package contains:
- harness.py: Sheet-specific test harness
- test_exceptions.py: Exception lifecycle tests (E01-E12)
- test_transitions.py: State transition tests (T01-T11)
- test_combinations.py: Multi-step scenarios (C01-C04, M01-M02)
- test_edge_cases.py: Field validation and boundaries
- test_action_log.py: Column verification and idempotency
"""

from .harness import LinkedServersTestHarness

__all__ = ["LinkedServersTestHarness"]
