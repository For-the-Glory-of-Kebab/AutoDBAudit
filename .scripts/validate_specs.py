"""
Script to validate that sheet specifications match the Writer method signatures.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from autodbaudit.infrastructure.excel.writer import EnhancedReportWriter
from ultimate_e2e.sheet_specs.all_specs import ALL_SHEET_SPECS


def main():
    writer = EnhancedReportWriter()
    failures = []

    print("Validating Sheet Specs against Writer Methods...")
    print("-" * 60)

    for spec in ALL_SHEET_SPECS:
        if not spec.writer_method:
            continue

        method_name = spec.writer_method
        kwargs = spec.sample_kwargs

        print(f"Checking {spec.sheet_name} ({method_name})... ", end="")

        if not hasattr(writer, method_name):
            print("FAILED ❌")
            print(f"  Method '{method_name}' not found on EnhancedReportWriter")
            failures.append(spec.sheet_name)
            continue

        method = getattr(writer, method_name)

        try:
            method(**kwargs)
            print("OK ✅")
        except TypeError as e:
            print("FAILED ❌")
            print(f"  TypeError: {e}")
            failures.append(spec.sheet_name)
        except Exception as e:
            print("FAILED ❌")
            print(f"  Error: {e}")
            traceback.print_exc()
            failures.append(spec.sheet_name)

    print("-" * 60)
    if failures:
        print(f"Found {len(failures)} invalid specs:")
        for name in failures:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print("All specs are valid! 🎉")


if __name__ == "__main__":
    main()
