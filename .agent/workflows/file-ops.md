---
description: File operations within project (mkdir, copy, move, delete in repo)
---
// turbo-all

Safe file operations WITHIN the project directory only:

1. Create directories:
```powershell
New-Item -ItemType Directory -Path "TARGET_PATH" -Force | Out-Null
```

2. Copy files:
```powershell
Copy-Item "SOURCE" "DESTINATION" -Force
```

3. Move files within project:
```powershell
Move-Item "SOURCE" "DESTINATION" -Force
```

4. Delete files/folders in .test_workspace or output:
```powershell
Remove-Item "PATH" -Recurse -Force -ErrorAction SilentlyContinue
```

5. Create temp files for scripts:
```powershell
Set-Content -Path ".test_workspace\temp.py" -Value $code
```

All of these are SAFE when operating within the project root.
