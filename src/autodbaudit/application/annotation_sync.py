"""
Annotation Sync Service.

Provides bidirectional synchronization of user annotations (Notes, Reasons, Dates)
between Excel reports and SQLite database.

Core Principles:
1. SQLite = Source of Truth for system data
2. Excel = UI for human annotations
3. Stable entity keys for reliable round-trip
4. Whitelist-only editable columns
5. All keys normalized to lowercase for case-insensitive matching
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from autodbaudit.domain.entity_key import (
    normalize_key_string,
    annotation_key_to_finding_key,
)

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
            "Last Reviewed": "last_reviewed",
        },
    },
    "SA Account": {
        "entity_type": "sa_account",
        "key_cols": ["Server", "Instance", "Current Name"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            "Notes": "notes",
        },
    },
    "Server Logins": {
        "entity_type": "login",
        "key_cols": ["Server", "Instance", "Login Name"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
    },
    "Sensitive Roles": {
        "entity_type": "server_role_member",
        # Key includes Role to disambiguate same member in multiple roles
        "key_cols": ["Server", "Instance", "Role", "Member"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
    },
    "Configuration": {
        "entity_type": "config",
        "key_cols": ["Server", "Instance", "Setting"],
        "editable_cols": {
            "Review Status": "review_status",
            "Exception Reason": "justification",  # Config uses 'Exception Reason'
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            # No Notes column in Excel for this sheet
        },
    },
    "Services": {
        "entity_type": "service",
        "key_cols": ["Server", "Instance", "Service Name"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            # No Notes column in Excel for this sheet
        },
    },
    "Databases": {
        "entity_type": "database",
        "key_cols": ["Server", "Instance", "Database"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            "Notes": "notes",
        },
    },
    "Database Users": {
        "entity_type": "db_user",
        "key_cols": ["Server", "Instance", "Database", "User Name"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            "Notes": "notes",
        },
    },
    "Database Roles": {
        "entity_type": "db_role",
        "key_cols": ["Server", "Instance", "Database", "Role", "Member"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            # No Notes column in Excel for this sheet
        },
    },
    "Permission Grants": {
        "entity_type": "permission",
        # Key includes Database + Entity Name to disambiguate same permission on different objects
        "key_cols": [
            "Server",
            "Instance",
            "Scope",
            "Database",
            "Grantee",
            "Permission",
            "Entity Name",
        ],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            "Notes": "notes",
        },
    },
    "Orphaned Users": {
        "entity_type": "orphaned_user",
        "key_cols": ["Server", "Instance", "Database", "User Name"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            # No Notes column in Excel for this sheet
        },
    },
    "Linked Servers": {
        "entity_type": "linked_server",
        # Include logins to prevent collision if multiple mappings exist per LS
        "key_cols": [
            "Server",
            "Instance",
            "Linked Server",
            "Local Login",
            "Remote Login",
        ],
        "editable_cols": {
            "Review Status": "review_status",
            "Purpose": "purpose",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
            # No Notes column in Excel for this sheet
        },
    },
    "Triggers": {
        "entity_type": "trigger",
        # Key includes Scope to distinguish SERVER vs DATABASE level triggers
        # Added Event to distinguish multiple events for same trigger
        "key_cols": [
            "Server",
            "Instance",
            "Scope",
            "Database",
            "Trigger Name",
            "Event",
        ],
        "editable_cols": {
            "Review Status": "review_status",
            "Notes": "notes",  # Purpose/notes for this trigger
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
    },
    "Client Protocols": {
        "entity_type": "protocol",
        "key_cols": ["Server", "Instance", "Protocol"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",
        },
    },
    "Backups": {
        "entity_type": "backup",
        "key_cols": ["Server", "Instance", "Database", "Recovery Model"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            "Notes": "notes",
        },
    },
    "Audit Settings": {
        "entity_type": "audit_settings",
        "key_cols": ["Server", "Instance", "Setting"],
        "editable_cols": {
            "Review Status": "review_status",
            "Justification": "justification",
            "Last Reviewed": "last_reviewed",  # Excel has 'Last Reviewed'
            "Notes": "notes",
        },
    },
    "Encryption": {
        "entity_type": "encryption",
        # Column names match writer: "Key Type" and "Key Name"
        "key_cols": ["Server", "Instance", "Key Type", "Key Name"],
        "editable_cols": {
            "Notes": "notes",
        },
    },
    "Actions": {
        "entity_type": "action",
        "key_cols": ["ID"],  # Use DB ID for unique, reliable row matching
        "editable_cols": {
            "Detected Date": "action_date",  # User can override detected date
            "Notes": "notes",  # User commentary
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
                # Prefix with entity type for uniqueness (lowercase for consistency)
                entity_type = str(config["entity_type"]).lower()
                full_key = f"{entity_type}|{entity_key}"
                all_annotations[full_key] = fields

        wb.close()
        logger.info(
            "Read %d annotations from %d sheets",
            len(all_annotations),
            len(wb.sheetnames),
        )
        return all_annotations

    def _read_sheet_annotations(self, ws, config: dict) -> dict[str, dict]:
        """
        Read annotations from a single worksheet.

        Uses header row to find column positions dynamically.
        Handles merged cells by tracking last non-empty values for key columns.
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
        found_keys = 0

        # Try primary key config
        for key_col in config["key_cols"]:
            found = False
            if key_col in header_map:
                key_indices.append(header_map[key_col])
                found = True
            else:
                # Try EXACT match first (case-insensitive)
                exact_found = False
                for h, idx in header_map.items():
                    if key_col.lower() == h.lower():
                        key_indices.append(idx)
                        found = True
                        exact_found = True
                        break
                # Only use partial match if exact match failed
                if not exact_found:
                    for h, idx in header_map.items():
                        # Partial match but avoid substring collisions
                        if key_col.lower() in h.lower() and len(key_col) >= len(h) // 2:
                            key_indices.append(idx)
                            found = True
                            break
            if found:
                found_keys += 1

        # Fallback for Backups (backward compatibility for existing reports)
        if found_keys != len(config["key_cols"]) and config["entity_type"] == "backup":
            logger.warning("Backups sheet missing 'Recovery Model'. Trying legacy key.")
            legacy_keys = ["Server", "Instance", "Database"]
            key_indices = []
            found_keys = 0
            for key_col in legacy_keys:
                if key_col in header_map:
                    key_indices.append(header_map[key_col])
                    found_keys += 1

            # If we found the legacy keys, valid.
            # Note: This means entity_key will be "Server|Instance|Database"
            # Logic later needs to handle this or migration.
            if found_keys == 3:
                logger.info("Using legacy key for Backups sheet.")

        if found_keys != len(key_indices) and found_keys == 0:
            # Logic above: key_indices length might differ if we fallback?
            # Actually, key_indices contains the indices. found_keys tracks count.
            # If we used fallback, key_indices has 3 items. found_keys is 3.
            pass

        # Strict check: Did we find enough keys for strict match OR fallback match?
        # If we are using standard config, we need match.
        required_keys = (
            3
            if (config["entity_type"] == "backup" and len(key_indices) == 3)
            else len(config["key_cols"])
        )

        if len(key_indices) != required_keys:
            logger.warning(
                "Could not find all key columns for %s sheet (Found %d/%d)",
                ws.title,
                len(key_indices),
                required_keys,
            )
            return annotations

        # Find editable column indices
        editable_indices = {}
        missing_cols = []
        for col_name, field_name in config["editable_cols"].items():
            found = False
            # Try EXACT match first (case-sensitive)
            if col_name in header_map:
                editable_indices[field_name] = header_map[col_name]
                found = True
            else:
                # Try EXACT match (case-insensitive)
                for h, idx in header_map.items():
                    if col_name.lower() == h.lower():
                        editable_indices[field_name] = idx
                        found = True
                        break
                # Only use partial match if exact match failed
                if not found:
                    for h, idx in header_map.items():
                        if col_name.lower() in h.lower():
                            editable_indices[field_name] = idx
                            found = True
                            break
            if not found:
                missing_cols.append(col_name)

        # Log warning if columns are missing
        if missing_cols:
            logger.warning(
                "Sheet %s: Could not find editable columns: %s (Available: %s)",
                ws.title,
                missing_cols,
                list(header_map.keys()),
            )

        # Find action indicator column (column with header containing ⏳)
        # MUST use raw header_row because header_map keys are stripped of emojis
        action_col_idx = None
        status_col_idx = None  # Track Status column for discrepancy detection
        for idx, val in enumerate(header_row):
            if val:
                val_str = str(val)
                if "⏳" in val_str:
                    action_col_idx = idx
                # Find Status column (may contain PASS/FAIL/WARN)
                if val_str.strip().lower() == "status" or val_str.strip() == "Status":
                    status_col_idx = idx

        logger.warning(
            f"DEBUG: Sheet {ws.title} ActionCol={action_col_idx} StatusCol={status_col_idx}"
        )

        # Track last non-empty values for key columns (handles merged cells)
        # When cells are merged, only first row has value, rest are None
        last_key_values = [""] * len(key_indices)

        # Read data rows
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or all(v is None for v in row):
                continue

            # Build entity key from key columns
            # Use last non-empty value if current is None (merged cell)
            key_parts = []
            for i, idx in enumerate(key_indices):
                val = row[idx] if idx < len(row) else None

                # If value is None, use last known value (merged cell case)
                if val is None:
                    val = last_key_values[i]
                else:
                    # Normalize: "(Default)" -> ""
                    if val == "(Default)":
                        val = ""
                    else:
                        val = str(val)
                    # Update last known value
                    last_key_values[i] = val

                key_parts.append(val)

            # Build entity key and normalize to lowercase for case-insensitive matching
            entity_key = "|".join(str(p).lower() for p in key_parts)

            # Skip if we couldn't build a valid key
            if not any(key_parts):
                continue

            # Extract editable fields
            fields = {}
            has_any_value = False
            for field_name, col_idx in editable_indices.items():
                if col_idx < len(row):
                    val = row[col_idx]

                    # Robust Parsing & Casting
                    # Robust Parsing & Casting
                    val_str = str(val).strip() if val is not None else ""

                    if val_str:
                        # A) Date Fields: Use robust parser
                        if (
                            "date" in field_name.lower()
                            or "revised" in field_name.lower()
                            or "reviewed" in field_name.lower()
                        ):
                            from autodbaudit.infrastructure.excel.base import (
                                parse_datetime_flexible,
                            )

                            parsed_date = parse_datetime_flexible(
                                val, log_errors=True, context=f"{ws.title}|{entity_key}"
                            )
                            if parsed_date:
                                fields[field_name] = parsed_date
                                has_any_value = True

                        # B) Text Fields: Strict String Cast
                        else:
                            fields[field_name] = val_str
                            has_any_value = True
                    else:
                        # Capture empty strings to allow clearing annotations in DB
                        fields[field_name] = ""
                        has_any_value = True

            # AUTO-STATUS: Check Justification ONLY (notes/purpose are documentation, NOT exception triggers)
            raw_just = fields.get("justification")

            # Check review status for "Exception"
            raw_status = fields.get("review_status")
            is_explicit_exception = raw_status and "Exception" in str(raw_status)

            if (raw_just and str(raw_just).strip()) or is_explicit_exception:
                from autodbaudit.infrastructure.excel.base import STATUS_VALUES

                # We enforce Exception status so it syncs back to Excel next time
                fields["review_status"] = STATUS_VALUES.EXCEPTION
                # NOTE: Do NOT set action_needed here - that's only for actual discrepant rows
                # Justification on a PASS row is just documentation
                has_any_value = True
                logger.debug(
                    "Set review_status to Exception for %s (justification/status present)",
                    entity_key,
                )

            # If explicit "Exception" status but no justification, we still treat as documented
            # (Logic handled in detect_exception_changes)

            # Check if this row has action indicator (⏳ means needs action = FAIL/WARN)
            # This is used by detect_exception_changes to only log exceptions for FAIL items
            if action_col_idx is not None and action_col_idx < len(row):
                action_val = row[action_col_idx]
                if "Sensitive-Role" in entity_key:
                    logger.warning(
                        f"DEBUG: {entity_key} ActionVal='{action_val}' ActionCol={action_col_idx}"
                    )
                # ⏳ = needs action (FAIL), ✅ = documented exception
                if action_val and "⏳" in str(action_val):
                    fields["action_needed"] = True
                elif action_val and "✅" in str(action_val):
                    # Already documented, but was previously a FAIL
                    fields["action_needed"] = True

            # Read actual Status column value for discrepancy detection
            if status_col_idx is not None and status_col_idx < len(row):
                status_val = row[status_col_idx]
                if status_val:
                    fields["status"] = str(status_val).strip()

            # Only store if there are actual annotations
            if has_any_value:
                # IMPORTANT: Store with UNPREFIXED key for backward compatibility
                # The write_all_to_excel expects unprefixed keys to match Excel rows
                # DB persistence in persist_to_db() adds the prefix when saving
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
        except PermissionError:
            logger.error(
                f"❌ Cannot write to '{excel_path.name}' - file is open!\n"
                f"   Please close the file in Excel and try again."
            )
            return 0
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
        logger.warning(
            f"DEBUG: _write_sheet_annotations for {ws.title} with {len(annotations)} items"
        )

        # Get header row to find column indices
        header_row = [cell.value for cell in ws[1]]
        if not header_row:
            logger.warning(f"DEBUG: No header row found in {ws.title}")
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
            # Try EXACT match first
            exact_found = False
            for h, idx in header_map.items():
                if key_col.lower() == h.lower():
                    key_indices.append(idx)
                    exact_found = True
                    break
            # Only use partial match if exact match failed
            if not exact_found:
                for h, idx in header_map.items():
                    # Partial match but avoid substring collisions
                    if key_col.lower() in h.lower() and len(key_col) >= len(h) // 2:
                        key_indices.append(idx)
                        break

        if len(key_indices) != len(config["key_cols"]):
            logger.warning(f"DEBUG: Header mismatch in {ws.title}. Start Search.")

        # Find editable column indices (1-indexed)
        editable_indices = {}
        for col_name, field_name in config["editable_cols"].items():
            # Try EXACT match first
            exact_found = False
            for h, idx in header_map.items():
                if col_name.lower() == h.lower():
                    editable_indices[field_name] = idx
                    exact_found = True
                    break
            # Only use partial match if exact match failed
            if not exact_found:
                for h, idx in header_map.items():
                    if col_name.lower() in h.lower():
                        editable_indices[field_name] = idx
                        break

        # Find action indicator column (usually column 1 with header "⏳")
        action_col_idx = None
        status_col_idx = None  # Column with PASS/FAIL/WARN values
        for h, idx in header_map.items():
            if "⏳" in str(h) or h == "":  # Action column header is usually just ⏳
                action_col_idx = idx
            if h.strip().lower() == "status":
                status_col_idx = idx

        # Check if this sheet has a justification field
        has_justification = "justification" in config["editable_cols"].values()

        # Track last non-empty values for key columns (handles merged cells)
        last_key_values = [""] * len(key_indices)

        # Iterate through data rows and update matching cells
        rows_processed = 0
        for row_num in range(2, ws.max_row + 1):
            rows_processed += 1
            # Build entity key from key columns
            # Handle merged cells by using last non-empty value
            key_parts = []
            for i, col_idx in enumerate(key_indices):
                cell_val = ws.cell(row=row_num, column=col_idx).value

                if cell_val is None:
                    # Merged cell - use last known value
                    key_parts.append(last_key_values[i])
                elif cell_val == "(Default)":
                    key_parts.append("")
                    last_key_values[i] = ""
                else:
                    val = str(cell_val)
                    key_parts.append(val)
                    last_key_values[i] = val

            entity_key = "|".join(key_parts)
            # Normalize to lowercase for consistent matching with DB keys
            entity_key_lower = entity_key.lower()

            # Skip if we couldn't build a valid key
            if not any(key_parts):
                continue

            # Check if we have annotations for this row (use lowercase key)
            if entity_key_lower in annotations:
                row_annotations = annotations[entity_key_lower]
                for field_name, col_idx in editable_indices.items():
                    if field_name in row_annotations:
                        val = row_annotations[field_name]

                        # Convert ISO date strings back to datetime objects for Excel
                        if (
                            val
                            and isinstance(val, str)
                            and (
                                "date" in field_name.lower()
                                or "revised" in field_name.lower()
                                or "reviewed" in field_name.lower()
                            )
                        ):
                            from autodbaudit.infrastructure.excel.base import (
                                parse_datetime_flexible,
                            )

                            dt = parse_datetime_flexible(val, log_errors=False)
                            if dt:
                                val = dt

                        ws.cell(row=row_num, column=col_idx).value = val
                        updated += 1

                # Update action indicator (⏳→✅) ONLY if:
                # - Row is FAIL/WARN (discrepant), AND
                # - justification is filled OR review_status is "Exception"
                # PASS rows: keep justification as text but NO indicator, CLEAR Exception status
                if has_justification and action_col_idx:
                    justification = row_annotations.get("justification", "")
                    review_status = row_annotations.get("review_status", "")
                    has_just = justification and str(justification).strip()
                    has_exception = review_status and "Exception" in str(review_status)

                    # Check row status - must be discrepant to apply indicator
                    is_discrepant = False
                    status_val = None
                    if status_col_idx:
                        status_val = ws.cell(row=row_num, column=status_col_idx).value
                        if status_val:
                            status_str = str(status_val).upper()
                            is_discrepant = status_str in ("FAIL", "WARN", "⏳", "⚠")

                    # Fallback: Check Action Indicator Column (for sheets like Logins)
                    if not is_discrepant and action_col_idx:
                        action_val = ws.cell(row=row_num, column=action_col_idx).value
                        if action_val:
                            s_val = str(action_val)
                            if "⏳" in s_val or "✓" in s_val or "✅" in s_val:
                                is_discrepant = True

                    if (has_just or has_exception) and is_discrepant:
                        # DISCREPANT + (justification OR Exception status) = Valid Exception
                        from autodbaudit.infrastructure.excel.base import (
                            apply_exception_documented_styling,
                        )

                        apply_exception_documented_styling(
                            ws.cell(row=row_num, column=action_col_idx)
                        )
                        updated += 1
                        logger.warning(
                            "DEBUG: Updated Excel Indicator for %s (Just=%s, Exc=%s, Stat=%s, Row=%d)",
                            entity_key,
                            has_just,
                            has_exception,
                            status_val,
                            row_num,
                        )
                    elif is_discrepant and not (has_just or has_exception):
                        # Was an exception (or marked discrepant), but justification removed.
                        # Revert to Needs Action (⏳)
                        from autodbaudit.infrastructure.excel.base import (
                            apply_action_needed_styling,
                        )

                        apply_action_needed_styling(
                            ws.cell(row=row_num, column=action_col_idx),
                            needs_action=True,
                        )
                        updated += 1
                        logger.warning(
                            "DEBUG: Reverted Excel Indicator for %s (Just=%s, Exc=%s, Row=%d)",
                            entity_key,
                            has_just,
                            has_exception,
                            row_num,
                        )
                    elif has_exception and not is_discrepant:
                        # PASS row with Exception dropdown: CLEAR the exception status
                        # Per requirements: "Non-discrepant + Exception dropdown → Ignored, cleared"
                        # Keep justification as documentation (don't touch it)
                        review_status_col = editable_indices.get("review_status")
                        if review_status_col:
                            ws.cell(row=row_num, column=review_status_col).value = ""
                            logger.debug(
                                "Cleared Exception status for PASS row: %s", entity_key
                            )
                    else:
                        logger.warning(
                            "DEBUG: Skipped Indicator Update for %s (Just=%s, Exc=%s, Disc=%s, Stat=%s, Row=%d)",
                            entity_key,
                            has_just,
                            has_exception,
                            is_discrepant,
                            status_val,
                            row_num,
                        )
                    # Note: has_just and not is_discrepant → justification kept as documentation (no action needed)

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
            # Normalize to lowercase for consistent matching
            entity_type = row["entity_type"].lower() if row["entity_type"] else ""
            entity_key = row["entity_key"].lower() if row["entity_key"] else ""
            full_key = f"{entity_type}|{entity_key}"
            if full_key not in annotations:
                annotations[full_key] = {}
            annotations[full_key][row["field_name"]] = row["field_value"]

        conn.close()
        logger.info("Loaded %d annotation entries from database", len(annotations))
        return annotations

    def get_all_annotations(self) -> dict[str, dict]:
        """
        Get all annotations keyed by entity_key.

        This is an alias for load_from_db() to satisfy the AnnotationsProvider protocol
        expected by StatsService.

        Returns:
            Dict of {entity_type|entity_key: {field_name: value}}
        """
        return self.load_from_db()

    def detect_exception_changes(
        self,
        old_annotations: dict[str, dict],
        new_annotations: dict[str, dict],
        current_findings: list[dict] | None = None,
    ) -> list[dict]:
        """
        Compare annotations to detect new/changed/removed justifications for FAIL items.

        Only logs as "exception" when an item that had a pending action (⏳)
        now has justification. Items that were already PASS are just notes,
        not exceptions.

        Also detects REMOVED exceptions: when user clears BOTH Justification
        AND Review Status (reverts from Exception).

        Args:
            old_annotations: Previous annotations from DB
            new_annotations: Current annotations from Excel
            current_findings: Current findings from DB (for accurate PASS/FAIL status)

        Returns:
            List of {entity_key, entity_type, justification, is_new, change_type}
            where change_type is 'added', 'updated', or 'removed'
        """
        exceptions = []

        # Build findings map for status lookup with LOWERCASE keys
        # Key format in findings: entity_key like "SERVER|INSTANCE|entity_name"
        # Key format in annotations: "entity_type|SERVER|INSTANCE|entity_name"
        # We normalize ALL keys to lowercase for case-insensitive matching
        findings_status_map: dict[str, str] = {}
        if current_findings:
            for f in current_findings:
                raw_key = f.get("entity_key", "")
                # Normalize to lowercase for matching
                normalized_key = normalize_key_string(raw_key)
                findings_status_map[normalized_key] = f.get("status", "PASS")

        # Helper to check if DB annotation was already an exception
        # DB annotations don't have status field - just check justification/review_status
        def was_previously_exception(fields: dict) -> bool:
            if not fields:
                return False
            raw_just = fields.get("justification")
            justification = str(raw_just).strip() if raw_just else ""
            raw_status = fields.get("review_status", "")
            has_exception_status = "Exception" in str(raw_status)
            return bool(justification) or has_exception_status

        # Helper to check if Excel annotation qualifies as NEW exception
        # Must be DISCREPANT (FAIL/WARN) to count as exception
        def is_new_exception(fields: dict) -> bool:
            if not fields:
                return False

            # First check status - must be FAIL/WARN to be exception
            row_status = str(fields.get("status", "")).upper()
            is_discrepant = row_status in ("FAIL", "WARN", "⏳", "⚠")

            # Also treat as discrepant if action_needed was explicitly set
            if fields.get("action_needed", False):
                is_discrepant = True

            # If row is passing, it's NOT an exception (just documentation)
            if not is_discrepant:
                return False

            # Now check if it has justification or Exception status
            raw_just = fields.get("justification")
            justification = str(raw_just).strip() if raw_just else ""
            raw_status = fields.get("review_status", "")
            has_exception_status = "Exception" in str(raw_status)
            return bool(justification) or has_exception_status

        # 1. Detect NEW and UPDATED exceptions
        for full_key, fields in new_annotations.items():
            # Check if this has justification OR review_status set to Exception
            # Notes/Purpose are DOCUMENTATION ONLY, not exception triggers
            raw_just = fields.get("justification")
            justification = str(raw_just).strip() if raw_just else ""

            raw_review_status = fields.get("review_status", "")
            review_status = str(raw_review_status).strip() if raw_review_status else ""
            has_exception_status = "Exception" in review_status

            # Need at least one of: justification text OR exception status
            if not justification and not has_exception_status:
                continue

            # CRITICAL: Check if this row is actually DISCREPANT (FAIL/WARN)
            # PASS rows with justification are documentation only, NOT exceptions
            # Use findings_status_map for accurate lookup (not Excel status column)

            # Extract entity_key from full_key (remove entity_type prefix)
            # and normalize to lowercase for case-insensitive matching
            entity_type, finding_key = annotation_key_to_finding_key(full_key)
            normalized_finding_key = normalize_key_string(finding_key)

            # Look up actual status from findings (using normalized lowercase key)
            finding_status = findings_status_map.get(normalized_finding_key, "")

            # Debug: Log key matching for troubleshooting
            if justification or has_exception_status:
                logger.info(
                    "Exception candidate: %s -> finding_key=%s, status=%s",
                    full_key,
                    normalized_finding_key,
                    finding_status or "NOT_FOUND",
                )

            # Fallback to annotation's status field if no finding match
            if not finding_status:
                row_status = str(fields.get("status", "")).upper()
                # Check Status column - must be FAIL/WARN to be discrepant
                is_discrepant = row_status in ("FAIL", "WARN")
                # Also check for emoji indicators in status
                if "⏳" in row_status or "⚠" in row_status or "✗" in row_status:
                    is_discrepant = True
                # NOTE: Do NOT use action_needed here - that flag being True doesn't mean discrepant
                logger.debug(
                    "Using Excel status fallback for %s: status=%s, discrepant=%s",
                    full_key,
                    row_status,
                    is_discrepant,
                )
            else:
                is_discrepant = finding_status.upper() in ("FAIL", "WARN")

            # If row is passing and no explicit exception status, skip it
            # Keep the justification in DB as documentation for future reference
            if not is_discrepant:
                logger.debug(
                    "Skipping non-discrepant row with justification: %s (status=%s)",
                    full_key,
                    finding_status or "unknown",
                )
                continue

            # Check if this is NEW or CHANGED
            old_fields = old_annotations.get(full_key, {})
            old_raw = old_fields.get("justification")
            old_justification = str(old_raw).strip() if old_raw else ""

            old_status = old_fields.get("review_status", "")
            was_exception = was_previously_exception(old_fields)

            # Detect change: new/updated justification or new Exception status
            # Note: We do NOT check status_mismatch - finding status correctly stays FAIL
            # for exceptioned items. Checking status_mismatch caused duplicate detections.
            if justification != old_justification or (
                has_exception_status and not was_exception
            ):
                # Parse entity key
                parts = full_key.split("|", 1)
                if len(parts) == 2:
                    entity_type, entity_key = parts

                    if not was_exception:
                        change_type = "added"
                    else:
                        change_type = "updated"

                    exceptions.append(
                        {
                            "full_key": full_key,
                            "entity_type": entity_type,
                            "entity_key": entity_key,
                            "justification": justification,
                            "is_new": not was_exception,
                            "change_type": change_type,
                        }
                    )
                    logger.info(
                        "Exception %s: %s - %s",
                        change_type,
                        entity_type,
                        entity_key[:50],
                    )

        # 2. Detect REMOVED exceptions
        # A "removed exception" is when:
        #   - Row was discrepant (FAIL/WARN) with justification (was exception)
        #   - Row is STILL discrepant but user CLEARED the justification
        # NOT a "removed exception" if:
        #   - Row became PASS (that's a FIX, not removal)
        #   - Row was never discrepant (was just documentation)
        for full_key, old_fields in old_annotations.items():
            if not was_previously_exception(old_fields):
                continue  # Was not marked as exception before

            # Look up current finding status
            parts = full_key.split("|", 1)
            entity_key_for_lookup = parts[1] if len(parts) == 2 else full_key
            current_status = findings_status_map.get(entity_key_for_lookup, "")

            # If row is now PASS, this is a FIX - not a "removed exception"
            # If status is unknown/missing (not in current findings), assume FIX or GONE
            # The exception documentation becomes historical note
            if not current_status or current_status.upper() == "PASS":
                logger.debug(
                    "Row became PASS/Gone (%s), exception docs now historical: %s",
                    current_status,
                    entity_key_for_lookup[:50],
                )
                continue

            # Row is still discrepant - check if justification was cleared
            new_fields = new_annotations.get(full_key, {})
            new_just = new_fields.get("justification", "")
            new_status = new_fields.get("review_status", "")
            has_new_just = new_just and str(new_just).strip()
            has_new_exception = "Exception" in str(new_status)

            if has_new_just or has_new_exception:
                continue  # Still has exception documentation

            # User cleared both justification AND exception status on a FAIL row
            # This is a genuine "removed exception"
            if len(parts) == 2:
                entity_type, entity_key = parts
                old_just = old_fields.get("justification", "")

                exceptions.append(
                    {
                        "full_key": full_key,
                        "entity_type": entity_type,
                        "entity_key": entity_key,
                        "justification": "",  # Now empty
                        "old_justification": str(old_just).strip() if old_just else "",
                        "is_new": False,
                        "change_type": "removed",
                    }
                )
                logger.info(
                    "Exception removed: %s - %s",
                    entity_type,
                    entity_key[:50],
                )

        return exceptions
