#!/usr/bin/env python
"""
Autonomous Test Runner

This script runs tests without requiring interactive prompts.
It sets PYTHONPATH and runs pytest directly, capturing output.

Usage:
    python scripts/run_tests.py [test_path] [pytest_args...]

Examples:
    python scripts/run_tests.py                          # Run all tests
    python scripts/run_tests.py tests/test_annotation_config.py -v
    python scripts/run_tests.py tests/ultimate_e2e/ -v
"""
import os
import sys
import subprocess
from pathlib import Path

# Set PYTHONPATH to src directory
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
os.environ["PYTHONPATH"] = str(src_dir)


def main():
    # Default test path is all tests
    test_args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"] + test_args

    print(f"[Runner] PYTHONPATH={src_dir}")
    print(f"[Runner] Running: {' '.join(cmd)}")
    print("-" * 60)

    # Run pytest
    result = subprocess.run(cmd, cwd=str(project_root))

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
