"""
Verification script for Refactoring Integrity.
Checks if Facades implement the expected methods and if Imports work.
"""

import sys
import inspect
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def log(msg, status="INFO"):
    print(f"[{status}] {msg}")


def check_audit_collector():
    log("Checking AuditDataCollector Facade...", "TEST")
    try:
        from autodbaudit.application.data_collector import AuditDataCollector

        # Instantiate with dummy args
        collector = AuditDataCollector("localhost", "sa", "password")
        log("Successfully instantiated AuditDataCollector", "PASS")

        # Check for key methods expected by AuditService
        # NOTE: Individual collect_* methods are now internal implementation details
        # encapsulated in sub-collectors. Only 'collect_all' is required by AuditService.
        expected_methods = ["collect_all"]

        for m in expected_methods:
            if hasattr(collector, m):
                log(f"Has method/property: {m}", "PASS")
            else:
                log(f"Missing method/property: {m}", "FAIL")
                return False

    except Exception as e:
        log(f"AuditDataCollector check failed: {e}", "FAIL")
        import traceback

        traceback.print_exc()
        return False
    return True


def check_remediation_service():
    log("Checking RemediationService Facade...", "TEST")
    try:
        # Check Facade Import
        from autodbaudit.application.remediation_service import (
            RemediationService as FacadeService,
        )
        from autodbaudit.application.remediation.service import (
            RemediationService as RealService,
        )

        if FacadeService is RealService:
            log("RemediationService Facade correctly aliases RealService", "PASS")
        else:
            log(
                "RemediationService Facade is NOT aliasing RealService directly (Inheritance?)",
                "INFO",
            )

        # Instantiate
        service = FacadeService(db_path=":memory:", output_dir="tmp_remediation")
        log("Successfully instantiated RemediationService", "PASS")

        # Check methods expected by CLI
        expected_methods = ["generate_scripts"]

        for m in expected_methods:
            if hasattr(service, m):
                log(f"Has method: {m}", "PASS")
            else:
                log(f"Missing method: {m}", "FAIL")
                return False

        # Inspect signature of generate_scripts
        sig = inspect.signature(service.generate_scripts)
        log(f"generate_scripts signature: {sig}", "INFO")
        # Expected: (audit_run_id=None, sql_targets=None, aggressiveness=1)

    except Exception as e:
        log(f"RemediationService check failed: {e}", "FAIL")
        import traceback

        traceback.print_exc()
        return False
    return True


if __name__ == "__main__":
    log("Starting Refactoring Integrity Verification...")

    ok_col = check_audit_collector()
    ok_rem = check_remediation_service()

    if ok_col and ok_rem:
        log("ALL INTEGRITY CHECKS PASSED", "SUCCESS")
        sys.exit(0)
    else:
        log("INTEGRITY CHECKS FAILED", "ERROR")
        sys.exit(1)
