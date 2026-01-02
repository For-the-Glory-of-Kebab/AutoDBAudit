"""
Root pytest configuration with markers for modular test execution.

Markers allow running subsets of tests:
    pytest -m unit           # Only atomic unit tests (< 5s)
    pytest -m component      # Single service tests (< 30s)
    pytest -m integration    # Multi-service tests (< 60s)
    pytest -m e2e            # Per-sheet E2E tests (< 120s)
    pytest -m scenario       # Complex scenario tests (slow)
    pytest -m "not slow"     # Everything except slow tests
    pytest -m sheet          # Per-sheet parametrized tests
"""

import sys
from pathlib import Path

# Ensure src is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Atomic unit tests (state machine, parsing)"
    )
    config.addinivalue_line(
        "markers", "component: Single service tests (annotation sync, stats)"
    )
    config.addinivalue_line("markers", "integration: Multi-service integration tests")
    config.addinivalue_line("markers", "e2e: Per-sheet end-to-end tests")
    config.addinivalue_line(
        "markers", "scenario: Complex scenario tests (multi-sync, errors)"
    )
    config.addinivalue_line("markers", "slow: Tests that take > 30 seconds")
    config.addinivalue_line("markers", "sheet: Per-sheet parametrized tests")
    config.addinivalue_line("markers", "finalize: Finalize/Definalize flow tests")
    config.addinivalue_line(
        "markers", "remediation: Remediation script generation tests"
    )
