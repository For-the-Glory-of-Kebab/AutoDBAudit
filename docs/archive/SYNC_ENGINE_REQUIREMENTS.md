# Sync Engine Requirements Specification

> **Purpose**: Single source of truth for ALL sync engine logic.  
> **Created**: 2025-12-18 | **Updated**: 2025-12-18  
> **Status**: ACTIVE SPECIFICATION - Do NOT proceed until approved

---

## Part 1: Core Definitions

### 1.1 Finding Status
| Status | Discrepant? |
|--------|-------------|
| `PASS` | ❌ No |
| `FAIL` | ✅ Yes |
| `WARN` | ✅ Yes |

### 1.2 Exception
A row is **exceptioned** if:
1. Was discrepant (FAIL/WARN), AND
2. Has (justification OR review_status == "Exception")

> **Non-discrepant + Exception dropdown** → Ignored, cleared next sync  
> **Non-discrepant + Justification** → Saved as note (becomes exception if discrepant later)

### 1.3 Priority When Multiple Events
1. **Fix** (highest) - clears exception
2. Regression
3. Exception Added
4. Exception Removed
5. Still Failing (no new log)

---

## Part 2: Entity-Mutation Reference

> Derived from `db-requirements.md` (28 requirements)

### 2.1 SA Account (Req #4)
| Mutation | Loggable? | Example |
|----------|-----------|---------|
| Renamed | ✅ | `sa → $@` |
| Disabled/Enabled | ✅ | `Enabled → Disabled` |
| Password Changed | ⚠️ Info | Password policy changed |
| Default DB Changed | ⚠️ Info | `master → tempdb` |

### 2.2 Server Logins (Req #5,7,8,26)
| Mutation | Loggable? |
|----------|-----------|
| Added | ✅ |
| Removed | ✅ |
| Renamed | ✅ |
| Disabled/Enabled | ✅ |
| Password Policy On/Off | ✅ |
| Password Expiration On/Off | ✅ |
| Default Database Changed | ⚠️ Info |
| Added to Sensitive Role | ✅ Critical |
| Removed from Sensitive Role | ✅ |

### 2.3 Server Roles / Sensitive Roles (Req #5,8,26)
| Mutation | Loggable? |
|----------|-----------|
| Member Added | ✅ Critical |
| Member Removed | ✅ |

### 2.4 Configuration Settings (Req #10,16,18,20,21,22)
| Mutation | Loggable? |
|----------|-----------|
| Value Changed | ✅ |
| Became Compliant | ✅ Fix |
| Became Non-Compliant | ✅ Regression |

Settings tracked: `xp_cmdshell`, `Ad Hoc Distributed Queries`, `Database Mail XPs`, `remote access`, `clr enabled`, `Ole Automation Procedures`, Login Auditing mode

### 2.5 Services (Req #6,19,21)
| Mutation | Loggable? |
|----------|-----------|
| Started/Stopped | ✅ |
| Startup Type Changed | ✅ |
| Service Account Changed | ✅ |
| Became Compliant | ✅ Fix |
| Became Non-Compliant | ✅ Regression |

### 2.6 Databases (Req #15)
| Mutation | Loggable? |
|----------|-----------|
| Added | ✅ |
| Removed/Detached | ✅ |
| Owner Changed | ⚠️ Info |
| Recovery Model Changed | ⚠️ Info |
| Trustworthy On/Off | ✅ Security |
| State Changed | ⚠️ Info |

### 2.7 Database Users (Req #13,27)
| Mutation | Loggable? |
|----------|-----------|
| Added | ✅ |
| Removed | ✅ |
| Orphaned | ✅ Critical |
| Fixed (mapped) | ✅ Fix |
| Guest Enabled | ✅ Critical |
| Guest Disabled | ✅ Fix |

### 2.8 Database Roles (Req #8,27)
| Mutation | Loggable? |
|----------|-----------|
| Member Added to db_owner | ✅ Critical |
| Member Removed from db_owner | ✅ |
| Member Added to other role | ⚠️ Info |

### 2.9 Linked Servers (Req #24,25)
| Mutation | Loggable? |
|----------|-----------|
| Added | ✅ |
| Removed | ✅ |
| Remote Login Changed | ✅ Security |
| Using sa/sysadmin | ✅ Critical |
| RPC Out Enabled/Disabled | ⚠️ Info |

### 2.10 Triggers (Req #12)
| Mutation | Loggable? |
|----------|-----------|
| Added | ✅ |
| Removed | ✅ |
| Enabled/Disabled | ✅ |

### 2.11 Backups (Req #11)
| Mutation | Loggable? |
|----------|-----------|
| Backup Missing → Present | ✅ Fix |
| Backup Present → Missing | ✅ Critical |
| Backup Age Exceeded Threshold | ✅ Warning |

### 2.12 Client Protocols (Req #17)
| Mutation | Loggable? |
|----------|-----------|
| Protocol Enabled | ✅ |
| Protocol Disabled | ✅ |
| Port Changed | ⚠️ Info |

### 2.13 Encryption (Req #11)
| Mutation | Loggable? |
|----------|-----------|
| Key Created | ⚠️ Info |
| Key Backed Up | ✅ |
| TDE Enabled/Disabled | ✅ Security |

### 2.14 Instance/Version (Req #1,2,3)
| Mutation | Loggable? |
|----------|-----------|
| Version Updated | ✅ Info |
| Product Level Changed | ✅ Info |
| Edition Changed | ⚠️ Rare |

---

## Part 3: Action Log Specification

### 3.1 Behavior Rules
- **Append-only**: Never delete rows
- **No duplicates**: Same entity + same change_type in same sync = one entry
- **User-editable fields**: `Detected Date`, `Notes`
- **Persistence**: User edits sync back to SQLite

### 3.2 What Creates Entries
| Event | Creates Log? | Change Type |
|-------|--------------|-------------|
| FAIL→PASS | ✅ | Fixed |
| PASS→FAIL | ✅ | Regression |
| New FAIL | ✅ | New Issue |
| Exception added | ✅ | Exception Documented |
| Exception removed | ✅ | Exception Removed |
| Exception updated | ⚠️ Optional | Exception Updated |
| Entity mutation (see Part 2) | ✅ | Per-mutation type |
| No change | ❌ | - |

### 3.3 Deduplication
```
IF exists(action WHERE entity_key=X AND change_type=Y AND sync_run_id=current):
    SKIP  # Already logged this sync
ELSE:
    INSERT new action
```

### 3.4 Date Handling
- `Detected Date`: Set when FIRST detected
- User can override → persisted to `user_date_override` column
- Display logic: `COALESCE(user_date_override, detected_date)`
- Merged cell re-ordering must handle empty cells gracefully

### 3.5 Stats vs Logs Distinction
> **Important**: Action log ≠ Stats calculation

- **Action Log**: Historical record of events (append-only)
- **Stats**: Current state calculation (computed fresh each time)

Example: Editing justification = 1 log entry, but NOT a new exception count

---

## Part 4: Stats Service Specification

### 4.1 Single Source of Truth
```python
class StatsService:
    """THE authoritative source for all stats."""
    
    def calculate(self, baseline_run_id, current_run_id) -> SyncStats:
        """Returns all stats from one function."""
```

### 4.2 Stats Returned
```python
@dataclass
class SyncStats:
    # Current State
    total_findings: int
    active_issues: int      # FAIL/WARN without exception
    documented_exceptions: int
    compliant_items: int    # PASS
    
    # Changes from Baseline
    fixed_since_baseline: int
    regressions_since_baseline: int
    new_issues_since_baseline: int
    exceptions_added_since_baseline: int
    
    # Changes from Last Sync
    fixed_since_last: int
    regressions_since_last: int
    new_issues_since_last: int
    exceptions_added_since_last: int
    
    # Entity Changes (info-only)
    entity_changes_count: int
```

### 4.3 Consumers
- CLI `--sync` output
- CLI `--status` command
- Excel Cover Sheet
- `--finalize` validation

ALL call `StatsService.calculate()` - no inline stat logic!

---

## Part 5: Excel↔DB Sync Architecture

### 5.1 Unique Keys per Sheet
| Sheet | Key Columns |
|-------|-------------|
| Instances | Server + Instance |
| SA Account | Server + Instance + Current Name |
| Server Logins | Server + Instance + Login Name |
| Sensitive Roles | Server + Instance + Role + Member |
| Configuration | Server + Instance + Setting |
| Services | Server + Instance + Service Name |
| Databases | Server + Instance + Database |
| Database Users | Server + Instance + Database + User Name |
| Database Roles | Server + Instance + Database + Role + Member |
| Orphaned Users | Server + Instance + Database + User Name |
| Linked Servers | Server + Instance + Linked Server Name |
| Triggers | Server + Instance + Scope + Trigger Name |
| Backups | Server + Instance + Database + Recovery Model |
| Client Protocols | Server + Instance + Protocol |
| Encryption | Server + Instance + Type + Name |
| Audit Settings | Server + Instance + Setting |
| **Actions** | **ID** (DB-generated) |

### 5.2 Bidirectional Sync Rules
```
READ from Excel:
  - User-editable columns only (Justification, Review Status, Notes, Date)
  - Match by key columns
  - Handle merged cells (track last non-empty value)

WRITE to Excel:
  - System columns (Status, Indicators)
  - Preserve user-edited values
  - Update indicators (⏳/✓) based on state
```

### 5.3 Error Handling
- Key not found → Log warning, skip row
- Parse error → Log warning, use default
- Merged cell → Track context, don't lose data
- File locked → Error out gracefully, no partial writes

---

## Part 6: Implementation Phases

### Phase 1: Domain Layer (~2hrs)
- [ ] `domain/change_types.py` - Enums
- [ ] `domain/state_machine.py` - Transition logic
- [ ] Unit tests for all transitions

### Phase 2: Stats Service (~2hrs)
- [ ] `application/stats_service.py` - Single source
- [ ] Unit tests for counting logic

### Phase 3: Entity Diff Module (~3hrs)
- [ ] `application/diff/` module
- [ ] Per-entity diff functions
- [ ] Integration with state machine

### Phase 4: Action System (~2hrs)
- [ ] `application/actions/action_detector.py`
- [ ] `application/actions/action_recorder.py`
- [ ] Deduplication logic

### Phase 5: Excel Sync Robustness (~2hrs)
- [ ] Key validation per sheet
- [ ] Error handling improvements
- [ ] ID persistence for Actions

### Phase 6: Sync Orchestrator (~3hrs)
- [ ] Rewrite `sync_service.py` (~100 lines)
- [ ] Wire all modules together
- [ ] CLI output formatting

### Phase 7: Testing (~2hrs)
- [ ] E2E test with simulation script
- [ ] Multi-sync stability test

---

## Part 7: Test Scenarios

### Basic
- [ ] Fresh audit → All FAIL/WARN show ⏳
- [ ] Add justification → ✓ Exception
- [ ] Fix in SQL Server → Logged as Fixed
- [ ] PASS + justification → Note saved (not exception)

### Multi-Sync Stability  
- [ ] Sync 1→2→3 no changes → Counts stable
- [ ] Exception not re-detected in subsequent syncs
- [ ] Action log doesn't duplicate

### Edge Cases
- [ ] Instance unavailable → Not falsely Fixed
- [ ] Exception + Fix same sync → Fix wins
- [ ] Regression of fixed item → Logged

---

*Approved by user: Pending*
