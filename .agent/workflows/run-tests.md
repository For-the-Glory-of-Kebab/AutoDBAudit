---
description: Run tests autonomously using the venv wrapper
---
// turbo-all

Use the generic venv wrapper to run pytest. This avoids direct venv calls that trigger prompts.

To run all tests (excluding robust suite if needed):
```powershell
python .scripts/run_in_venv.py -m pytest tests/ --ignore=tests/e2e_robust -v --tb=short
```

To run a specific test file:
```powershell
python .scripts/run_in_venv.py -m pytest tests/ultimate_e2e/test_persistence.py -v
```

To run the full suite (if robust setup is fixed):
```powershell
python .scripts/run_in_venv.py -m pytest tests/ultimate_e2e/ -v
```
