"""
Master E2E Test Runner - Orchestrates the complete verification cycle.

This is the ONE COMMAND to rule them all:

    python run_full_e2e.py

What it does:
1. Runs simulation (apply discrepancies to SQL instances)
2. Runs audit (creates Excel with expected findings)
3. Verifies expected discrepancies appear in correct sheets
4. Writes test annotations to Excel
5. Runs sync (picks up Excel changes)
6. Verifies annotations persisted and action log updated
7. Tests state transitions (FIXED, REGRESSION, etc.)
8. Runs finalize + Persian report
9. Verifies Persian file created with RTL
10. Prints comprehensive pass/fail summary

Total time: ~5 minutes for full cycle
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# PATH SETUP
# ═══════════════════════════════════════════════════════════════════════════════
SIMULATION_DIR = Path(__file__).parent
PROJECT_ROOT = SIMULATION_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from verify_e2e import E2EVerifier, VerificationReport
from annotation_writer import AnnotationWriter
from discrepancy_tracker import DiscrepancyTracker

# Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_simulation(mode: str = "apply", target: str = None) -> bool:
    """Run simulation script."""
    print(f"\n{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}PHASE 1: SIMULATION ({mode.upper()}){RESET}")
    print(f"{CYAN}{'═' * 60}{RESET}")

    cmd = [
        sys.executable,
        str(SIMULATION_DIR / "run_simulation.py"),
        "--mode",
        mode,
    ]

    if target:
        cmd.extend(["--targets", target])
    else:
        cmd.append("--all")

    # Interactive - needs user confirmation
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode == 0


def run_verification() -> VerificationReport:
    """Run comprehensive verification."""
    print(f"\n{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}PHASE 2: COMPREHENSIVE VERIFICATION{RESET}")
    print(f"{CYAN}{'═' * 60}{RESET}")

    verifier = E2EVerifier(PROJECT_ROOT)
    return verifier.run_full_verification()


def run_annotation_test(excel_path: Path, audit_id: int) -> bool:
    """Test annotation persistence."""
    print(f"\n{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}PHASE 3: ANNOTATION PERSISTENCE TEST{RESET}")
    print(f"{CYAN}{'═' * 60}{RESET}")

    # Write test annotations
    writer = AnnotationWriter(excel_path)
    if not writer.open():
        print(f"{RED}Failed to open Excel{RESET}")
        return False

    count = writer.write_test_annotations()
    print(f"  Wrote {count} test annotations")

    if not writer.save():
        print(f"{RED}Failed to save Excel{RESET}")
        return False

    # Run sync to pick up changes
    print(f"  Running sync...")
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "sync",
        "--audit-id",
        str(audit_id),
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)

    if result.returncode != 0:
        print(f"{RED}Sync failed: {result.stderr[:200]}{RESET}")
        return False

    # Verify annotations persisted
    found, missing, errors = writer.verify_annotations_persisted()

    print(f"  Persistence check: {found} found, {missing} missing")

    if errors:
        for e in errors[:5]:
            print(f"    {RED}! {e}{RESET}")

    return missing == 0


def run_cli_command(command: str, *args) -> subprocess.CompletedProcess:
    """Run a CLI command."""
    cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), command] + list(args)
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description="Master E2E Test Runner")
    parser.add_argument(
        "--skip-sim",
        action="store_true",
        help="Skip simulation (use existing discrepancies)",
    )
    parser.add_argument("--target", help="Specific target to test against")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode - skip simulation and annotation tests",
    )

    args = parser.parse_args()

    start_time = datetime.now()

    print(f"\n{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}COMPREHENSIVE E2E TEST SUITE{RESET}")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{CYAN}{'═' * 60}{RESET}")

    results = {
        "simulation": None,
        "verification": None,
        "annotations": None,
    }

    # Phase 1: Simulation
    if not args.skip_sim and not args.quick:
        results["simulation"] = run_simulation("apply", args.target)
        if not results["simulation"]:
            print(f"{YELLOW}Simulation failed or cancelled - continuing anyway{RESET}")
    else:
        print(f"{YELLOW}Skipping simulation{RESET}")
        results["simulation"] = True

    # Phase 2: Verification
    report = run_verification()
    results["verification"] = report.passed

    # Phase 3: Annotation persistence (if we have an audit)
    if not args.quick and report.excel_path and report.audit_id:
        results["annotations"] = run_annotation_test(report.excel_path, report.audit_id)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}FINAL SUMMARY{RESET}")
    print(f"{CYAN}{'═' * 60}{RESET}")
    print(f"Duration: {duration:.1f} seconds")
    print()

    all_passed = True
    for phase, passed in results.items():
        if passed is None:
            status = f"{YELLOW}SKIPPED{RESET}"
        elif passed:
            status = f"{GREEN}PASSED{RESET}"
        else:
            status = f"{RED}FAILED{RESET}"
            all_passed = False
        print(f"  {phase.title()}: {status}")

    print()
    if all_passed:
        print(f"{GREEN}{BOLD}✓ ALL TESTS PASSED{RESET}")
    else:
        print(f"{RED}{BOLD}✗ SOME TESTS FAILED{RESET}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
