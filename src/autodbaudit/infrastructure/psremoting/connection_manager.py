"""Thin wrapper exposing PSRemotingConnectionManager from the manager package."""

from .manager.orchestrator import PSRemotingConnectionManager

__all__ = ["PSRemotingConnectionManager"]
