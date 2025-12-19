---
description: Run any Python command in venv without prompting
---
// turbo-all

Execute Python in the project venv - all variations are safe:

1. One-liner:
```powershell
.\venv\Scripts\python.exe -c "print('hello')"
```

2. Run a module:
```powershell
.\venv\Scripts\python.exe -m MODULE_NAME ARGS
```

3. Run a script file:
```powershell
.\venv\Scripts\python.exe SCRIPT.py
```

4. Run pytest:
```powershell
.\venv\Scripts\python.exe -m pytest ARGS
```

5. Run src.main:
```powershell
.\venv\Scripts\python.exe -m src.main ARGS
```

All Python execution within venv is SAFE to auto-run.
