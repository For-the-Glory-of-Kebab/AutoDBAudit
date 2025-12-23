"""
Configuration for Robust E2E Tests.
"""

from pathlib import Path
import tempfile
import os

# Create a deterministic temp directory for easier debugging if needed
# or allow random for CI/CD isolation. For now, fixed for debugging.
TEST_ROOT = Path(tempfile.gettempdir()) / "autodbaudit_robust_e2e"
TEST_ROOT.mkdir(exist_ok=True, parents=True)

OUTPUT_DIR = TEST_ROOT / "output"
CONFIG_DIR = TEST_ROOT / "config"

DB_PATH = OUTPUT_DIR / "audit_history.db"

# We'll need a dummy targets file for the AuditService to load
TARGETS_FILE = CONFIG_DIR / "sql_targets.json"

# Mock Server Details
SERVER_NAME = "TEST-SERVER"
INSTANCE_NAME = "TEST-INSTANCE"
SQL_VERSION = "15.0.2000"

# Entity Keys for Test Data
ENTITY_LOGIN_FAIL = "Login-Fail-User"
ENTITY_LOGIN_PASS = "Login-Pass-User"
ENTITY_ROLE_MEMBER = "Sensitive-Role-Member"
