---
trigger: always_on
---

# Engineering Standards
## Code Quality
- **Max file size**: 400 lines. (arbitrary and not set in stone, the smaller the better ) Split larger files into modules.
- **Python version**: 3.11+ features (type hints, dataclasses, walrus operator) (target up to 3.14 and 3.15 stuff)
- **File structure**: Clear package hierarchy with `__init__.py` exports
- **Interfaces**: Well-defined, documented interfaces between modules and sub-modules
- **No dead code**: Remove unused imports, functions, comments
## Architecture
- Domain-driven: `domain/`, `application/`, `infrastructure/`, `interface/`
- Single responsibility per module
- Dependency injection where appropriate
- Robust error handling with clear messages
- do as many folder and file hierarchies as you think helps readability, separation and tidyness.
- suggest and refine fitting architectures as we go
- god tier veteran modern python design patterns and architectures
## Naming
- default python conventions but with meaningful and profound ones for the files and the folders.
- consistent across all parts.
- Intuitive, descriptive names (no abbreviations)