#!/usr/bin/env python
"""Minimal test to verify the logic tests work."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

results = []

try:
    # Test 1: Import state machine
    from autodbaudit.domain.change_types import FindingStatus, ChangeType
    from autodbaudit.domain.state_machine import (
        is_exception_eligible,
        classify_finding_transition,
    )

    results.append("✅ Imports successful")

    # Test 2: FAIL + justification = exception
    assert is_exception_eligible(FindingStatus.FAIL, True, None) == True
    results.append("✅ FAIL + justification = exception")

    # Test 3: PASS + justification = NOT exception
    assert is_exception_eligible(FindingStatus.PASS, True, None) == False
    results.append("✅ PASS + justification = NOT exception")

    # Test 4: FAIL→PASS = FIXED
    trans = classify_finding_transition(FindingStatus.FAIL, FindingStatus.PASS)
    assert trans.change_type == ChangeType.FIXED
    results.append("✅ FAIL → PASS = FIXED")

    # Test 5: PASS→FAIL = REGRESSION
    trans = classify_finding_transition(FindingStatus.PASS, FindingStatus.FAIL)
    assert trans.change_type == ChangeType.REGRESSION
    results.append("✅ PASS → FAIL = REGRESSION")

    # Test 6: Exception persists
    trans = classify_finding_transition(
        FindingStatus.FAIL,
        FindingStatus.FAIL,
        old_has_exception=True,
        new_has_exception=True,
    )
    assert trans.change_type == ChangeType.STILL_FAILING
    results.append("✅ Exception persists = STILL_FAILING")

    results.append("\n" + "=" * 50)
    results.append("ALL 6 CORE LOGIC TESTS PASSED!")
    results.append("=" * 50)

except Exception as e:
    results.append(f"❌ ERROR: {e}")
    import traceback

    results.append(traceback.format_exc())

# Write to file
with open("logic_test_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

# Also print
for r in results:
    print(r)
