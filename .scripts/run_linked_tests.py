"""Run linked servers tests with full output."""
import subprocess
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

# Ensure output dir exists
os.makedirs(PROJECT_ROOT / ".test_output", exist_ok=True)

result = subprocess.run(
    [str(VENV_PYTHON), "-m", "pytest", 
     "tests/atomic_e2e/sheets/test_linked_servers.py", 
     "-v", "--tb=short"],
    cwd=str(PROJECT_ROOT),
    capture_output=True,
    text=True,
    env={
        **os.environ,
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }
)

# Write full output to file
with open(PROJECT_ROOT / ".test_output" / "test_results.txt", "w") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)

print(f"Tests finished with exit code: {result.returncode}")
print(f"Full output written to .test_output/test_results.txt")

# Print summary
lines = result.stdout.splitlines()
for line in lines:
    if "passed" in line or "failed" in line or "error" in line.lower():
        print(line)
