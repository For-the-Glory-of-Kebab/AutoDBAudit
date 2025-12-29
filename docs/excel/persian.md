# Persian (Farsi) / RTL Excel Reports (Specification)

Status: Spec-only; not yet implemented in production. This document captures the design and minimal verification steps required to implement dual-language Persian (RTL) output.

## Usage

- CLI: `finalize --persian` should produce `AuditReport_fa.xlsx` alongside the English report.

## Included Fonts (recommended)

- `IRTitr.ttf` - Headings
- `IRNazanin.ttf` - Body text

Installation (Windows): Copy `.ttf` files to `fonts/` in the distribution, right-click each `.ttf` and choose "Install for all users". Restart Excel if it was open.

## Behaviour

- Sheet names, headers, dropdown options, and status values are translated (e.g., "Instances" -> "نمونه‌ها").
- Conditional formatting rules are updated to reference translated values.
- Reading direction: Right-to-left; text alignment: right.
- Manual user-entered text (notes, justifications) remains in its original language.

## Limitations

- openpyxl cannot embed fonts; the target system must have the fonts installed to render correctly.
- Not all fields are translated (server names, IPs remain as-is).

## Tests (suggested)

- `test_cmd_persian.py`: verify `finalize --persian` produces the expected output files and that header rows are translated and right-aligned.
- Visual verification step: open `AuditReport_fa.xlsx` with Persian fonts installed and confirm headings/columns render correctly.

## Status & Next Steps

- Marked: Spec-only. Implementation notes and a small test harness are in the legacy backup branch for reference. Extract this spec to the implementation plan when ready to implement.
