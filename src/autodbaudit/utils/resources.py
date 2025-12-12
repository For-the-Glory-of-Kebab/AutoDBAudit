"""
Resource Utilities.

Provides robust path resolution for assets and configuration files,
supporting both development environments and frozen (PyInstaller) executables.
"""

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_base_path() -> Path:
    """
    Get the base path of the application.

    Handles:
    1. PyInstaller _MEIPASS (frozen mode)
    2. Development source root (relative to this file)
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller temp folder
        return Path(sys._MEIPASS)

    # Development mode: resolve project root relative to this file
    # This file is in src/autodbaudit/utils/resources.py
    # Root is up 3 levels: src/autodbaudit/utils -> src/autodbaudit -> src -> Root
    # Wait, usually "Root" contains 'src' and 'assets'.
    # If assets are in project root (peer to src), we go up 4 levels?
    # src/autodbaudit/utils/resources.py
    # ^ parent = utils
    # ^ parent.parent = autodbaudit
    # ^ parent.parent.parent = src
    # ^ parent.parent.parent.parent = Project Root (containing assets/, pyproject.toml)

    # However, relying on depth is fragile. We should search for a marker.
    current = Path(__file__).resolve().parent
    for _ in range(6):  # Search up to 6 levels
        if (current / "assets").exists():
            return current
        if (current / "pyproject.toml").exists():
            return current
        if current.parent == current:  # Reached root
            break
        current = current.parent

    # Fallback to CWD if marker not found (dangerous but standard last resort)
    return Path.cwd()


def get_asset_path(filename: str) -> Path:
    """
    Get the absolute path to an asset file.

    Args:
        filename: Name of the asset (e.g., 'sql_audit_icon.png')

    Returns:
        Path object to the asset

    Raises:
        FileNotFoundError: If the asset cannot be found
    """
    base = get_base_path()

    # 1. Check in 'assets' folder (Standard structure)
    asset_path = base / "assets" / filename
    if asset_path.exists():
        return asset_path

    # 2. Check in '_internal/assets' (PyInstaller one-dir default sometimes)
    asset_path = base / "_internal" / "assets" / filename
    if asset_path.exists():
        return asset_path

    # 3. Check direct path (if flat)
    asset_path = base / filename
    if asset_path.exists():
        return asset_path

    logger.warning("Asset not found: %s in base %s", filename, base)

    # Allow checking CWD explicitly as final fallback
    cwd_path = Path.cwd() / "assets" / filename
    if cwd_path.exists():
        return cwd_path

    raise FileNotFoundError(f"Could not locate asset: {filename}")
