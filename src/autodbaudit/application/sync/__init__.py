"""
Sync Package - Modular Annotation Synchronization.

Provides bidirectional synchronization of user annotations
between Excel reports and SQLite database.

This package replaces the monolithic annotation_sync.py with
clean, modular components following single-responsibility principle.

Package Structure:
    service.py      - AnnotationSyncService (main orchestrator)
    config.py       - Sheet configuration (deprecated, use sheet_registry)
    excel_reader.py - Read annotations from Excel worksheets
    excel_writer.py - Write annotations to Excel worksheets
    db_ops.py       - SQLite read/write operations
    differ.py       - Detect changes between annotation states
    key_builder.py  - Entity key normalization and building

Usage:
    from autodbaudit.application.sync import AnnotationSyncService

    sync = AnnotationSyncService("output/audit_history.db")
    annotations = sync.read_all_from_excel("report.xlsx")
    sync.persist_to_db(annotations)
"""

from autodbaudit.application.sync.service import AnnotationSyncService

__all__ = ["AnnotationSyncService"]
