"""
CLI package for AutoDBAudit.

Contains command-line interface components.
"""

from . import commands  # pylint: disable=no-name-in-module
from .cli import main

__all__ = ["commands", "main"]
