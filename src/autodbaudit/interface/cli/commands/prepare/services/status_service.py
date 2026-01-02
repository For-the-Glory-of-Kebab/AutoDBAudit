"""
Status Service - Show PS Remoting Connection Status

Displays recorded connection status and availability for all servers.
"""

import json
from typing import List, Optional
from datetime import datetime

from autodbaudit.infrastructure.config.manager import ConfigManager
from autodbaudit.infrastructure.psremoting.repository import PSRemotingRepository
from autodbaudit.infrastructure.psremoting.models import ConnectionProfile


class StatusService:
    """Service for displaying PS remoting connection status."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.repository = PSRemotingRepository()

    def show_status(self, format: str = "table", filter: str = "all") -> str:
        """
        Show recorded PS remoting connection status.

        Args:
            format: Output format (table, json, csv)
            filter: Filter results (all, successful, failed, manual)

        Returns:
            Formatted status report
        """
        profiles = self.repository.get_all_profiles()

        if format == "json":
            return self._format_json(profiles, filter)
        elif format == "csv":
            return self._format_csv(profiles, filter)
        else:
            return self._format_table(profiles, filter)

    def _format_table(self, profiles: List[ConnectionProfile], filter: str) -> str:
        """Format profiles as a table."""
        filtered = self._filter_profiles(profiles, filter)

        if not filtered:
            return "No connection profiles found."

        # Create table header
        header = "| Server | Method | Auth | Last Success | Attempts | SQL Targets | Status |"
        separator = "|--------|--------|------|--------------|----------|-------------|--------|"

        rows = []
        for profile in filtered:
            status = "✅ Success" if profile.successful else "❌ Failed"
            targets = ", ".join(profile.sql_targets) if profile.sql_targets else "None"
            last_success = profile.last_successful_attempt or "Never"
            if last_success != "Never":
                try:
                    # Parse ISO timestamp and format
                    dt = datetime.fromisoformat(last_success.replace('Z', '+00:00'))
                    last_success = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass  # Keep as-is if parsing fails

            row = f"| {profile.server_name} | {profile.connection_method.value} | {profile.auth_method or 'N/A'} | {last_success} | {profile.attempt_count} | {targets} | {status} |"
            rows.append(row)

        return "\n".join([header, separator] + rows)

    def _format_json(self, profiles: List[ConnectionProfile], filter: str) -> str:
        """Format profiles as JSON."""
        filtered = self._filter_profiles(profiles, filter)

        data = []
        for profile in filtered:
            data.append({
                "server_name": profile.server_name,
                "connection_method": profile.connection_method.value,
                "auth_method": profile.auth_method,
                "successful": profile.successful,
                "last_successful_attempt": profile.last_successful_attempt,
                "last_attempt": profile.last_attempt,
                "attempt_count": profile.attempt_count,
                "sql_targets": profile.sql_targets,
                "baseline_state": profile.baseline_state,
                "current_state": profile.current_state,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            })

        return json.dumps(data, indent=2)

    def _format_csv(self, profiles: List[ConnectionProfile], filter: str) -> str:
        """Format profiles as CSV."""
        filtered = self._filter_profiles(profiles, filter)

        if not filtered:
            return "Server,Method,Auth,Last Success,Attempts,SQL Targets,Status"

        lines = ["Server,Method,Auth,Last Success,Attempts,SQL Targets,Status"]

        for profile in filtered:
            status = "Success" if profile.successful else "Failed"
            targets = ";".join(profile.sql_targets) if profile.sql_targets else ""
            last_success = profile.last_successful_attempt or ""

            line = f"{profile.server_name},{profile.connection_method.value},{profile.auth_method or ''},{last_success},{profile.attempt_count},{targets},{status}"
            lines.append(line)

        return "\n".join(lines)

    def _filter_profiles(self, profiles: List[ConnectionProfile], filter: str) -> List[ConnectionProfile]:
        """Filter profiles based on the filter criteria."""
        if filter == "all":
            return profiles
        elif filter == "successful":
            return [p for p in profiles if p.successful]
        elif filter == "failed":
            return [p for p in profiles if not p.successful]
        elif filter == "manual":
            # TODO: Implement manual override detection
            return []
        else:
            return profiles
