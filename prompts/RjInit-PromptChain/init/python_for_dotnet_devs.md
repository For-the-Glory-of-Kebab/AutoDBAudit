# Python for .NET Developers - Quick Reference

> **For the AutoDBAudit project**: A practical guide for .NET developers working in Python

---

## Mental Model Translation

### .NET → Python Equivalents

| .NET Concept | Python Equivalent | Notes |
|--------------|-------------------|-------|
| **Solution (.sln)** | Python project root directory | No single file, just directory structure |
| **Project (.csproj)** | Directory with `__init__.py` | Makes directory a package |
| **NuGet packages** | pip packages | Installed via `pip install` |
| **packages.config** | `requirements.txt` | Lists dependencies |
| **bin/Debug output** | `dist/` folder (PyInstaller) | After building executable |
| **namespace** | Python package/module | Directories with `__init__.py` |
| **using statement** | `import` statement | Import modules/packages |
| **class library (DLL)** | Python module (.py file) | Imported, not compiled separately |
| **MSBuild** | No equivalent (Python is interpreted) | PyInstaller for distribution |
| **Debug/Release config** | N/A (Python doesn't compile) | Can set via environment variables |
| **app.config / appsettings.json** | JSON config files | Load with `json.load()` |
| **var (type inference)** | All variables (Python is dynamically typed) | No type declarations needed |
| **null** | `None` | Python's null equivalent |
| **List<T>** | `list` (no generics, any type) | `my_list = [1, "two", 3.0]` |
| **Dictionary<K,V>** | `dict` | `my_dict = {"key": "value"}` |
| **LINQ** | List comprehensions, `filter()`, `map()` | `[x for x in items if x > 5]` |
| **async/await** | `async`/`await` (same syntax!) | Very similar to C# |
| **try/catch** | `try`/`except` | Almost identical |
| **IDisposable** | Context managers (`with` statement) | `with open(file) as f:` |

---

## Project Structure (Our Project)

### .NET Mental Model

```
Solution/
├── AutoDBAudit.sln
├── AutoDBAudit.Core/
│   ├── AutoDBAudit.Core.csproj
│   ├── SqlConnector.cs
│   └── AuditEngine.cs
├── AutoDBAudit.Remediation/
│   └── ScriptGenerator.cs
└── AutoDBAudit.CLI/
    └── Program.cs
```

### Python Equivalent (Our Project)

```
AutoDBAudit/                    # Solution root
├── src/                        # Like your project folders
│   ├── core/
│   │   ├── __init__.py        # Makes it a package
│   │   ├── sql_connector.py   # Like SqlConnector.cs
│   │   └── audit_engine.py    # Like AuditEngine.cs
│   ├── remediation/
│   │   ├── __init__.py
│   │   └── script_generator.py
│   └── utils/
│       └── ...
├── main.py                    # Entry point (like Program.cs)
├── requirements.txt           # Like packages.config
├── venv/                      # Virtual environment (like packages folder)
└── dist/                      # Build output (like bin/)
```

**Key Difference**: No solution/project files. Just directories with `__init__.py`.

---

## Package Management

### .NET (NuGet)

```bash
Install-Package Newtonsoft.Json
# or
dotnet add package Newtonsoft.Json
```

### Python (pip)

```bash
pip install openpyxl
# or install all from file
pip install -r requirements.txt
```

**Creating requirements.txt** (like exporting packages.config):

```bash
pip freeze > requirements.txt
```

---

## Virtual Environments (Critical Concept)

### Problem in .NET

Not really a problem - NuGet packages are project-scoped.

### Problem in Python

**Global package installation conflicts!** If you `pip install openpyxl==3.0` globally, it affects ALL Python projects.

### Solution: Virtual Environments (venv)

Think of it as **a local NuGet packages folder per project**.

```bash
# Create virtual environment (one-time per project)
python -m venv venv

# Activate it (EVERY time you work on project)
venv\Scripts\activate       # Windows
# or
source venv/bin/activate    # Linux/Mac

# Now pip installs go to THIS project only
pip install openpyxl

# Deactivate when done
deactivate
```

**CRITICAL for AutoDBAudit**: We'll use a clean venv for PyInstaller to avoid bundling unnecessary packages.

---

## Imports (using/namespace)

### .NET

```csharp
using System.Data.SqlClient;
using AutoDBAudit.Core;

namespace AutoDBAudit.Remediation {
    public class ScriptGenerator {
        SqlConnection conn;
    }
}
```

### Python

```python
import pyodbc                      # Like using System.Data
from src.core import sql_connector # Like using AutoDBAudit.Core

# No namespace declaration needed
class ScriptGenerator:
    def __init__(self):
        self.conn = None
```

**Common Import Patterns**:

```python
import os                          # Import module
from pathlib import Path           # Import specific class
import json as j                   # Alias (like using j = Newtonsoft.Json)
from openpyxl import Workbook      # Specific import
```

---

## Code Style Differences

### .NET (C#)

```csharp
public class SqlConnector {
    private string _connectionString;
    
    public SqlConnector(string connString) {
        _connectionString = connString;
    }
    
    public DataTable ExecuteQuery(string query) {
        using (var conn = new SqlConnection(_connectionString)) {
            conn.Open();
            // ...
        }
    }
}
```

### Python (PEP 8 Style)

```python
class SqlConnector:
    def __init__(self, conn_string):
        self._connection_string = conn_string  # _prefix = private by convention
    
    def execute_query(self, query):
        with pyodbc.connect(self._connection_string) as conn:  # Like using()
            cursor = conn.cursor()
            # ...
```

**Key Differences**:

- **No semicolons!**
- **Indentation matters** (no braces `{}`)
- **snake_case** for functions/variables (not camelCase)
- **PascalCase** for classes (same as C#)
- **No explicit access modifiers** (public/private) - use `_` prefix convention
- **No type declarations** (dynamic typing)

---

## Type Hints (Optional but Recommended)

Python 3.5+ supports type hints (like C# types):

```python
def execute_query(self, query: str) -> list[dict]:
    """Execute SQL query and return list of dictionaries."""
    # ...
    return results
```

**Benefits**:

- IDE autocomplete (like IntelliSense)
- Type checking (via `mypy` tool)
- Self-documenting code

**Not enforced at runtime** - just hints for developers/tools.

---

## Error Handling

### .NET

```csharp
try {
    ExecuteQuery("SELECT ...");
} catch (SqlException ex) {
    Console.WriteLine($"SQL Error: {ex.Message}");
} finally {
    conn.Close();
}
```

### Python

```python
try:
    execute_query("SELECT ...")
except pyodbc.Error as ex:
    print(f"SQL Error: {ex}")
finally:
    conn.close()
```

**Almost identical!** Just `except` instead of `catch`.

---

## Null Handling

### .NET

```csharp
string? name = GetName();
if (name != null) {
    Console.WriteLine(name.ToUpper());
}
```

### Python

```python
name = get_name()
if name is not None:  # Use 'is', not '=='
    print(name.upper())
```

**Key**: Use `is None` / `is not None`, not `== None`.

---

## String Formatting

### .NET (String Interpolation)

```csharp
string name = "Alice";
int age = 30;
Console.WriteLine($"Hello {name}, you are {age} years old");
```

### Python (f-strings, Python 3.6+)

```python
name = "Alice"
age = 30
print(f"Hello {name}, you are {age} years old")
```

**Identical syntax!** Use `f"..."` prefix.

---

## Collections & LINQ

### .NET (LINQ)

```csharp
var adults = people
    .Where(p => p.Age >= 18)
    .Select(p => p.Name)
    .ToList();
```

### Python (List Comprehensions)

```python
adults = [p.name for p in people if p.age >= 18]
```

**Or functional style**:

```python
adults = list(map(lambda p: p.name, filter(lambda p: p.age >= 18, people)))
```

**List comprehensions are idiomatic Python** (preferred).

---

## Common Gotchas for .NET Developers

### 1. **Indentation is Syntax**

```python
# WRONG
def foo():
print("Hello")  # IndentationError!

# CORRECT
def foo():
    print("Hello")  # 4 spaces indent
```

### 2. **Mutable Default Arguments**

```python
# DANGEROUS (like C# reference type default)
def add_item(item, items=[]):  # DON'T DO THIS
    items.append(item)
    return items

# SAFE
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 3. **Integer Division**

```python
# Python 3
5 / 2   # = 2.5 (float division)
5 // 2  # = 2 (integer division)

# C# equivalent
5 / 2   // = 2 (integer division if both ints)
5.0 / 2 // = 2.5
```

### 4. **No `++` operator**

```python
# C#: i++;
# Python:
i += 1  # No i++ or ++i
```

---

## AutoDBAudit-Specific Patterns

### Configuration Loading (.NET → Python)

```csharp
// C#
var config = JsonSerializer.Deserialize<AuditConfig>(
    File.ReadAllText("config.json")
);
```

```python
# Python
import json
with open("config.json", "r") as f:
    config = json.load(f)  # Returns dict
```

### SQL Execution (.NET → Python)

```csharp
// C# (Dapper/ADO.NET)
using (var conn = new SqlConnection(connString)) {
    var results = conn.Query<ServerInfo>("SELECT * FROM sys.servers");
}
```

```python
# Python (pyodbc)
import pyodbc
with pyodbc.connect(conn_string) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sys.servers")
    results = cursor.fetchall()  # Returns list of Row objects
```

### Excel Generation (.NET → Python)

```csharp
// C# (ClosedXML or EPPlus)
using (var workbook = new XLWorkbook()) {
    var worksheet = workbook.AddWorksheet("Sheet1");
    worksheet.Cell("A1").Value = "Hello";
    workbook.SaveAs("output.xlsx");
}
```

```python
# Python (openpyxl)
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws['A1'] = "Hello"
wb.save("output.xlsx")
```

**Very similar!**

---

## Quick Command Reference

```bash
# Create venv
python -m venv venv

# Activate venv
venv\Scripts\activate

# Install package
pip install package_name

# Install from requirements.txt
pip install -r requirements.txt

# Save current packages
pip freeze > requirements.txt

# Run Python file
python main.py

# Build executable (after PyInstaller installed)
pyinstaller --onefile main.py

# Deactivate venv
deactivate
```

---

**Remember**: Python is simpler than C# in many ways. Don't overthink it. When in doubt, the Pythonic way is usually the simpler way. 🐍
