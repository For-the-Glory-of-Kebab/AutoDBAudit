#!/usr/bin/env python
"""
Comprehensive Sync Verification Suite

Runs all sync-related tests and produces a summary report.
"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
os.environ["PYTHONPATH"] = str(src_dir)

SYNC_TESTS = [
    "tests/test_annotation_config.py",
    "tests/test_excel_parsing.py",
    "tests/test_actions_sheet.py",
    "tests/test_all_sheets_roundtrip.py",
    "tests/test_linked_servers_columns.py",
    "tests/test_rigorous_e2e.py",
    "tests/simulation_e2e.py",
    "tests/ultimate_e2e/test_sync_integrity.py",
]


def run_test(test_path):
    """Run a single test and return (passed, output)."""
    cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
    result = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
    return result.returncode == 0, result.stdout + result.stderr


def main():
    print("=" * 70)
    print("COMPREHENSIVE SYNC VERIFICATION SUITE")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = {}
    all_passed = True

    for test_path in SYNC_TESTS:
        full_path = project_root / test_path
        if not full_path.exists():
            print(f"\n[SKIP] {test_path} - File not found")
            results[test_path] = ("SKIP", "File not found")
            continue

        print(f"\n[TEST] {test_path}")
        print("-" * 50)

        passed, output = run_test(test_path)
        status = "PASS" if passed else "FAIL"
        results[test_path] = (status, output)

        if passed:
            print(f"[OK] {test_path} - PASSED")
        else:
            print(f"[!!] {test_path} - FAILED")
            print(output[-500:])  # Last 500 chars of output
            all_passed = False

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for test_path, (status, _) in results.items():
        icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "○"
        print(f"  {icon} {test_path}: {status}")

    passed_count = sum(1 for s, _ in results.values() if s == "PASS")
    total_count = len(results)

    print(f"\nResult: {passed_count}/{total_count} tests passed")

    if all_passed:
        print("\n[SUCCESS] All sync tests passed!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed. See output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
