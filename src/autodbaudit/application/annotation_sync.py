"""
Annotation Sync Service.

Provides bidirectional synchronization of user annotations (Notes, Reasons, Dates)
between Excel reports and SQLite database.

Core Principles:
1. SQLite = Source of Truth for system data
2. Excel = UI for human annotations
3. Stable entity keys for reliable round-trip
4. Whitelist-only editable columns
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# Sheet configuration: entity type, key columns, editable columns
# Key columns are column header names (matched case-insensitively)
# Editable columns map Excel header name to DB field name
# Justification columns mark FAIL items as documented exceptions when filled
SHEET_ANNOTATION_CONFIG = {
    "Instances": {
        "entity_type": "instance",
        "key_cols": ["Server", "Instance"],
        "editable_cols": {
            "Notes": "notes",
        },
    },
    "SA Account": {
        "entity_type": "sa_account",
        "key_cols": ["Server", "Instance"],
        "editable_cols": {
            "Justification": "justification",  # FAIL + justification = exception
            "Notes": "notes",
        },
    },
    "Server Logins": {
        "entity_type": "login",
        "key_cols": ["Server", "Instance", "Login Name"],
        "editable_cols": {
            "Justification": "justification",
            "Notes": "notes",
        },
    },
    "Sensitive Roles": {
        "entity_type": "role_member",
        "key_cols": ["Server", "Instance", "Role", "Member"],
        "editable_cols": {
            "Justification": "justification",
        },
    },
    "Configuration": {
        "entity_type": "config",
        "key_cols": ["Server", "Instance", "Setting"],
        "editable_cols": {
            "Exception Reason": "justification",  # Original column name
        },
    },
    "Services": {
        "entity_type": "service",
        "key_cols": ["Server", "Service Name"],
        "editable_cols": {
            "Notes": "notes",
        },
    },
    "Databases": {
        "entity_type": "database",
        "key_cols": ["Server", "Instance", "Database"],
        "editable_cols": {
            "Justification": "justification",
            "Notes": "notes",
        },
    },
    "Database Users": {
        "entity_type": "db_user",
        "key_cols": ["Server", "Instance", "Database", "User Name"],
        "editable_cols": {
            "Justification": "justification",
            "Notes": "notes",
        },
    },
    "Database Roles": {
        "entity_type": "db_role",
        "key_cols": ["Server", "Instance", "Database", "Role", "Member"],
        "editable_cols": {
            "Justification": "justification",
        },
    },
    "Permission Grants": {
        "entity_type": "permission",
        "key_cols": ["Server", "Instance", "Scope", "Grantee", "Permission"],
        "editable_cols": {
            "Justification": "justification",
            "Notes": "notes",
        },
    },
    "Orphaned Users": {
        "entity_type": "orphaned_user",
        "key_cols": ["Server", "Instance", "Database", "User Name"],
        "editable_cols": {
            "Remediation": "remediation_notes",
        },
    },
    "Linked Servers": {
        "entity_type": "linked_server",
        "key_cols": ["Server", "Instance", "Linked Server"],
        "editable_cols": {
            "Purpose": "purpose",  # Info-only, not discrepancy
        },
    },
    "Triggers": {
        "entity_type": "trigger",
        "key_cols": ["Server", "Instance", "Database", "Trigger Name"],
        "editable_cols": {
            "Purpose": "purpose",
        },
    },
    "Backups": {
        "entity_type": "backup",
        "key_cols": ["Server", "Instance", "Database"],
        "editable_cols": {
            "Justification": "justification",
            "Notes": "notes",
        },
    },
    "Audit Settings": {
        "entity_type": "audit_settings",
        "key_cols": ["Server", "Instance", "Setting"],
        "editable_cols": {
            "Justification": "justification",
            "Notes": "notes",
        },
    },
    "Encryption": {
        "entity_type": "encryption",
        "key_cols": ["Server", "Instance", "Type", "Name"],
        "editable_cols": {
            "Notes": "notes",
        },
    },
    "Actions": {
        "entity_type": "action",
        "key_cols": ["Server", "Instance", "Finding"],
        "editable_cols": {
            "Detected Date": "detected_date",
            "Assigned To": "assigned_to",
            "Notes": "notes",
        },
    },
}


class AnnotationSyncService:
    """
    Bidirectional annotation sync between Excel and SQLite.
    
    Usage:
        sync = AnnotationSyncService("output/audit_history.db")
        
        # Before regenerating Excel:
        annotations = sync.read_all_from_excel("output/Audit_Latest.xlsx")
        
        # After regenerating Excel:
        sync.write_all_to_excel("output/Audit_Latest.xlsx", annotations)
        
        # Persist to DB (for finalize):
        sync.persist_to_db(annotations)
    """
    
    def __init__(self, db_path: str | Path = "output/audit_history.db"):
        """Initialize annotation sync service."""
        self.db_path = Path(db_path)
        logger.info("AnnotationSyncService initialized")
    
    def read_all_from_excel(self, excel_path: Path | str) -> dict[str, dict]:
        """
        Read all annotations from all configured sheets in Excel.
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            Dict of {entity_key: {field_name: value}}
        """
        from openpyxl import load_workbook
        
        excel_path = Path(excel_path)
        all_annotations: dict[str, dict] = {}
        
        if not excel_path.exists():
            logger.warning("Excel file not found: %s", excel_path)
            return all_annotations
        
        try:
            wb = load_workbook(excel_path, read_only=True, data_only=True)
        except Exception as e:
            logger.error("Failed to open Excel file: %s", e)
            return all_annotations
        
        for sheet_name, config in SHEET_ANNOTATION_CONFIG.items():
            if sheet_name not in wb.sheetnames:
                continue
            
            ws = wb[sheet_name]
            sheet_annotations = self._read_sheet_annotations(ws, config)
            
            for entity_key, fields in sheet_annotations.items():
                # Prefix with entity type for uniqueness
                full_key = f"{config['entity_type']}|{entity_key}"
                all_annotations[full_key] = fields
        
        wb.close()
        logger.info("Read %d annotations from %d sheets", 
                    len(all_annotations), len(wb.sheetnames))
        return all_annotations
    
    def _read_sheet_annotations(
        self, ws, config: dict
    ) -> dict[str, dict]:
        """
        Read annotations from a single worksheet.
        
        Uses header row to find column positions dynamically.
        """
        annotations: dict[str, dict] = {}
        
        # Get header row to find column indices
        header_row = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))[0]
        if not header_row:
            return annotations
        
        # Map header names to column indices (0-indexed)
        header_map = {}
        for idx, header in enumerate(header_row):
            if header:
                # Normalize header (strip whitespace, handle emojis)
                clean_header = str(header).strip()
                # Remove common prefixes/emojis
                for prefix in ["⏳ ", "✅ ", "⚠️ ", "❌ "]:
                    clean_header = clean_header.replace(prefix, "")
                header_map[clean_header] = idx
        
        # Find key column indices
        key_indices = []
        for key_col in config["key_cols"]:
            if key_col in header_map:
                key_indices.append(header_map[key_col])
            else:
                # Try partial match
                for h, idx in header_map.items():
                    if key_col.lower() in h.lower():
                        key_indices.append(idx)
                        break
        
        if len(key_indices) != len(config["key_cols"]):
            logger.warning("Could not find all key columns for %s sheet", ws.title)
            return annotations
        
        # Find editable column indices
        editable_indices = {}
        for col_name, field_name in config["editable_cols"].items():
            if col_name in header_map:
                editable_indices[field_name] = header_map[col_name]
            else:
                # Try partial match
                for h, idx in header_map.items():
                    if col_name.lower() in h.lower():
                        editable_indices[field_name] = idx
                        break
        
        # Find action indicator column (column 1 with header containing ⏳)
        action_col_idx = None
        for h, idx in header_map.items():
            if "⏳" in str(h):
                action_col_idx = idx
                break
        
        # Read data rows
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or all(v is None for v in row):
                continue
            
            # Build entity key from key columns
            key_parts = []
            for idx in key_indices:
                val = row[idx] if idx < len(row) else None
                # Normalize: "(Default)" -> ""
                if val == "(Default)" or val is None:
                    key_parts.append("")
                else:
                    key_parts.append(str(val))
            
            entity_key = "|".join(key_parts)
            
            # Extract editable fields
            fields = {}
            has_any_value = False
            for field_name, col_idx in editable_indices.items():
                if col_idx < len(row):
                    val = row[col_idx]
                    if val is not None and str(val).strip():
                        fields[field_name] = val
                        has_any_value = True
            
            # Check if this row has action indicator (⏳ means needs action = FAIL/WARN)
            # This is used by detect_exception_changes to only log exceptions for FAIL items
            if action_col_idx is not None and action_col_idx < len(row):
                action_val = row[action_col_idx]
                # ⏳ = needs action (FAIL), ✅ = documented exception
                if action_val and "⏳" in str(action_val):
                    fields["action_needed"] = True
                elif action_val and "✅" in str(action_val):
                    # Already documented, but was previously a FAIL
                    fields["action_needed"] = True
            
            # Only store if there are actual annotations
            if has_any_value:
                annotations[entity_key] = fields
        
        logger.debug("Read %d annotations from %s sheet", len(annotations), ws.title)
        return annotations
    
    def write_all_to_excel(
        self, excel_path: Path | str, annotations: dict[str, dict]
    ) -> int:
        """
        Write annotations back to Excel file.
        
        Args:
            excel_path: Path to Excel file
            annotations: Dict from read_all_from_excel
            
        Returns:
            Number of cells updated
        """
        from openpyxl import load_workbook
        
        excel_path = Path(excel_path)
        if not excel_path.exists():
            logger.warning("Excel file not found: %s", excel_path)
            return 0
        
        try:
            wb = load_workbook(excel_path)
        except Exception as e:
            logger.error("Failed to open Excel file for writing: %s", e)
            return 0
        
        total_updated = 0
        
        for sheet_name, config in SHEET_ANNOTATION_CONFIG.items():
            if sheet_name not in wb.sheetnames:
                continue
            
            ws = wb[sheet_name]
            entity_type = config["entity_type"]
            
            # Filter annotations for this sheet
            sheet_annotations = {
                k.split("|", 1)[1]: v 
                for k, v in annotations.items() 
                if k.startswith(f"{entity_type}|")
            }
            
            if sheet_annotations:
                count = self._write_sheet_annotations(ws, config, sheet_annotations)
                total_updated += count
        
        try:
            wb.save(excel_path)
            logger.info("Wrote %d annotation cells to %s", total_updated, excel_path)
        except Exception as e:
            logger.error("Failed to save Excel file: %s", e)
            return 0
        
        wb.close()
        return total_updated
    
    def _write_sheet_annotations(
        self, ws, config: dict, annotations: dict[str, dict]
    ) -> int:
        """Write annotations to a single worksheet."""
        updated = 0
        
        # Get header row to find column indices
        header_row = [cell.value for cell in ws[1]]
        if not header_row:
            return 0
        
        # Map header names to column indices (1-indexed for openpyxl write)
        header_map = {}
        for idx, header in enumerate(header_row):
            if header:
                clean_header = str(header).strip()
                for prefix in ["⏳ ", "✅ ", "⚠️ ", "❌ "]:
                    clean_header = clean_header.replace(prefix, "")
                header_map[clean_header] = idx + 1  # 1-indexed
        
        # Find key column indices
        key_indices = []
        for key_col in config["key_cols"]:
            for h, idx in header_map.items():
                if key_col.lower() in h.lower():
                    key_indices.append(idx)
                    break
        
        # Find editable column indices (1-indexed)
        editable_indices = {}
        for col_name, field_name in config["editable_cols"].items():
            for h, idx in header_map.items():
                if col_name.lower() in h.lower():
                    editable_indices[field_name] = idx
                    break
        
        # Find action indicator column (usually column 1 with header "⏳")
        action_col_idx = None
        for h, idx in header_map.items():
            if "⏳" in str(h) or h == "":  # Action column header is usually just ⏳
                action_col_idx = idx
                break
        
        # Check if this sheet has a justification field
        has_justification = "justification" in config["editable_cols"].values()
        
        # Iterate through data rows and update matching cells
        for row_num in range(2, ws.max_row + 1):
            # Build entity key from key columns
            key_parts = []
            for col_idx in key_indices:
                cell_val = ws.cell(row=row_num, column=col_idx).value
                if cell_val == "(Default)" or cell_val is None:
                    key_parts.append("")
                else:
                    key_parts.append(str(cell_val))
            
            entity_key = "|".join(key_parts)
            
            # Check if we have annotations for this row
            if entity_key in annotations:
                row_annotations = annotations[entity_key]
                for field_name, col_idx in editable_indices.items():
                    if field_name in row_annotations:
                        ws.cell(row=row_num, column=col_idx).value = row_annotations[field_name]
                        updated += 1
                
                # If this row has justification filled, update action indicator (⏳→✅)
                if has_justification and action_col_idx:
                    justification = row_annotations.get("justification", "")
                    if justification and str(justification).strip():
                        # Import styling function
                        from autodbaudit.infrastructure.excel.base import apply_exception_documented_styling
                        apply_exception_documented_styling(ws.cell(row=row_num, column=action_col_idx))
                        updated += 1
        
        return updated
    
    def persist_to_db(self, annotations: dict[str, dict]) -> int:
        """
        Persist all annotations to SQLite database.
        
        Args:
            annotations: Dict from read_all_from_excel
            
        Returns:
            Number of annotations saved
        """
        import sqlite3
        from autodbaudit.infrastructure.sqlite.schema import set_annotation
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        count = 0
        for full_key, fields in annotations.items():
            parts = full_key.split("|", 1)
            if len(parts) != 2:
                continue
            
            entity_type, entity_key = parts
            
            for field_name, value in fields.items():
                if value is not None:
                    # Convert datetime to string if needed
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    
                    set_annotation(
                        connection=conn,
                        entity_type=entity_type,
                        entity_key=entity_key,
                        field_name=field_name,
                        field_value=str(value),
                    )
                    count += 1
        
        conn.close()
        logger.info("Persisted %d annotations to database", count)
        return count
    
    def load_from_db(self) -> dict[str, dict]:
        """
        Load all annotations from SQLite database.
        
        Returns:
            Dict of {entity_type|entity_key: {field_name: value}}
        """
        import sqlite3
        
        annotations: dict[str, dict] = {}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute(
            "SELECT entity_type, entity_key, field_name, field_value FROM annotations"
        ).fetchall()
        
        for row in rows:
            full_key = f"{row['entity_type']}|{row['entity_key']}"
            if full_key not in annotations:
                annotations[full_key] = {}
            annotations[full_key][row["field_name"]] = row["field_value"]
        
        conn.close()
        logger.info("Loaded %d annotation entries from database", len(annotations))
        return annotations
    
    def detect_exception_changes(
        self,
        old_annotations: dict[str, dict],
        new_annotations: dict[str, dict],
    ) -> list[dict]:
        """
        Compare annotations to detect new/changed justifications for FAIL items.
        
        Only logs as "exception" when an item that had a pending action (⏳)
        now has justification. Items that were already PASS are just notes,
        not exceptions.
        
        Args:
            old_annotations: Previous annotations from DB
            new_annotations: Current annotations from Excel
            
        Returns:
            List of {entity_key, entity_type, justification, is_new}
        """
        exceptions = []
        
        for full_key, fields in new_annotations.items():
            # Check if this has justification field
            justification = fields.get("justification", "").strip()
            if not justification:
                continue
            
            # Check if this row had action_needed = True (was showing ⏳)
            # This indicates it was a FAIL/WARN item needing attention
            # If not present, we assume it's not an exception (just a note on PASS item)
            action_needed = fields.get("action_needed", False)
            
            # Only treat as exception if it was marked as needing action
            # If action_needed is not set (None/False), skip - it's just a note
            if not action_needed:
                continue
            
            # Check if this is NEW or CHANGED
            old_fields = old_annotations.get(full_key, {})
            old_justification = old_fields.get("justification", "").strip()
            
            if justification != old_justification:
                # Parse entity key
                parts = full_key.split("|", 1)
                if len(parts) == 2:
                    entity_type, entity_key = parts
                    exceptions.append({
                        "full_key": full_key,
                        "entity_type": entity_type,
                        "entity_key": entity_key,
                        "justification": justification,
                        "is_new": not old_justification,
                    })
                    logger.info(
                        "Exception %s: %s - %s",
                        "added" if not old_justification else "updated",
                        entity_type,
                        entity_key[:50],
                    )
        
        return exceptions

