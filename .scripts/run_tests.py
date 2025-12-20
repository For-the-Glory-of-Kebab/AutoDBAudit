"""
Universal test runner wrapper script.

This script activates the venv and runs pytest to avoid command prompt issues.
Usage: python .scripts/run_tests.py [pytest args...]
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"


def main():
    # Build pytest command with any passed arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/", "-v", "--tb=short"]

    # Run pytest directly using venv python
    cmd = [str(VENV_PYTHON), "-m", "pytest"] + args

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
