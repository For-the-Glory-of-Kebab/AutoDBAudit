"""
OS Data Module - Ultra-Granular Architecture.

Modern facade over micro-components for OS data collection.
Railway-oriented with priority fallback chain.
"""

from autodbaudit.application.os_data.orchestrator import OsDataOrchestrator
from autodbaudit.application.os_data.puller import OsDataPuller, OsDataResult

__all__ = ["OsDataOrchestrator", "OsDataPuller", "OsDataResult"]
