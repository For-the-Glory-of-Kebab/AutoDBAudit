"""
Pytest fixtures for Robust E2E Tests.
"""

import pytest
import shutil
import os
import sys
import json
from pathlib import Path

# Ensure src is in python path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.e2e_robust import config


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up the test environment directories and config files."""
    # 1. Clean previous run
    if config.OUTPUT_DIR.exists():
        shutil.rmtree(config.OUTPUT_DIR)
    if config.CONFIG_DIR.exists():
        shutil.rmtree(config.CONFIG_DIR)

    # 2. Create directories
    config.OUTPUT_DIR.mkdir(parents=True)
    config.CONFIG_DIR.mkdir(parents=True)

    # 3. Create dummy sql_targets.json
    targets_data = [
        {
            "id": "t1",
            "server": config.SERVER_NAME,
            "instance": config.INSTANCE_NAME,
            "username": "sa",
            "password": "password",
            "enabled": True,
            "auth": "sql",
        }
    ]
    with open(config.TARGETS_FILE, "w") as f:
        json.dump({"targets": targets_data}, f)

    yield

    # Teardown (optional, maybe keep for inspection)
    # shutil.rmtree(config.TEST_ROOT)


@pytest.fixture
def mock_output_dir():
    """Return the configured output directory."""
    return config.OUTPUT_DIR
