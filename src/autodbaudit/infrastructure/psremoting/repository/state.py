"""
Server state persistence for PS remoting.
"""
# pylint: disable=line-too-long

import json
from typing import Optional

from ..models import ServerState
from .base import RepositoryBase


class ServerStateMixin(RepositoryBase):
    """Baseline/current server state storage."""

    def save_server_state(self, state: ServerState) -> int:
        """Persist a server state snapshot."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            firewall_ports_json = json.dumps(state.winrm_firewall_ports) if state.winrm_firewall_ports else None
            full_state_json = json.dumps(state.full_state_json) if state.full_state_json else None

            cursor.execute(
                """
                INSERT INTO psremoting_server_state
                (profile_id, state_type, collected_at, winrm_service_status,
                 winrm_service_startup, winrm_service_account,
                 winrm_firewall_enabled, winrm_firewall_ports, trusted_hosts,
                 network_category, local_account_token_filter,
                 allow_unencrypted, auth_basic, auth_kerberos, auth_negotiate,
                 auth_certificate, auth_credssp, auth_digest, execution_policy,
                 enable_lua, remote_management_enabled, full_state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?)
                """,
                (
                    state.profile_id,
                    state.state_type,
                    state.collected_at,
                    state.winrm_service_status,
                    state.winrm_service_startup,
                    state.winrm_service_account,
                    state.winrm_firewall_enabled,
                    firewall_ports_json,
                    state.trusted_hosts,
                    state.network_category,
                    state.local_account_token_filter,
                    state.allow_unencrypted,
                    state.auth_basic,
                    state.auth_kerberos,
                    state.auth_negotiate,
                    state.auth_certificate,
                    state.auth_credssp,
                    state.auth_digest,
                    state.execution_policy,
                    state.enable_lua,
                    state.remote_management_enabled,
                    full_state_json,
                ),
            )

            state_id = cursor.lastrowid
            conn.commit()
            return int(state_id or 0)

    def get_server_state(self, profile_id: int, state_type: str) -> Optional[ServerState]:
        """Get the latest server state snapshot for a profile/state_type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT profile_id, state_type, collected_at, winrm_service_status,
                       winrm_service_startup, winrm_service_account,
                       winrm_firewall_enabled, winrm_firewall_ports,
                       trusted_hosts, network_category,
                       local_account_token_filter, allow_unencrypted, auth_basic,
                       auth_kerberos, auth_negotiate, auth_certificate,
                       auth_credssp, auth_digest, execution_policy, enable_lua,
                       remote_management_enabled, full_state_json
                FROM psremoting_server_state
                WHERE profile_id = ? AND state_type = ?
                ORDER BY collected_at DESC
                LIMIT 1
                """,
                (profile_id, state_type),
            )

            row = cursor.fetchone()
            if not row:
                return None

            firewall_ports = json.loads(row["winrm_firewall_ports"]) if row["winrm_firewall_ports"] else None
            full_state_json = json.loads(row["full_state_json"]) if row["full_state_json"] else None

            return ServerState(
                profile_id=row["profile_id"],
                state_type=row["state_type"],
                collected_at=row["collected_at"],
                winrm_service_status=row["winrm_service_status"],
                winrm_service_startup=row["winrm_service_startup"],
                winrm_service_account=row["winrm_service_account"],
                winrm_firewall_enabled=row["winrm_firewall_enabled"],
                winrm_firewall_ports=firewall_ports,
                trusted_hosts=row["trusted_hosts"],
                network_category=row["network_category"],
                local_account_token_filter=row["local_account_token_filter"],
                allow_unencrypted=row["allow_unencrypted"],
                auth_basic=row["auth_basic"],
                auth_kerberos=row["auth_kerberos"],
                auth_negotiate=row["auth_negotiate"],
                auth_certificate=row["auth_certificate"],
                auth_credssp=row["auth_credssp"],
                auth_digest=row["auth_digest"],
                execution_policy=row["execution_policy"],
                enable_lua=row["enable_lua"],
                remote_management_enabled=row["remote_management_enabled"],
                full_state_json=full_state_json,
            )
