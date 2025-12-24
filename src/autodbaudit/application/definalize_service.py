"""
Definalize Service - Revert finalized audits to in-progress state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autodbaudit.infrastructure.sqlite import HistoryStore

logger = logging.getLogger(__name__)


class DefinalizeService:
    """
    Service to revert finalized audits to in-progress state.
    """

    def __init__(self, db_path: str | Path = "output/audit_history.db"):
        self.db_path = Path(db_path)
        self.store = HistoryStore(self.db_path)

    def definalize(self, audit_id: int) -> dict[str, Any]:
        """
        Revert audit status from 'finalized' to 'in_progress'.

        Args:
            audit_id: ID of the audit to definalize

        Returns:
            Dict with status and message
        """
        # Get audit status from audits table
        with self.store._get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM audits WHERE id = ?", (audit_id,)
            ).fetchone()
            if not row:
                return {"error": f"Audit #{audit_id} not found"}
            audit = {"status": row[0]}

        if audit["status"] != "finalized":
            return {
                "error": f"Audit #{audit_id} is not finalized (status: {audit['status']})"
            }

        try:
            # We need to manually execute SQL update since HistoryStore might not have this method
            # Direct SQL access for this special operation
            with self.store._get_connection() as conn:
                conn.execute(
                    "UPDATE audits SET status = ?, completed_at = NULL WHERE id = ?",
                    ("in_progress", audit_id),
                )
                conn.commit()

            logger.info("Audit #%d definalized (reverted to in_progress)", audit_id)
            return {
                "success": True,
                "message": f"Audit #{audit_id} reverted to 'in_progress'",
            }

        except Exception as e:
            logger.error("Definalize failed: %s", e)
            return {"error": f"Failed to definalize: {e}"}
