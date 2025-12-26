# Persian/RTL Excel Reports

## Overview

AutoDBAudit can generate Persian (Farsi) Excel reports alongside English ones.
Use `--persian` flag with finalize to generate dual-language output.

## Usage

```bash
# Generate English + Persian reports
python main.py finalize --persian
```

This creates:
- `AuditReport.xlsx` (English)
- `AuditReport_fa.xlsx` (Persian/RTL)

## Font Installation

**Important**: Persian fonts must be installed on the viewing system for proper display.

### Included Fonts

The Field Kit includes two Persian fonts:
- `fonts/IRTitr.ttf` - For headings
- `fonts/IRNazanin.ttf` - For content

### Installing Fonts (Windows)

1. Open the `fonts/` folder in the Field Kit
2. Right-click each `.ttf` file
3. Select "Install for all users"
4. Restart Excel if it was open

### Verifying Installation

Open the Persian Excel file. If fonts display correctly, you'll see:
- Headers in **IRTitr** (bold, decorative)
- Content in **IRNazanin** (clean, readable)

If fonts show as squares or question marks, the fonts are not installed.

## What Gets Translated

| Item | Translated? | Notes |
|------|-------------|-------|
| Sheet names | ✅ | "Instances" → "نمونه‌ها" |
| Column headers | ✅ | "Server" → "سرور" |
| Dropdown options | ✅ | "High" → "بالا" |
| Status values | ✅ | "PASS" → "تأیید" |
| Conditional formatting | ✅ | Rules updated for Persian values |
| User notes | ❌ | Your text preserved as-is |
| Server names | ❌ | Technical values unchanged |
| Justifications | ❌ | Your documentation preserved |

## RTL Direction

Persian sheets are configured with:
- Right-to-left reading direction
- Right-aligned text
- Proper cell ordering

## Limitations

1. **Font embedding not supported** - openpyxl cannot embed fonts in Excel files
2. **Manual data untranslated** - Notes, justifications you write stay in original language
3. **Technical values unchanged** - Server names, IPs, config values remain English
