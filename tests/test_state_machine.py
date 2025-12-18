"""
Unit tests for the state machine and change types.

Tests all state transitions, edge cases, and counting logic.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import unittest
from autodbaudit.domain.change_types import (
    FindingStatus,
    ChangeType,
    ExceptionInfo,
)
from autodbaudit.domain.state_machine import (
    classify_finding_transition,
    classify_exception_change,
    resolve_concurrent_changes,
    is_exception_eligible,
    should_clear_exception_status,
)


class TestFindingStatus(unittest.TestCase):
    """Test FindingStatus enum methods."""
    
    def test_is_discrepant(self):
        """FAIL and WARN are discrepant, PASS is not."""
        self.assertTrue(FindingStatus.FAIL.is_discrepant())
        self.assertTrue(FindingStatus.WARN.is_discrepant())
        self.assertFalse(FindingStatus.PASS.is_discrepant())
    
    def test_from_string(self):
        """Test parsing various status formats."""
        self.assertEqual(FindingStatus.from_string("PASS"), FindingStatus.PASS)
        self.assertEqual(FindingStatus.from_string("pass"), FindingStatus.PASS)
        self.assertEqual(FindingStatus.from_string("FAIL"), FindingStatus.FAIL)
        self.assertEqual(FindingStatus.from_string("WARN"), FindingStatus.WARN)
        self.assertEqual(FindingStatus.from_string("✓"), FindingStatus.PASS)
        self.assertEqual(FindingStatus.from_string("❌"), FindingStatus.FAIL)
        self.assertIsNone(FindingStatus.from_string("unknown"))
        self.assertIsNone(FindingStatus.from_string(None))


class TestClassifyFindingTransition(unittest.TestCase):
    """Test the main transition classification function."""
    
    def test_fixed(self):
        """FAIL→PASS = Fixed."""
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.PASS,
        )
        self.assertEqual(result.change_type, ChangeType.FIXED)
        self.assertTrue(result.should_log)
    
    def test_fixed_from_warn(self):
        """WARN→PASS = Fixed."""
        result = classify_finding_transition(
            old_status=FindingStatus.WARN,
            new_status=FindingStatus.PASS,
        )
        self.assertEqual(result.change_type, ChangeType.FIXED)
    
    def test_regression(self):
        """PASS→FAIL = Regression."""
        result = classify_finding_transition(
            old_status=FindingStatus.PASS,
            new_status=FindingStatus.FAIL,
        )
        self.assertEqual(result.change_type, ChangeType.REGRESSION)
        self.assertTrue(result.should_log)
    
    def test_regression_to_warn(self):
        """PASS→WARN = Regression."""
        result = classify_finding_transition(
            old_status=FindingStatus.PASS,
            new_status=FindingStatus.WARN,
        )
        self.assertEqual(result.change_type, ChangeType.REGRESSION)
    
    def test_new_issue(self):
        """None→FAIL = New Issue."""
        result = classify_finding_transition(
            old_status=None,
            new_status=FindingStatus.FAIL,
        )
        self.assertEqual(result.change_type, ChangeType.NEW_ISSUE)
        self.assertTrue(result.should_log)
    
    def test_still_failing(self):
        """FAIL→FAIL with no exception change = Still Failing (no log)."""
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.FAIL,
            old_has_exception=False,
            new_has_exception=False,
        )
        self.assertEqual(result.change_type, ChangeType.STILL_FAILING)
        self.assertFalse(result.should_log)
    
    def test_exception_added(self):
        """FAIL→FAIL with new exception = Exception Added."""
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.FAIL,
            old_has_exception=False,
            new_has_exception=True,
        )
        self.assertEqual(result.change_type, ChangeType.EXCEPTION_ADDED)
        self.assertTrue(result.should_log)
    
    def test_exception_removed(self):
        """FAIL→FAIL with exception removed = Exception Removed."""
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.FAIL,
            old_has_exception=True,
            new_has_exception=False,
        )
        self.assertEqual(result.change_type, ChangeType.EXCEPTION_REMOVED)
        self.assertTrue(result.should_log)
    
    def test_instance_unavailable(self):
        """If instance wasn't scanned, don't falsely mark as fixed."""
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=None,  # Disappeared
            instance_was_scanned=False,  # But we couldn't reach it
        )
        self.assertEqual(result.change_type, ChangeType.UNKNOWN)
        self.assertFalse(result.should_log)
    
    def test_fix_clears_exception(self):
        """FAIL+Exception → PASS = Fixed (exception cleared automatically)."""
        result = classify_finding_transition(
            old_status=FindingStatus.FAIL,
            new_status=FindingStatus.PASS,
            old_has_exception=True,
            new_has_exception=False,
        )
        # Fix takes precedence
        self.assertEqual(result.change_type, ChangeType.FIXED)
    
    def test_no_change_pass_to_pass(self):
        """PASS→PASS = No Change."""
        result = classify_finding_transition(
            old_status=FindingStatus.PASS,
            new_status=FindingStatus.PASS,
        )
        self.assertEqual(result.change_type, ChangeType.NO_CHANGE)
        self.assertFalse(result.should_log)


class TestExceptionEligibility(unittest.TestCase):
    """Test exception eligibility checks."""
    
    def test_fail_with_justification_is_eligible(self):
        """FAIL + justification = eligible."""
        self.assertTrue(is_exception_eligible(
            status=FindingStatus.FAIL,
            has_justification=True,
            review_status=None,
        ))
    
    def test_fail_with_exception_status_is_eligible(self):
        """FAIL + review_status='Exception' = eligible."""
        self.assertTrue(is_exception_eligible(
            status=FindingStatus.FAIL,
            has_justification=False,
            review_status="Exception",
        ))
    
    def test_pass_with_justification_not_eligible(self):
        """PASS + justification = NOT eligible (it's just a note)."""
        self.assertFalse(is_exception_eligible(
            status=FindingStatus.PASS,
            has_justification=True,
            review_status=None,
        ))
    
    def test_pass_with_exception_status_not_eligible(self):
        """PASS + review_status='Exception' = NOT eligible."""
        self.assertFalse(is_exception_eligible(
            status=FindingStatus.PASS,
            has_justification=False,
            review_status="Exception",
        ))
    
    def test_fail_without_documentation_not_eligible(self):
        """FAIL without justification or status = NOT eligible."""
        self.assertFalse(is_exception_eligible(
            status=FindingStatus.FAIL,
            has_justification=False,
            review_status=None,
        ))


class TestShouldClearExceptionStatus(unittest.TestCase):
    """Test clearing invalid exception status."""
    
    def test_pass_with_exception_status_should_clear(self):
        """PASS + 'Exception' dropdown = should clear."""
        self.assertTrue(should_clear_exception_status(
            status=FindingStatus.PASS,
            review_status="Exception",
        ))
    
    def test_fail_with_exception_status_should_not_clear(self):
        """FAIL + 'Exception' dropdown = should NOT clear."""
        self.assertFalse(should_clear_exception_status(
            status=FindingStatus.FAIL,
            review_status="Exception",
        ))
    
    def test_pass_with_other_status_should_not_clear(self):
        """PASS + 'Needs Review' = should NOT clear."""
        self.assertFalse(should_clear_exception_status(
            status=FindingStatus.PASS,
            review_status="Needs Review",
        ))


class TestResolveConcurrentChanges(unittest.TestCase):
    """Test priority resolution when multiple changes detected."""
    
    def test_fix_wins_over_exception(self):
        """If both Fixed and Exception detected, Fixed wins."""
        from autodbaudit.domain.change_types import TransitionResult, ActionStatus
        
        fixed = TransitionResult(
            change_type=ChangeType.FIXED,
            should_log=True,
            action_status=ActionStatus.CLOSED,
        )
        exception = TransitionResult(
            change_type=ChangeType.EXCEPTION_ADDED,
            should_log=True,
            action_status=ActionStatus.EXCEPTION,
        )
        
        result = resolve_concurrent_changes([exception, fixed])
        self.assertEqual(result.change_type, ChangeType.FIXED)
    
    def test_single_change_returned_as_is(self):
        """Single change is returned directly."""
        from autodbaudit.domain.change_types import TransitionResult, ActionStatus
        
        fixed = TransitionResult(
            change_type=ChangeType.FIXED,
            should_log=True,
            action_status=ActionStatus.CLOSED,
        )
        
        result = resolve_concurrent_changes([fixed])
        self.assertEqual(result.change_type, ChangeType.FIXED)


class TestExceptionChange(unittest.TestCase):
    """Test exception change detection."""
    
    def test_exception_added(self):
        """Detect new exception."""
        old = None
        new = ExceptionInfo(
            entity_key="test",
            has_justification=True,
            justification_text="Test reason",
        )
        result = classify_exception_change(old, new, FindingStatus.FAIL)
        self.assertEqual(result.change_type, ChangeType.EXCEPTION_ADDED)
    
    def test_exception_updated(self):
        """Detect updated exception (text changed)."""
        old = ExceptionInfo(
            entity_key="test",
            has_justification=True,
            justification_text="Old reason",
        )
        new = ExceptionInfo(
            entity_key="test",
            has_justification=True,
            justification_text="New reason",
        )
        result = classify_exception_change(old, new, FindingStatus.FAIL)
        self.assertEqual(result.change_type, ChangeType.EXCEPTION_UPDATED)
    
    def test_exception_on_pass_is_no_change(self):
        """Exception on PASS row = no valid change."""
        new = ExceptionInfo(
            entity_key="test",
            has_justification=True,
        )
        result = classify_exception_change(None, new, FindingStatus.PASS)
        self.assertEqual(result.change_type, ChangeType.NO_CHANGE)


if __name__ == "__main__":
    unittest.main()
