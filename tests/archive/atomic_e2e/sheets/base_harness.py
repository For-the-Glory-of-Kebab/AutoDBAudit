"""
Sheet Test Generator.

Auto-generates E2E test harnesses from SHEET_ANNOTATION_CONFIG.
This provides a base pattern for all sheets.
"""

from __future__ import annotations

import logging
from typing import Any

from tests.atomic_e2e.core.test_harness import AtomicE2ETestHarness, SyncCycleResult

logger = logging.getLogger(__name__)


def create_sheet_harness(
    sheet_name: str,
    entity_type: str,
    key_cols: list[str],
    editable_cols: dict[str, str],
    writer_method: str,
    writer_args_builder,
) -> type:
    """
    Factory to create sheet-specific test harness class.
    
    Args:
        sheet_name: Excel sheet name
        entity_type: Entity type string
        key_cols: List of column names forming entity_key
        editable_cols: Dict mapping Excel header to DB field
        writer_method: Method name on writer (e.g., 'add_backup')
        writer_args_builder: Function(finding) -> dict of writer args
    """
    
    class GeneratedHarness(AtomicE2ETestHarness):
        SHEET_NAME = sheet_name
        ENTITY_TYPE = entity_type
        KEY_COLS = key_cols
        EDITABLE_COLS = list(editable_cols.keys())
        
        def _add_finding_to_writer(self, writer, finding: dict):
            method = getattr(writer, writer_method)
            args = writer_args_builder(finding, self.ctx if hasattr(self, 'ctx') else None)
            method(**args)
        
        def create_mock_finding(
            self,
            server: str = "PROD-SQL01",
            instance: str = "",
            status: str = "FAIL",
            **kwargs,
        ) -> dict[str, Any]:
            """Create a mock finding with proper entity_key format."""
            # Build key parts from KEY_COLS
            key_parts = []
            for col in self.KEY_COLS:
                col_lower = col.lower().replace(" ", "_")
                val = kwargs.get(col_lower, "")
                if col == "Server":
                    val = server
                elif col == "Instance":
                    val = instance
                key_parts.append(str(val).lower())
            
            entity_key = "|".join(key_parts)
            
            finding = {
                "entity_key": entity_key,
                "server": server,
                "instance": instance,
                "status": status,
            }
            finding.update(kwargs)
            return finding
        
        # Assertion helpers
        def assert_action_logged(
            self, result: SyncCycleResult, action_type: str, count: int = 1, msg: str = ""
        ) -> list[dict]:
            all_actions = result.actions_logged
            matches = [a for a in all_actions if action_type.lower() in a.get("action_type", "").lower()]
            if count == 0:
                assert len(matches) == 0, f"{msg or 'Expected NO'} {action_type}, found {len(matches)}"
            else:
                assert len(matches) >= count, f"{msg or 'Expected'} {count} {action_type}, got {len(matches)}"
            return matches
        
        def assert_no_action_logged(self, result: SyncCycleResult, action_type: str, msg: str = ""):
            self.assert_action_logged(result, action_type, count=0, msg=msg)
        
        def assert_annotation_in_db(self, entity_key: str, field: str, contains: str = None) -> dict:
            annotation = self.get_db_annotation(entity_key)
            assert annotation is not None, f"Annotation not found for {entity_key}"
            if contains:
                assert contains.lower() in str(annotation.get(field, "")).lower()
            return annotation
    
    GeneratedHarness.__name__ = f"{sheet_name.replace(' ', '')}TestHarness"
    return GeneratedHarness
