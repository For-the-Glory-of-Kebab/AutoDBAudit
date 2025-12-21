"""
Controlled Randomizer for Atomic E2E Tests.

Provides constrained randomization with GUARANTEED coverage.

Key Principle: Random variations WITHIN guaranteed bounds.
- Never 0 exceptions tested
- Never 0 syncs  
- Always hits all required combinations
"""

from __future__ import annotations

import logging
import random
import string
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CoverageTracker:
    """
    Tracks what the randomizer covered to ensure completeness.
    """
    
    coverage: dict[str, int] = field(default_factory=lambda: {
        "fail_with_justification": 0,
        "fail_with_status": 0,
        "fail_with_both": 0,
        "fail_no_exception": 0,
        "pass_with_note": 0,
        "pass_clean": 0,
        "syncs_run": 0,
        "modifications": 0,
    })
    
    def record(self, category: str, count: int = 1):
        """Record coverage of a category."""
        if category in self.coverage:
            self.coverage[category] += count
        else:
            self.coverage[category] = count
            
    def validate(self) -> list[str]:
        """
        Validate minimum coverage was achieved.
        
        Returns:
            List of validation errors (empty if all pass)
        """
        errors = []
        
        # Must test at least one of each exception trigger
        if self.coverage["fail_with_justification"] < 1:
            errors.append("Must test FAIL + justification at least once")
            
        if self.coverage["fail_with_status"] < 1:
            errors.append("Must test FAIL + status at least once")
            
        if self.coverage["pass_with_note"] < 1:
            errors.append("Must test PASS + note at least once")
            
        if self.coverage["syncs_run"] < 2:
            errors.append("Must run at least 2 sync cycles")
            
        return errors
        
    def summary(self) -> str:
        """Get coverage summary."""
        return ", ".join(f"{k}={v}" for k, v in self.coverage.items())


class ConstrainedRandomizer:
    """
    Controlled randomization with GUARANTEED coverage.
    
    Usage:
        rand = ConstrainedRandomizer(seed=12345)  # Reproducible
        
        # Get random count within bounds
        num_exceptions = rand.count_exceptions()  # 2-5
        
        # Get random rows
        rows = rand.select_rows([2, 3, 4, 5, 6], count=3)
        
        # Generate random text
        note = rand.random_note()
    """
    
    # === CONSTRAINTS ===
    MIN_EXCEPTIONS_TO_TEST = 2
    MAX_EXCEPTIONS_TO_TEST = 5
    MIN_SYNCS = 2
    MAX_SYNCS = 5
    MIN_ROWS_MODIFIED = 2
    MAX_ROWS_MODIFIED = 8
    
    def __init__(self, seed: int | None = None):
        """
        Initialize randomizer.
        
        Args:
            seed: Random seed for reproducibility. If None, uses current time.
        """
        self.seed = seed if seed is not None else int(time.time())
        self.rng = random.Random(self.seed)
        self.tracker = CoverageTracker()
        
        self._log_seed()
        
    def _log_seed(self):
        """Log seed for reproducibility."""
        logger.info(f"[RANDOMIZER] Seed={self.seed} - save this to reproduce!")
        
    # === COUNT GENERATORS ===
    
    def count_exceptions(self) -> int:
        """Random exception count with guaranteed minimum."""
        return self.rng.randint(
            self.MIN_EXCEPTIONS_TO_TEST,
            self.MAX_EXCEPTIONS_TO_TEST
        )
        
    def count_syncs(self) -> int:
        """Random sync count with guaranteed minimum."""
        return self.rng.randint(self.MIN_SYNCS, self.MAX_SYNCS)
        
    def count_rows(self, available: int) -> int:
        """Random row count within bounds."""
        max_rows = min(self.MAX_ROWS_MODIFIED, available)
        min_rows = min(self.MIN_ROWS_MODIFIED, max_rows)
        return self.rng.randint(min_rows, max_rows)
        
    # === ROW SELECTION ===
    
    def select_rows(
        self,
        available: list[int],
        count: int | None = None,
    ) -> list[int]:
        """
        Select random rows from available.
        
        Args:
            available: List of available row numbers
            count: How many to select (random if None)
            
        Returns:
            List of selected row numbers
        """
        if not available:
            return []
            
        if count is None:
            count = self.count_rows(len(available))
            
        count = min(count, len(available))
        return self.rng.sample(available, count)
        
    def split_rows(
        self,
        available: list[int],
        categories: list[str],
    ) -> dict[str, list[int]]:
        """
        Split available rows into categories.
        
        Args:
            available: List of available row numbers
            categories: List of category names
            
        Returns:
            Dict of category -> row list
        """
        result = {cat: [] for cat in categories}
        
        # Shuffle rows
        rows = available.copy()
        self.rng.shuffle(rows)
        
        # Distribute evenly-ish
        for i, row in enumerate(rows):
            cat = categories[i % len(categories)]
            result[cat].append(row)
            
        return result
        
    # === TEXT GENERATORS ===
    
    def random_note(self, min_len: int = 10, max_len: int = 50) -> str:
        """Generate random note text."""
        length = self.rng.randint(min_len, max_len)
        words = [
            "test", "note", "documented", "verified", "checked",
            "approved", "reviewed", "legacy", "temporary", "exception",
            "valid", "confirmed", "pending", "needs", "review"
        ]
        parts = [self.rng.choice(words) for _ in range(length // 5 + 1)]
        result = " ".join(parts)
        
        # Add unique identifier
        unique_id = "".join(self.rng.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{result} [{unique_id}]"
        
    def random_justification(self) -> str:
        """Generate random justification text."""
        prefixes = [
            "Business justification:",
            "Approved by:",
            "Exception reason:",
            "Per policy:",
            "Legacy system:",
        ]
        suffix = self.random_note(20, 80)
        return f"{self.rng.choice(prefixes)} {suffix}"
        
    def random_date(self, days_back: int = 365) -> str:
        """Generate random date string."""
        days = self.rng.randint(0, days_back)
        dt = datetime.now() - timedelta(days=days)
        
        # Random format
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d-%b-%Y",
        ]
        return dt.strftime(self.rng.choice(formats))
        
    # === DECISION MAKERS ===
    
    def should(self, probability: float = 0.5) -> bool:
        """Random boolean with given probability."""
        return self.rng.random() < probability
        
    def pick(self, options: list) -> Any:
        """Pick random item from list."""
        return self.rng.choice(options) if options else None
        
    # === COVERAGE HELPERS ===
    
    def ensure_coverage(
        self,
        fail_rows: list[int],
        pass_rows: list[int],
    ) -> dict[str, list[tuple[int, str, str]]]:
        """
        Generate test plan ensuring coverage of all combinations.
        
        Returns:
            Dict of category -> list of (row, col, value) tuples
        """
        plan = {
            "fail_with_justification": [],
            "fail_with_status": [],
            "fail_with_both": [],
            "pass_with_note": [],
        }
        
        # Ensure at least one of each type
        if fail_rows:
            # Justification only
            row = fail_rows[0] if len(fail_rows) > 0 else None
            if row:
                plan["fail_with_justification"].append(
                    (row, "Justification", self.random_justification())
                )
                self.tracker.record("fail_with_justification")
                
            # Status only
            row = fail_rows[1] if len(fail_rows) > 1 else None
            if row:
                plan["fail_with_status"].append(
                    (row, "Review Status", "Exception")
                )
                self.tracker.record("fail_with_status")
                
            # Both
            row = fail_rows[2] if len(fail_rows) > 2 else None
            if row:
                plan["fail_with_both"].append(
                    (row, "Justification", self.random_justification())
                )
                plan["fail_with_both"].append(
                    (row, "Review Status", "Exception")
                )
                self.tracker.record("fail_with_both")
                
        if pass_rows:
            # Pass with note
            row = pass_rows[0] if len(pass_rows) > 0 else None
            if row:
                plan["pass_with_note"].append(
                    (row, "Justification", self.random_justification())
                )
                self.tracker.record("pass_with_note")
                
        return plan
        
    def validate_coverage(self) -> None:
        """Validate coverage was achieved, raise if not."""
        errors = self.tracker.validate()
        if errors:
            raise AssertionError(
                f"Coverage validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )


# Type alias for Any to avoid import
from typing import Any
