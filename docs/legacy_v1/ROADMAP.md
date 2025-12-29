# Feature Backlog & Testing Guidelines

## Testing Strategy (ALWAYS FOLLOW)

**Layered Test Pyramid - Run in order of scope:**
1. **L1-L2** (5-10s): Unit tests
2. **L3-L4** (30s): Integration  
3. **L5-L6** (2-3 min): E2E - before commits only

---

## MEDIUM PRIORITY - Future

### 1. Extended Merge Cells Logic
**Status**: Needs careful design before implementation.

---

## DONE BUT UNVERIFIED 🔄

### Persian Dual-Language Output (2025-12-26)
**Comprehensive i18n with full formatting preservation**

- `infrastructure/i18n/` package (6 files):
  - `sheets.py` - 25 sheet names translated
  - `headers.py` - 100+ column headers by sheet
  - `dropdowns.py` - All dropdown values (status, risk, change type)
  - `cover.py` - ALL cover page text (sections, labels, metadata)
  - `translator.py` - Main Translator + text() method
  - `rtl_excel.py` - RTL utilities
- `persian_generator.py` - Full transformation:
  - Cover sheet: translates all text, preserves icons (📊)
  - Other sheets: headers, dropdown values
  - CF rules: cleared and recreated with Persian values
  - Dropdowns: rebuilt with Persian options
  - Fonts preserved: bold, italic, size, color, underline, strike
  - Alignment preserved: wrap_text, horizontal, vertical
- CLI: `python main.py finalize --persian`
- Fonts: IRTitr (headings), IRNazanin (content) bundled in build
- 14 unit tests

### PSRemote pywinrm Implementation (2025-12-26)
- Multi-transport (HTTPS/HTTP), multi-auth (negotiate/kerberos/ntlm/basic)
- Connection caching, retry logic
- ScriptExecutor for bundled PS scripts

### Remediation Engine (2025-12-26)
- Jinja2 templates (SQL 2008 compatible)
- Aggressiveness levels, exception-aware
- 8 unit tests

---

## COMPLETED ✅

- [x] Access Preparation (8-layer strategy)
- [x] Default Instance Naming Check (Req 14)
- [x] Text Wrap for date/justification columns
- [x] Unicode/Persian name support (UTF-8)
- [x] Build manifest includes assets/scripts + fonts
- [x] Manual Action Log - Dropdowns + CF
