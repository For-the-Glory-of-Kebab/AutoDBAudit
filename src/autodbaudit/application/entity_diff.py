"""
Entity Diff Service.

Provides comprehensive entity diffing between audit runs to detect ALL changes
to tracked SQL Server entities. This is the core engine for the Actions sheet
changelog.

Change Categories:
    - Entity Added/Removed
    - Property Changed (e.g., SA renamed, login disabled)
    - Status Changed (e.g., xp_cmdshell enabled)
    - Compliance Changed (FAIL → PASS, PASS → FAIL)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EntityChange:
    """Represents a detected change between audit runs."""

    entity_type: str  # sa_account, login, config, etc.
    entity_key: str  # Unique key: Server|Instance|Name
    change_type: str  # SA_RENAMED, LOGIN_DISABLED, FIXED, etc.
    description: str  # Human-readable description
    risk_level: str  # low, medium, high, critical
    old_value: str | None  # Previous value (if applicable)
    new_value: str | None  # New value (if applicable)
    server: str  # Server name for display
    instance: str  # Instance name for display


def detect_all_changes(
    store,
    initial_run_id: int,
    current_run_id: int,
    scanned_instances: set[int] | None = None,
) -> list[EntityChange]:
    """
    Detect ALL changes between the initial audit and current sync.

    Args:
        store: HistoryStore instance
        initial_run_id: The baseline audit run
        current_run_id: The current sync run
        scanned_instances: Set of instance IDs that were scanned (for availability check)

    Returns:
        List of EntityChange objects
    """
    changes = []
    conn = store._get_connection()

    # Get scanned instances for current run if not provided
    if scanned_instances is None:
        scanned_instances = _get_scanned_instances(conn, current_run_id)

    # 1. SA Account changes
    changes.extend(
        _diff_sa_accounts(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 2. Login changes
    changes.extend(
        _diff_logins(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 3. Configuration changes
    changes.extend(
        _diff_config(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 4. Service changes
    changes.extend(
        _diff_services(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 5. Linked server changes
    changes.extend(
        _diff_linked_servers(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 6. Trigger changes
    changes.extend(
        _diff_triggers(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 7. Database changes
    changes.extend(
        _diff_databases(conn, initial_run_id, current_run_id, scanned_instances)
    )

    # 8. Role membership changes
    changes.extend(
        _diff_role_members(conn, initial_run_id, current_run_id, scanned_instances)
    )

    logger.info("EntityDiff: Detected %d total changes", len(changes))
    return changes


def _get_scanned_instances(conn, run_id: int) -> set[int]:
    """Get set of instance IDs that were scanned in a run."""
    rows = conn.execute(
        "SELECT instance_id FROM audit_run_instances WHERE audit_run_id = ?", (run_id,)
    ).fetchall()
    return {row["instance_id"] for row in rows}


def _get_instance_info(conn, instance_id: int) -> tuple[str, str]:
    """Get server and instance name for display."""
    row = conn.execute(
        """
        SELECT s.hostname, i.instance_name
        FROM instances i
        JOIN servers s ON i.server_id = s.id
        WHERE i.id = ?
        """,
        (instance_id,),
    ).fetchone()
    if row:
        return row["hostname"], row["instance_name"] or "(Default)"
    return "Unknown", ""


def _make_entity_key(*parts: str) -> str:
    """Build a composite entity key from parts."""
    return "|".join(str(p) for p in parts)


# =============================================================================
# SA Account Diffing
# =============================================================================


def _diff_sa_accounts(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect SA account changes (rename, disable, enable)."""
    changes = []

    # Get SA data from logins table (where is_sa_account = 1)
    initial = _get_sa_data(conn, initial_run_id)
    current = _get_sa_data(conn, current_run_id)

    for instance_id, cur_data in current.items():
        if instance_id not in scanned:
            continue  # Skip instances not scanned in current run

        server, instance = _get_instance_info(conn, instance_id)
        entity_key = _make_entity_key("sa_account", server, instance)

        if instance_id in initial:
            old_data = initial[instance_id]

            # Check for rename
            if cur_data["login_name"] != old_data["login_name"]:
                changes.append(
                    EntityChange(
                        entity_type="sa_account",
                        entity_key=entity_key,
                        change_type="SA_RENAMED",
                        description=f"SA account renamed: '{old_data['login_name']}' → '{cur_data['login_name']}'",
                        risk_level="low",
                        old_value=old_data["login_name"],
                        new_value=cur_data["login_name"],
                        server=server,
                        instance=instance,
                    )
                )

            # Check for disable
            if cur_data["is_disabled"] and not old_data["is_disabled"]:
                changes.append(
                    EntityChange(
                        entity_type="sa_account",
                        entity_key=entity_key,
                        change_type="SA_DISABLED",
                        description=f"SA account '{cur_data['login_name']}' disabled",
                        risk_level="low",
                        old_value="enabled",
                        new_value="disabled",
                        server=server,
                        instance=instance,
                    )
                )
            elif not cur_data["is_disabled"] and old_data["is_disabled"]:
                changes.append(
                    EntityChange(
                        entity_type="sa_account",
                        entity_key=entity_key,
                        change_type="SA_ENABLED",
                        description=f"SA account '{cur_data['login_name']}' re-enabled (REGRESSION)",
                        risk_level="high",
                        old_value="disabled",
                        new_value="enabled",
                        server=server,
                        instance=instance,
                    )
                )

    return changes


def _get_sa_data(conn, run_id: int) -> dict[int, dict]:
    """Get SA account data for a run, keyed by instance_id."""
    rows = conn.execute(
        """
        SELECT instance_id, login_name, is_disabled
        FROM logins
        WHERE audit_run_id = ? AND is_sa_account = 1
        """,
        (run_id,),
    ).fetchall()
    return {row["instance_id"]: dict(row) for row in rows}


# =============================================================================
# Login Diffing
# =============================================================================


def _diff_logins(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect login changes (added, removed, disabled, enabled, password policy)."""
    changes = []

    initial = _get_logins_data(conn, initial_run_id)
    current = _get_logins_data(conn, current_run_id)

    # Get all unique keys
    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        instance_id, login_name = key
        if instance_id not in scanned:
            continue

        server, instance = _get_instance_info(conn, instance_id)
        entity_key = _make_entity_key("login", server, instance, login_name)

        in_initial = key in initial
        in_current = key in current

        if in_current and not in_initial:
            # LOGIN_ADDED
            changes.append(
                EntityChange(
                    entity_type="login",
                    entity_key=entity_key,
                    change_type="LOGIN_ADDED",
                    description=f"New login created: '{login_name}'",
                    risk_level="medium",
                    old_value=None,
                    new_value=login_name,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and not in_current:
            # LOGIN_REMOVED
            changes.append(
                EntityChange(
                    entity_type="login",
                    entity_key=entity_key,
                    change_type="LOGIN_REMOVED",
                    description=f"Login removed: '{login_name}'",
                    risk_level="low",
                    old_value=login_name,
                    new_value=None,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and in_current:
            old = initial[key]
            cur = current[key]

            # Check disabled status
            if cur["is_disabled"] and not old["is_disabled"]:
                changes.append(
                    EntityChange(
                        entity_type="login",
                        entity_key=entity_key,
                        change_type="LOGIN_DISABLED",
                        description=f"Login '{login_name}' disabled",
                        risk_level="low",
                        old_value="enabled",
                        new_value="disabled",
                        server=server,
                        instance=instance,
                    )
                )
            elif not cur["is_disabled"] and old["is_disabled"]:
                changes.append(
                    EntityChange(
                        entity_type="login",
                        entity_key=entity_key,
                        change_type="LOGIN_ENABLED",
                        description=f"Login '{login_name}' re-enabled",
                        risk_level="medium",
                        old_value="disabled",
                        new_value="enabled",
                        server=server,
                        instance=instance,
                    )
                )

            # Check password policy
            if cur.get("password_policy_enforced") and not old.get(
                "password_policy_enforced"
            ):
                changes.append(
                    EntityChange(
                        entity_type="login",
                        entity_key=entity_key,
                        change_type="LOGIN_PASSWORD_POLICY_ON",
                        description=f"Password policy enabled for '{login_name}'",
                        risk_level="low",
                        old_value="off",
                        new_value="on",
                        server=server,
                        instance=instance,
                    )
                )
            elif not cur.get("password_policy_enforced") and old.get(
                "password_policy_enforced"
            ):
                changes.append(
                    EntityChange(
                        entity_type="login",
                        entity_key=entity_key,
                        change_type="LOGIN_PASSWORD_POLICY_OFF",
                        description=f"Password policy disabled for '{login_name}' (REGRESSION)",
                        risk_level="high",
                        old_value="on",
                        new_value="off",
                        server=server,
                        instance=instance,
                    )
                )

    return changes


def _get_logins_data(conn, run_id: int) -> dict[tuple[int, str], dict]:
    """Get login data for a run, keyed by (instance_id, login_name)."""
    rows = conn.execute(
        """
        SELECT instance_id, login_name, is_disabled, password_policy_enforced
        FROM logins
        WHERE audit_run_id = ? AND is_sa_account != 1
        """,
        (run_id,),
    ).fetchall()
    return {(row["instance_id"], row["login_name"]): dict(row) for row in rows}


# =============================================================================
# Configuration Diffing
# =============================================================================


def _diff_config(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect configuration changes."""
    changes = []

    initial = _get_config_data(conn, initial_run_id)
    current = _get_config_data(conn, current_run_id)

    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        instance_id, setting_name = key
        if instance_id not in scanned:
            continue

        server, instance = _get_instance_info(conn, instance_id)
        entity_key = _make_entity_key("config", server, instance, setting_name)

        if key in initial and key in current:
            old = initial[key]
            cur = current[key]

            if cur["running_value"] != old["running_value"]:
                old_val = old["running_value"]
                new_val = cur["running_value"]

                # Determine if this is a fix or regression
                required = cur.get("required_value")
                if required is not None and new_val == required:
                    risk = "low"
                    change_type = "CONFIG_COMPLIANT"
                    desc = (
                        f"Config '{setting_name}' now compliant: {old_val} → {new_val}"
                    )
                else:
                    risk = "high" if required is not None else "medium"
                    change_type = "CONFIG_CHANGED"
                    desc = f"Config '{setting_name}' changed: {old_val} → {new_val}"

                changes.append(
                    EntityChange(
                        entity_type="config",
                        entity_key=entity_key,
                        change_type=change_type,
                        description=desc,
                        risk_level=risk,
                        old_value=str(old_val),
                        new_value=str(new_val),
                        server=server,
                        instance=instance,
                    )
                )

    return changes


def _get_config_data(conn, run_id: int) -> dict[tuple[int, str], dict]:
    """Get config settings for a run, keyed by (instance_id, setting_name)."""
    rows = conn.execute(
        """
        SELECT instance_id, setting_name, running_value, required_value
        FROM config_settings
        WHERE audit_run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {(row["instance_id"], row["setting_name"]): dict(row) for row in rows}


# =============================================================================
# Service Diffing
# =============================================================================


def _diff_services(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect service changes (account, status, startup type)."""
    changes = []

    initial = _get_services_data(conn, initial_run_id)
    current = _get_services_data(conn, current_run_id)

    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        server_id, service_name = key

        # For services, we need to check if any instance on this server was scanned
        # Services are per-server, not per-instance
        if key in initial and key in current:
            old = initial[key]
            cur = current[key]

            server = cur.get("server_hostname", "Unknown")
            entity_key = _make_entity_key("service", server, service_name)

            # Check account change
            if cur["service_account"] != old["service_account"]:
                changes.append(
                    EntityChange(
                        entity_type="service",
                        entity_key=entity_key,
                        change_type="SERVICE_ACCOUNT_CHANGED",
                        description=f"Service '{service_name}' account changed: '{old['service_account']}' → '{cur['service_account']}'",
                        risk_level="medium",
                        old_value=old["service_account"],
                        new_value=cur["service_account"],
                        server=server,
                        instance="",
                    )
                )

            # Check status change
            if cur["status"] != old["status"]:
                if cur["status"] == "Running" and old["status"] != "Running":
                    change_type = "SERVICE_STARTED"
                    risk = "medium"
                elif cur["status"] != "Running" and old["status"] == "Running":
                    change_type = "SERVICE_STOPPED"
                    risk = "low"
                else:
                    change_type = "SERVICE_STATUS_CHANGED"
                    risk = "low"

                changes.append(
                    EntityChange(
                        entity_type="service",
                        entity_key=entity_key,
                        change_type=change_type,
                        description=f"Service '{service_name}': {old['status']} → {cur['status']}",
                        risk_level=risk,
                        old_value=old["status"],
                        new_value=cur["status"],
                        server=server,
                        instance="",
                    )
                )

            # Check startup type change
            if cur.get("startup_type") != old.get("startup_type"):
                changes.append(
                    EntityChange(
                        entity_type="service",
                        entity_key=entity_key,
                        change_type="SERVICE_STARTUP_CHANGED",
                        description=f"Service '{service_name}' startup: {old.get('startup_type')} → {cur.get('startup_type')}",
                        risk_level="low",
                        old_value=old.get("startup_type"),
                        new_value=cur.get("startup_type"),
                        server=server,
                        instance="",
                    )
                )

    return changes


def _get_services_data(conn, run_id: int) -> dict[tuple[int, str], dict]:
    """Get service data for a run, keyed by (server_id, service_name)."""
    rows = conn.execute(
        """
        SELECT ss.server_id, ss.service_name, ss.service_account, ss.status, ss.startup_type,
               s.hostname as server_hostname
        FROM sql_services ss
        JOIN servers s ON ss.server_id = s.id
        WHERE ss.audit_run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {(row["server_id"], row["service_name"]): dict(row) for row in rows}


# =============================================================================
# Linked Server Diffing
# =============================================================================


def _diff_linked_servers(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect linked server changes (added, removed, config changed)."""
    changes = []

    initial = _get_linked_servers_data(conn, initial_run_id)
    current = _get_linked_servers_data(conn, current_run_id)

    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        instance_id, ls_name = key
        if instance_id not in scanned:
            continue

        server, instance = _get_instance_info(conn, instance_id)
        entity_key = _make_entity_key("linked_server", server, instance, ls_name)

        in_initial = key in initial
        in_current = key in current

        if in_current and not in_initial:
            changes.append(
                EntityChange(
                    entity_type="linked_server",
                    entity_key=entity_key,
                    change_type="LINKED_SERVER_ADDED",
                    description=f"New linked server: '{ls_name}'",
                    risk_level="medium",
                    old_value=None,
                    new_value=ls_name,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and not in_current:
            changes.append(
                EntityChange(
                    entity_type="linked_server",
                    entity_key=entity_key,
                    change_type="LINKED_SERVER_REMOVED",
                    description=f"Linked server removed: '{ls_name}'",
                    risk_level="low",
                    old_value=ls_name,
                    new_value=None,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and in_current:
            old = initial[key]
            cur = current[key]

            # Check for config changes
            config_fields = ["is_rpc_out_enabled", "is_data_access_enabled"]
            for field in config_fields:
                if cur.get(field) != old.get(field):
                    changes.append(
                        EntityChange(
                            entity_type="linked_server",
                            entity_key=entity_key,
                            change_type="LINKED_SERVER_CONFIG_CHANGED",
                            description=f"Linked server '{ls_name}' {field}: {old.get(field)} → {cur.get(field)}",
                            risk_level="medium",
                            old_value=str(old.get(field)),
                            new_value=str(cur.get(field)),
                            server=server,
                            instance=instance,
                        )
                    )

    return changes


def _get_linked_servers_data(conn, run_id: int) -> dict[tuple[int, str], dict]:
    """Get linked server data for a run."""
    rows = conn.execute(
        """
        SELECT instance_id, linked_server_name, is_rpc_out_enabled, is_data_access_enabled
        FROM linked_servers
        WHERE audit_run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {(row["instance_id"], row["linked_server_name"]): dict(row) for row in rows}


# =============================================================================
# Trigger Diffing
# =============================================================================


def _diff_triggers(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect trigger changes (added, removed, enabled/disabled)."""
    changes = []

    initial = _get_triggers_data(conn, initial_run_id)
    current = _get_triggers_data(conn, current_run_id)

    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        instance_id, trigger_name, database_name = key
        if instance_id not in scanned:
            continue

        server, instance = _get_instance_info(conn, instance_id)
        scope = database_name or "SERVER"
        entity_key = _make_entity_key("trigger", server, instance, scope, trigger_name)

        in_initial = key in initial
        in_current = key in current

        if in_current and not in_initial:
            changes.append(
                EntityChange(
                    entity_type="trigger",
                    entity_key=entity_key,
                    change_type="TRIGGER_ADDED",
                    description=f"New trigger: '{trigger_name}' ({scope})",
                    risk_level="medium",
                    old_value=None,
                    new_value=trigger_name,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and not in_current:
            changes.append(
                EntityChange(
                    entity_type="trigger",
                    entity_key=entity_key,
                    change_type="TRIGGER_REMOVED",
                    description=f"Trigger removed: '{trigger_name}' ({scope})",
                    risk_level="low",
                    old_value=trigger_name,
                    new_value=None,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and in_current:
            old = initial[key]
            cur = current[key]

            if cur.get("is_disabled") != old.get("is_disabled"):
                if cur.get("is_disabled"):
                    change_type = "TRIGGER_DISABLED"
                    risk = "low"
                else:
                    change_type = "TRIGGER_ENABLED"
                    risk = "medium"

                changes.append(
                    EntityChange(
                        entity_type="trigger",
                        entity_key=entity_key,
                        change_type=change_type,
                        description=f"Trigger '{trigger_name}' ({scope}): {'disabled' if cur.get('is_disabled') else 'enabled'}",
                        risk_level=risk,
                        old_value="disabled" if old.get("is_disabled") else "enabled",
                        new_value="disabled" if cur.get("is_disabled") else "enabled",
                        server=server,
                        instance=instance,
                    )
                )

    return changes


def _get_triggers_data(conn, run_id: int) -> dict[tuple[int, str, str], dict]:
    """Get trigger data for a run."""
    rows = conn.execute(
        """
        SELECT instance_id, trigger_name, database_name, is_disabled
        FROM triggers
        WHERE audit_run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {
        (row["instance_id"], row["trigger_name"], row["database_name"] or ""): dict(row)
        for row in rows
    }


# =============================================================================
# Database Diffing
# =============================================================================


def _diff_databases(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect database changes (added, removed, owner, recovery, trustworthy)."""
    changes = []

    initial = _get_databases_data(conn, initial_run_id)
    current = _get_databases_data(conn, current_run_id)

    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        instance_id, db_name = key
        if instance_id not in scanned:
            continue

        server, instance = _get_instance_info(conn, instance_id)
        entity_key = _make_entity_key("database", server, instance, db_name)

        in_initial = key in initial
        in_current = key in current

        if in_current and not in_initial:
            changes.append(
                EntityChange(
                    entity_type="database",
                    entity_key=entity_key,
                    change_type="DATABASE_ADDED",
                    description=f"New database: '{db_name}'",
                    risk_level="medium",
                    old_value=None,
                    new_value=db_name,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and not in_current:
            changes.append(
                EntityChange(
                    entity_type="database",
                    entity_key=entity_key,
                    change_type="DATABASE_REMOVED",
                    description=f"Database removed: '{db_name}'",
                    risk_level="medium",
                    old_value=db_name,
                    new_value=None,
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and in_current:
            old = initial[key]
            cur = current[key]

            # Owner change
            if cur.get("owner") != old.get("owner"):
                changes.append(
                    EntityChange(
                        entity_type="database",
                        entity_key=entity_key,
                        change_type="DATABASE_OWNER_CHANGED",
                        description=f"Database '{db_name}' owner: '{old.get('owner')}' → '{cur.get('owner')}'",
                        risk_level="medium",
                        old_value=old.get("owner"),
                        new_value=cur.get("owner"),
                        server=server,
                        instance=instance,
                    )
                )

            # Recovery model change
            if cur.get("recovery_model") != old.get("recovery_model"):
                changes.append(
                    EntityChange(
                        entity_type="database",
                        entity_key=entity_key,
                        change_type="DATABASE_RECOVERY_CHANGED",
                        description=f"Database '{db_name}' recovery: {old.get('recovery_model')} → {cur.get('recovery_model')}",
                        risk_level="medium",
                        old_value=old.get("recovery_model"),
                        new_value=cur.get("recovery_model"),
                        server=server,
                        instance=instance,
                    )
                )

            # Trustworthy change
            if cur.get("is_trustworthy") != old.get("is_trustworthy"):
                if cur.get("is_trustworthy"):
                    risk = "high"
                    desc = f"Database '{db_name}' TRUSTWORTHY enabled (SECURITY RISK)"
                else:
                    risk = "low"
                    desc = f"Database '{db_name}' TRUSTWORTHY disabled"

                changes.append(
                    EntityChange(
                        entity_type="database",
                        entity_key=entity_key,
                        change_type="DATABASE_TRUSTWORTHY_CHANGED",
                        description=desc,
                        risk_level=risk,
                        old_value="ON" if old.get("is_trustworthy") else "OFF",
                        new_value="ON" if cur.get("is_trustworthy") else "OFF",
                        server=server,
                        instance=instance,
                    )
                )

    return changes


def _get_databases_data(conn, run_id: int) -> dict[tuple[int, str], dict]:
    """Get database data for a run."""
    rows = conn.execute(
        """
        SELECT instance_id, database_name, owner, recovery_model, is_trustworthy
        FROM databases
        WHERE audit_run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {(row["instance_id"], row["database_name"]): dict(row) for row in rows}


# =============================================================================
# Role Membership Diffing
# =============================================================================


def _diff_role_members(
    conn, initial_run_id: int, current_run_id: int, scanned: set[int]
) -> list[EntityChange]:
    """Detect server role membership changes (added, removed)."""
    changes = []

    initial = _get_role_members_data(conn, initial_run_id)
    current = _get_role_members_data(conn, current_run_id)

    all_keys = set(initial.keys()) | set(current.keys())

    for key in all_keys:
        instance_id, role_name, member_login = key
        if instance_id not in scanned:
            continue

        server, instance = _get_instance_info(conn, instance_id)
        entity_key = _make_entity_key(
            "role_member", server, instance, role_name, member_login
        )

        in_initial = key in initial
        in_current = key in current

        # Determine risk level based on role
        is_sensitive = role_name.lower() in ("sysadmin", "securityadmin", "serveradmin")
        risk = "high" if is_sensitive else "medium"

        if in_current and not in_initial:
            changes.append(
                EntityChange(
                    entity_type="role_member",
                    entity_key=entity_key,
                    change_type="ROLE_MEMBER_ADDED",
                    description=f"'{member_login}' added to {role_name}",
                    risk_level=risk,
                    old_value=None,
                    new_value=f"{member_login} → {role_name}",
                    server=server,
                    instance=instance,
                )
            )
        elif in_initial and not in_current:
            changes.append(
                EntityChange(
                    entity_type="role_member",
                    entity_key=entity_key,
                    change_type="ROLE_MEMBER_REMOVED",
                    description=f"'{member_login}' removed from {role_name}",
                    risk_level="low",
                    old_value=f"{member_login} → {role_name}",
                    new_value=None,
                    server=server,
                    instance=instance,
                )
            )

    return changes


def _get_role_members_data(conn, run_id: int) -> dict[tuple[int, str, str], dict]:
    """Get role membership data for a run."""
    rows = conn.execute(
        """
        SELECT instance_id, role_name, member_login
        FROM login_role_memberships
        WHERE audit_run_id = ?
        """,
        (run_id,),
    ).fetchall()
    return {
        (row["instance_id"], row["role_name"], row["member_login"]): dict(row)
        for row in rows
    }
