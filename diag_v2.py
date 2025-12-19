import os
import sys

with open(
    "c:/Users/sickp/source/SQLAuditProject/AutoDBAudit/diag_success.txt", "w"
) as f:
    f.write("Python is running!\n")
    f.write(f"CWD: {os.getcwd()}\n")
    f.write(f"Executable: {sys.executable}\n")
