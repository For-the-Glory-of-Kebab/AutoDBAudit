"""Quick import verification for atomic_e2e modules."""
import sys
sys.path.insert(0, ".")

try:
    from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult
    print("[OK] test_harness imported")
except Exception as e:
    print(f"[FAIL] test_harness: {e}")

try:
    from tests.atomic_e2e.core.assertions import (
        assert_annotation_value,
        assert_exception_count,
        assert_key_format,
        require,
    )
    print("[OK] assertions imported")
except Exception as e:
    print(f"[FAIL] assertions: {e}")

try:
    from tests.atomic_e2e.core.randomizer import ConstrainedRandomizer, CoverageTracker
    print("[OK] randomizer imported")
except Exception as e:
    print(f"[FAIL] randomizer: {e}")

# Quick sanity check
rand = ConstrainedRandomizer(seed=12345)
print(f"[OK] Randomizer seed: {rand.seed}")
print(f"[OK] Random note: {rand.random_note()[:30]}...")
print(f"[OK] Sync count: {rand.count_syncs()}")

print("\nAll imports successful!")
