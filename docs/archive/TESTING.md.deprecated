# Testing Strategy & E2E Validation

**Version**: 1.2
**Role**: Canconical reference for the testing framework and coverage.

## 1. Test Architecture

AutoDBAudit uses a "Nuclear" offline testing strategy (`ultimate_e2e`) that simulates the entire audit lifecycle without needing a live SQL Server.

### Core Test Suite (`tests/ultimate_e2e/`)
*   **`test_persistence.py`**: Verifies 16/16 sheets can save/load annotations.
*   **`test_state_transitions.py`**: Verifies detection of Fixes, Regressions, and New Issues.
*   **`test_sync_stability.py`**: Ensures repeated syncs don't create duplicate logs.
*   **`test_report_generation.py`**: Checks Excel layout and Cover sheet stats.

**Run All Tests:**
```bash
.\scripts\run_e2e.ps1
```

---

## 2. Test Scenarios (State Matrix)

We verify 12 key scenarios to ensure data integrity during synchronization.

| Scenario | User Action | Expected System Behavior |
| :--- | :--- | :--- |
| **01. Justification** | Add note to FAIL item | Log `EXCEPTION_ADDED`, set Indicator ⏳->✓ |
| **02. Fix** | Discrepant item becomes Compliant | Log `FIXED`, Clear Exception |
| **03. Regression** | Compliant item becomes Discrepant | Log `REGRESSION`, set Indicator ⏳ |
| **04. Stability** | Sync 3x with no changes | Zero log entries, Zero stats changes |
| **05. Persistence** | Close/Open Excel | Annotations and IDs match 100% |
| **06. Resilience** | Edit text of existing note | Update DB, no new "Exception" count |

---

## 3. Sheet Coverage Status

| Sheet | Entity Type | Finding Logic? | Tests |
| :--- | :--- | :--- | :--- |
| **SA Account** | sa_account | ✅ Yes | ✅ Passing |
| **Server Logins** | login | ✅ Yes | ✅ Passing |
| **Sensitive Roles** | server_role_member | ✅ Yes | ✅ Passing |
| **Configuration** | config | ✅ Yes | ✅ Passing |
| **Services** | service | ✅ Yes | ✅ Passing |
| **Databases** | database | ✅ Yes | ✅ Passing |
| **DB Users** | db_user | ✅ Yes | ✅ Passing |
| **Permissions** | permission | ✅ Yes | ✅ Passing |
| **Linked Servers** | linked_server | ✅ Yes | ✅ Passing |
| **Backups** | backup | ✅ Yes | ✅ Passing |
| **Encryption** | encryption | Info Only | - |

**Total Status**:
*   **179 Total Tests**
*   **178 Passed** (99.4%)
*   **0 Failed**

---

## 4. Known Edge Cases (Handled)

1.  **Duplicate Detection**: Fixed by lowercase UUID normalization.
2.  **Icon Stripping**: Fixed by cleaning Permission keys (e.g., `🔌 Connect`).
3.  **Layout Shifts**: Tests adjusted for new UUID Column A offset.
