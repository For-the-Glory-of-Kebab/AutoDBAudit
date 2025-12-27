"""
Real-DB Test Fixtures and Configuration.

Provides:
- RealDBTestContext: Main test context with SQL connections
- Fixtures for audit lifecycle (session, function scoped)
- Baseline management for pre-existing discrepancies
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Ensure src and tests are in path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup
from tests.real_db.contexts.real_db_context import RealDBTestContext
from tests.real_db.contexts.baseline_manager import BaselineManager
from tests.shared.helpers.cli import CLIRunner


# ═══════════════════════════════════════════════════════════════════════════
# MARKERS
# ═══════════════════════════════════════════════════════════════════════════


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "realdb: Tests requiring real SQL Server connection"
    )
    config.addinivalue_line("markers", "slow: Tests taking >30 seconds")


# ═══════════════════════════════════════════════════════════════════════════
# SESSION FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def config_dir(project_root: Path) -> Path:
    """Config directory with sql_targets.json."""
    return project_root / "config"


@pytest.fixture(scope="session")
def cli_runner(project_root: Path) -> CLIRunner:
    """CLI runner for executing commands."""
    return CLIRunner(project_root)


@pytest.fixture(scope="session")
def baseline_manager(project_root: Path) -> BaselineManager:
    """
    Baseline manager for pre-existing discrepancy handling.

    Captures baseline once per session.
    """
    manager = BaselineManager(project_root / "output" / "test_baseline.json")
    return manager


@pytest.fixture(scope="session")
def session_audit(cli_runner: CLIRunner, project_root: Path) -> dict:
    """
    Run audit ONCE per session and cache the result.

    This is the KEY OPTIMIZATION - instead of running audit for each test,
    we run it once and all tests share the result.

    Returns:
        dict with audit_id, excel_path, output
    """
    result = cli_runner.audit()

    # Find the Excel file
    output_dir = project_root / "output"
    excels = list(output_dir.glob("**/*.xlsx"))
    excels = [e for e in excels if "_fa" not in e.stem]
    excel_path = max(excels, key=lambda p: p.stat().st_mtime) if excels else None

    return {
        "audit_id": result.audit_id,
        "excel_path": excel_path,
        "output": result.output,
        "success": result.success,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FUNCTION FIXTURES
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Isolated temporary output directory for each test."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def real_db_ctx(
    project_root: Path,
    config_dir: Path,
    temp_output_dir: Path,
    baseline_manager: BaselineManager,
) -> Generator[RealDBTestContext, None, None]:
    """
    Real-DB test context with isolation.

    Each test gets:
    - Fresh output directory
    - Access to real SQL connections
    - Baseline tracking
    """
    ctx = RealDBTestContext(
        project_root=project_root,
        config_dir=config_dir,
        output_dir=temp_output_dir,
        baseline_manager=baseline_manager,
    )

    yield ctx

    ctx.cleanup()


# ═══════════════════════════════════════════════════════════════════════════
# SKIP CONDITIONS
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def sql_available() -> bool:
    """Check if SQL Server is available."""
    try:
        import pyodbc

        # Quick connection test could go here
        return True
    except ImportError:
        return False


def pytest_collection_modifyitems(config, items):
    """Add skip markers for realdb tests when SQL not available."""
    # Skip realdb tests if --no-realdb flag is set
    if config.getoption("--no-realdb", default=False):
        skip_realdb = pytest.mark.skip(reason="--no-realdb flag set")
        for item in items:
            if "realdb" in item.keywords:
                item.add_marker(skip_realdb)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--no-realdb",
        action="store_true",
        default=False,
        help="Skip tests requiring real SQL Server",
    )
