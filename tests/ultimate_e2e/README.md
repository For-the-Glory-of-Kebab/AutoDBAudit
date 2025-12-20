# Ultimate E2E Test Suite

This directory contains the comprehensive, modular E2E test suite for the sync engine.

## Architecture

```
tests/ultimate_e2e/
├── __init__.py
├── conftest.py              # Shared fixtures and test infrastructure
├── sheet_specs/             # Per-sheet test specifications
│   ├── __init__.py
│   ├── base.py              # Base SheetSpec class
│   ├── cover.py             # 1. Cover sheet spec
│   ├── instances.py         # 2. Instances sheet spec
│   ├── sa_account.py        # 3. SA Account sheet spec
│   ├── ... (all 20 sheets)
│   └── actions.py           # 20. Actions sheet spec
├── test_persistence.py      # All sheets annotation persistence tests
├── test_sync_stability.py   # Multi-sync stability tests
├── test_state_transitions.py # Exception state transition tests
├── test_stats.py            # Statistics validation tests
└── test_per_sheet.py        # Per-sheet exception detection tests
```

## Running Tests

```bash
# Run all ultimate E2E tests
python .scripts/run_tests.py tests/ultimate_e2e/ -v

# Run specific test file
python .scripts/run_tests.py tests/ultimate_e2e/test_persistence.py -v

# Run with stdout output
python .scripts/run_tests.py tests/ultimate_e2e/ -v -s
```

## Sheet Coverage

All 20 sheets from EXCEL_COLUMNS.md are covered:

| # | Sheet | Entity Type | Has Exceptions | Has Notes |
|---|-------|-------------|----------------|-----------|
| 1 | Cover | summary | ❌ | ❌ |
| 2 | Instances | instance | ❌ | ✅ |
| 3 | SA Account | sa_account | ✅ | ✅ |
| 4 | Configuration | config | ✅ | ❌ |
| 5 | Server Logins | login | ✅ | ❌ |
| 6 | Sensitive Roles | server_role_member | ✅ | ❌ |
| 7 | Services | service | ✅ | ❌ |
| 8 | Databases | database | ✅ | ✅ |
| 9 | Database Users | db_user | ✅ | ✅ |
| 10 | Database Roles | db_role | ✅ | ❌ |
| 11 | Orphaned Users | orphaned_user | ✅ | ❌ |
| 12 | Permission Grants | permission | ✅ | ✅ |
| 13 | Role Matrix | role_matrix | ❌ | ❌ |
| 14 | Linked Servers | linked_server | ✅ | ✅ |
| 15 | Triggers | trigger | ✅ | ✅ |
| 16 | Backups | backup | ✅ | ✅ |
| 17 | Client Protocols | protocol | ✅ | ❌ |
| 18 | Encryption | encryption | ❌ | ✅ |
| 19 | Audit Settings | audit_settings | ✅ | ❌ |
| 20 | Actions | action | ❌ | ✅ |

## Test Philosophy

- **Expect failures**: The test suite is designed to expose bugs, not to pass artificially.
- **Modular**: Each sheet has its own spec file for easy maintenance.
- **Extensible**: Adding new sheets or test scenarios is straightforward.
- **Readable**: Clear test names and assertions indicate what failed.
