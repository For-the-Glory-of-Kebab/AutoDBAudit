import glob
import py_compile
import os

files = glob.glob("src/autodbaudit/infrastructure/excel/*.py")
print(f"Checking {len(files)} files...")

for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        print(f"❌ BROKEN: {os.path.basename(f)}")
        print(f"   {e}")
