# Entity Key Formats Reference

> **Purpose**: Single source of truth for entity key formats across all systems.  
> **Status**: ACTIVE - Update when testing each sheet

---

## Key Format Rules

### Universal Format
```
{entity_type}|{server}|{instance}|{...additional_keys}
```

### Case Sensitivity
- **All keys are normalized to lowercase** for matching
- Storage may preserve original case, but lookups MUST be case-insensitive

### DB Annotations Key Format
```
{entity_type}|{entity_key_from_excel}
```

---

## Per-Sheet Key Definitions

### Legend
- **Key Cols**: Columns used to build entity_key (from `SHEET_ANNOTATION_CONFIG`)
- **DB Format**: How the key appears in the annotations table
- **Verified**: ✅ tested, ⚠️ untested, ❌ broken

---

### 1. SA Account
| Property | Value |
|----------|-------|
| Entity Type | `sa_account` |
| Key Cols | Server, Instance, Current Name |
| Example | `sa_account\|myserver\|default\|sa_renamed` |
| Verified | ⚠️ Untested |

---

### 2. Server Logins
| Property | Value |
|----------|-------|
| Entity Type | `login` |
| Key Cols | Server, Instance, Login Name |
| Example | `login\|myserver\|default\|admin_user` |
| Verified | ⚠️ Untested |

---

### 3. Sensitive Roles
| Property | Value |
|----------|-------|
| Entity Type | `server_role_member` |
| Key Cols | Server, Instance, Role, Member |
| Example | `server_role_member\|myserver\|default\|sysadmin\|admin_user` |
| Verified | ⚠️ Untested |

---

### 4. Configuration
| Property | Value |
|----------|-------|
| Entity Type | `config` |
| Key Cols | Server, Instance, Setting |
| Example | `config\|myserver\|default\|xp_cmdshell` |
| Verified | ⚠️ Untested |

---

### 5. Services
| Property | Value |
|----------|-------|
| Entity Type | `service` |
| Key Cols | Server, Instance, Service Name |
| Example | `service\|myserver\|default\|SQL Server Agent` |
| Verified | ⚠️ Untested |

---

### 6. Databases
| Property | Value |
|----------|-------|
| Entity Type | `database` |
| Key Cols | Server, Instance, Database |
| Example | `database\|myserver\|default\|master` |
| Verified | ⚠️ Untested |

---

### 7. Database Users
| Property | Value |
|----------|-------|
| Entity Type | `db_user` |
| Key Cols | Server, Instance, Database, User Name |
| Example | `db_user\|myserver\|default\|master\|dbo` |
| Verified | ⚠️ Untested |

---

### 8. Database Roles
| Property | Value |
|----------|-------|
| Entity Type | `db_role` |
| Key Cols | Server, Instance, Database, Role, Member |
| Example | `db_role\|myserver\|default\|master\|db_owner\|admin` |
| Verified | ⚠️ Untested |

---

### 9. Permission Grants
| Property | Value |
|----------|-------|
| Entity Type | `permission` |
| Key Cols | Server, Instance, Scope, Database, Grantee, Permission, Entity Name |
| Example | `permission\|myserver\|default\|database\|master\|public\|select\|sys.tables` |
| Verified | ⚠️ Untested |

---

### 10. Orphaned Users
| Property | Value |
|----------|-------|
| Entity Type | `orphaned_user` |
| Key Cols | Server, Instance, Database, User Name |
| Example | `orphaned_user\|myserver\|default\|mydb\|old_user` |
| Verified | ⚠️ Untested |

---

### 11. Linked Servers ✅ VERIFIED
| Property | Value |
|----------|-------|
| Entity Type | `linked_server` |
| Key Cols | Server, Instance, Linked Server, Local Login, Remote Login |
| Example | `linked_server\|myserver\|default\|remote_srv\|sa\|sa_remote` |
| Verified | ✅ **20/20 tests passing** |
| Notes | Instance normalizes `(Default)` to empty string in DB key |

---

### 12. Triggers
| Property | Value |
|----------|-------|
| Entity Type | `trigger` |
| Key Cols | Server, Instance, Scope, Database, Trigger Name, Event |
| Example | `trigger\|myserver\|default\|server\|\|tr_audit_login\|LOGON` |
| Verified | ⚠️ Untested |

---

### 13. Client Protocols
| Property | Value |
|----------|-------|
| Entity Type | `protocol` |
| Key Cols | Server, Instance, Protocol |
| Example | `protocol\|myserver\|default\|TCP` |
| Verified | ⚠️ Untested |

---

### 14. Backups
| Property | Value |
|----------|-------|
| Entity Type | `backup` |
| Key Cols | Server, Instance, Database, Recovery Model |
| Example | `backup\|myserver\|default\|master\|SIMPLE` |
| Verified | ⚠️ Untested |
| Known Issues | Legacy key support (without Recovery Model) |

---

### 15. Audit Settings
| Property | Value |
|----------|-------|
| Entity Type | `audit_settings` |
| Key Cols | Server, Instance, Setting |
| Example | `audit_settings\|myserver\|default\|login_auditing` |
| Verified | ⚠️ Untested |

---

### 16. Encryption
| Property | Value |
|----------|-------|
| Entity Type | `encryption` |
| Key Cols | Server, Instance, Key Type, Key Name |
| Example | `encryption\|myserver\|default\|certificate\|my_cert` |
| Verified | ⚠️ Untested |

---

### 17. Instances (Notes Only)
| Property | Value |
|----------|-------|
| Entity Type | `instance` |
| Key Cols | Server, Instance |
| Example | `instance\|myserver\|default` |
| Verified | ⚠️ Untested |

---

### 18. Actions (Special)
| Property | Value |
|----------|-------|
| Entity Type | `action` |
| Key Cols | ID |
| Example | `action\|1` |
| Verified | ⚠️ Untested |
| Notes | Uses database ID, not entity key |

---

## Key Lookup Algorithm

```python
def find_annotation(entity_key: str, annotations: dict) -> dict | None:
    """
    1. Normalize entity_key to lowercase
    2. Try direct lookup
    3. If not found, try all known entity_type prefixes
    4. Return None if still not found
    """
    normalized = entity_key.lower()
    
    if normalized in annotations:
        return annotations[normalized]
    
    for entity_type in KNOWN_TYPES:
        prefixed = f"{entity_type}|{normalized}"
        if prefixed in annotations:
            return annotations[prefixed]
    
    return None
```

---

## Test Checklist (Layer 0)

For each sheet, verify:
- [ ] Excel key matches expected format
- [ ] DB annotation key = `{entity_type}|{excel_key}`
- [ ] Stats lookup finds the annotation
- [ ] Action recorder uses correct key
- [ ] All case variations work (MYSERVER vs myserver)
