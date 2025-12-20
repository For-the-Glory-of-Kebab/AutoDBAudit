"""Wrapper script to run ultimate E2E test."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

result = subprocess.run(
    [
        str(VENV_PYTHON),
        "-m",
        "pytest",
        "tests/test_ultimate_e2e.py",
        "-v",
        "-s",
        "--tb=short",
    ],
    cwd=str(PROJECT_ROOT),
    capture_output=False,
)
sys.exit(result.returncode)
