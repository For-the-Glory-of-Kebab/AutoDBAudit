"""
Shared constants for the application layer.
"""

from __future__ import annotations


# Security settings to audit (per db-requirements.md)
SECURITY_SETTINGS = {
    # HIGH RISK - command execution
    "xp_cmdshell": (0, "high"),
    "Ole Automation Procedures": (0, "high"),
    # MEDIUM RISK - feature surface area
    "clr enabled": (0, "medium"),
    "clr strict security": (1, "medium"),
    "Ad Hoc Distributed Queries": (0, "medium"),
    "Database Mail XPs": (0, "medium"),
    "cross db ownership chaining": (0, "medium"),
    "remote access": (0, "medium"),
    "remote admin connections": (0, "medium"),
    "scan for startup procs": (0, "medium"),
    "external scripts enabled": (0, "medium"),
    # LOW RISK - monitoring/info
    "show advanced options": (0, "low"),
    "default trace enabled": (1, "low"),
}

# System databases to skip for per-db queries
SYSTEM_DBS = ("master", "tempdb", "model", "msdb")
