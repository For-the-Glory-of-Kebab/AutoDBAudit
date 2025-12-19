"""Run exhaustive sheets test."""

import subprocess
import sys

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "tests/e2e_robust/test_exhaustive_sheets.py",
        "-v",
        "-s",
        "--tb=short",
    ],
    cwd=r"c:\Users\sickp\source\SQLAuditProject\AutoDBAudit",
    capture_output=True,
    text=True,
    check=False,
)

print("STDOUT:")
print(result.stdout[-15000:] if len(result.stdout) > 15000 else result.stdout)
print(f"\nReturn code: {result.returncode}")
