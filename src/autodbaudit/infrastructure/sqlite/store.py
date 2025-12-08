"""
SQLite-based history store for audit persistence.

Provides CRUD operations for:
- Audit runs
- Servers and instances
- Audit run ↔ instance relationships

Uses stdlib sqlite3 with no ORM.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.infrastructure.sql.connector import SqlServerInfo

from autodbaudit.domain.models import AuditRun, Server, Instance

logger = logging.getLogger(__name__)

# Schema version - increment when making breaking changes
SCHEMA_VERSION = 1


class HistoryStore:
    """
    SQLite-backed storage for audit history.
    
    Usage:
        store = HistoryStore(Path("output/history.db"))
        store.initialize_schema()
        
        run = store.begin_audit_run(organization="Acme Corp")
        server = store.upsert_server("PROD-SQL01")
        instance = store.upsert_instance(server, sql_info)
        store.link_instance_to_run(run.id, instance.id)
        store.complete_audit_run(run.id, "completed")
    """
    
    def __init__(self, db_path: Path | str) -> None:
        """
        Initialize history store.
        
        Args:
            db_path: Path to SQLite database file (created if not exists)
        """
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None
        logger.info("HistoryStore initialized: %s", self.db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Use Row factory for dict-like access
            self._connection.row_factory = sqlite3.Row
            logger.debug("Database connection established")
        return self._connection
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")
    
    # ========================================================================
    # Schema Management
    # ========================================================================
    
    def initialize_schema(self) -> None:
        """
        Create database tables if they don't exist.
        
        Safe to call multiple times - uses CREATE TABLE IF NOT EXISTS.
        """
        conn = self._get_connection()
        
        # Audit runs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                organization TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                config_hash TEXT
            )
        """)
        
        # Servers table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL UNIQUE,
                ip_address TEXT
            )
        """)
        
        # Instances table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                instance_name TEXT NOT NULL DEFAULT '',
                version TEXT,
                version_major INTEGER,
                edition TEXT,
                product_level TEXT,
                FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
                UNIQUE (server_id, instance_name)
            )
        """)
        
        # Junction table: which instances were audited in which run
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_run_instances (
                audit_run_id INTEGER NOT NULL,
                instance_id INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                PRIMARY KEY (audit_run_id, instance_id),
                FOREIGN KEY (audit_run_id) REFERENCES audit_runs(id) ON DELETE CASCADE,
                FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
            )
        """)
        
        # Schema metadata (for future migrations)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Store schema version
        conn.execute("""
            INSERT OR REPLACE INTO schema_meta (key, value)
            VALUES ('version', ?)
        """, (str(SCHEMA_VERSION),))
        
        conn.commit()
        logger.info("Database schema initialized (version %d)", SCHEMA_VERSION)
    
    # ========================================================================
    # Audit Run Operations
    # ========================================================================
    
    def begin_audit_run(
        self,
        organization: str | None = None,
        config_hash: str | None = None
    ) -> AuditRun:
        """
        Start a new audit run.
        
        Args:
            organization: Organization name (optional)
            config_hash: Hash of config file for reproducibility
            
        Returns:
            New AuditRun with id populated
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        cursor = conn.execute("""
            INSERT INTO audit_runs (started_at, organization, status, config_hash)
            VALUES (?, ?, 'running', ?)
        """, (now, organization, config_hash))
        
        conn.commit()
        run_id = cursor.lastrowid
        
        run = AuditRun(
            id=run_id,
            started_at=datetime.fromisoformat(now),
            organization=organization,
            status="running",
            config_hash=config_hash
        )
        
        logger.info("Audit run started: id=%d, org=%s", run_id, organization)
        return run
    
    def complete_audit_run(self, run_id: int, status: str) -> None:
        """
        Mark an audit run as complete.
        
        Args:
            run_id: Audit run ID
            status: Final status ("completed", "failed", "cancelled")
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute("""
            UPDATE audit_runs
            SET ended_at = ?, status = ?
            WHERE id = ?
        """, (now, status, run_id))
        
        conn.commit()
        logger.info("Audit run %d completed with status: %s", run_id, status)
    
    def get_audit_run(self, run_id: int) -> AuditRun | None:
        """Get an audit run by ID."""
        conn = self._get_connection()
        
        row = conn.execute("""
            SELECT id, started_at, ended_at, organization, status, config_hash
            FROM audit_runs WHERE id = ?
        """, (run_id,)).fetchone()
        
        if row is None:
            return None
        
        return AuditRun(
            id=row["id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            organization=row["organization"],
            status=row["status"],
            config_hash=row["config_hash"]
        )
    
    # ========================================================================
    # Server Operations
    # ========================================================================
    
    def upsert_server(
        self,
        hostname: str,
        ip_address: str | None = None
    ) -> Server:
        """
        Insert or update a server record.
        
        Args:
            hostname: Server hostname (unique key)
            ip_address: Optional IP address
            
        Returns:
            Server object with id populated
        """
        conn = self._get_connection()
        
        # Try to get existing server
        row = conn.execute(
            "SELECT id, hostname, ip_address FROM servers WHERE hostname = ?",
            (hostname,)
        ).fetchone()
        
        if row:
            # Update IP if provided and different
            if ip_address and row["ip_address"] != ip_address:
                conn.execute(
                    "UPDATE servers SET ip_address = ? WHERE id = ?",
                    (ip_address, row["id"])
                )
                conn.commit()
                logger.debug("Updated server %s IP to %s", hostname, ip_address)
            
            return Server(
                id=row["id"],
                hostname=row["hostname"],
                ip_address=ip_address or row["ip_address"]
            )
        
        # Insert new server
        cursor = conn.execute(
            "INSERT INTO servers (hostname, ip_address) VALUES (?, ?)",
            (hostname, ip_address)
        )
        conn.commit()
        
        server = Server(
            id=cursor.lastrowid,
            hostname=hostname,
            ip_address=ip_address
        )
        logger.debug("Created server: %s (id=%d)", hostname, server.id)
        return server
    
    # ========================================================================
    # Instance Operations
    # ========================================================================
    
    def upsert_instance(
        self,
        server: Server,
        instance_name: str,
        version: str,
        version_major: int,
        edition: str | None = None,
        product_level: str | None = None
    ) -> Instance:
        """
        Insert or update an instance record.
        
        Args:
            server: Server object (must have id)
            instance_name: Instance name (empty string for default)
            version: Full version string
            version_major: Major version number
            edition: SQL Server edition
            product_level: Service pack / CU level
            
        Returns:
            Instance object with id populated
        """
        if server.id is None:
            raise ValueError("Server must have an id before upserting instance")
        
        conn = self._get_connection()
        instance_name = instance_name or ""  # Normalize None to empty string
        
        # Check for existing instance
        row = conn.execute("""
            SELECT id FROM instances 
            WHERE server_id = ? AND instance_name = ?
        """, (server.id, instance_name)).fetchone()
        
        if row:
            # Update existing
            conn.execute("""
                UPDATE instances
                SET version = ?, version_major = ?, edition = ?, product_level = ?
                WHERE id = ?
            """, (version, version_major, edition, product_level, row["id"]))
            conn.commit()
            
            instance = Instance(
                id=row["id"],
                server_id=server.id,
                instance_name=instance_name,
                version=version,
                version_major=version_major,
                edition=edition,
                product_level=product_level
            )
            logger.debug("Updated instance: %s\\%s", server.hostname, instance_name or "(default)")
        else:
            # Insert new
            cursor = conn.execute("""
                INSERT INTO instances 
                (server_id, instance_name, version, version_major, edition, product_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (server.id, instance_name, version, version_major, edition, product_level))
            conn.commit()
            
            instance = Instance(
                id=cursor.lastrowid,
                server_id=server.id,
                instance_name=instance_name,
                version=version,
                version_major=version_major,
                edition=edition,
                product_level=product_level
            )
            logger.debug("Created instance: %s\\%s (id=%d)", 
                        server.hostname, instance_name or "(default)", instance.id)
        
        return instance
    
    def upsert_instance_from_info(
        self,
        server: Server,
        info: SqlServerInfo
    ) -> Instance:
        """
        Convenience method to upsert from SqlServerInfo.
        
        Args:
            server: Server object
            info: SqlServerInfo from detect_version()
            
        Returns:
            Instance object
        """
        return self.upsert_instance(
            server=server,
            instance_name=info.instance_name or "",
            version=info.version,
            version_major=info.version_major,
            edition=info.edition,
            product_level=info.product_level
        )
    
    # ========================================================================
    # Audit Run ↔ Instance Linking
    # ========================================================================
    
    def link_instance_to_run(self, run_id: int, instance_id: int) -> None:
        """
        Record that an instance was audited in a specific run.
        
        Args:
            run_id: Audit run ID
            instance_id: Instance ID
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute("""
            INSERT OR REPLACE INTO audit_run_instances (audit_run_id, instance_id, checked_at)
            VALUES (?, ?, ?)
        """, (run_id, instance_id, now))
        
        conn.commit()
    
    def get_instances_for_run(self, run_id: int) -> list[tuple[Server, Instance]]:
        """
        Get all server/instance pairs audited in a specific run.
        
        Args:
            run_id: Audit run ID
            
        Returns:
            List of (Server, Instance) tuples
        """
        conn = self._get_connection()
        
        rows = conn.execute("""
            SELECT 
                s.id as server_id, s.hostname, s.ip_address,
                i.id as instance_id, i.instance_name, i.version, 
                i.version_major, i.edition, i.product_level
            FROM audit_run_instances ari
            JOIN instances i ON ari.instance_id = i.id
            JOIN servers s ON i.server_id = s.id
            WHERE ari.audit_run_id = ?
            ORDER BY s.hostname, i.instance_name
        """, (run_id,)).fetchall()
        
        results = []
        for row in rows:
            server = Server(
                id=row["server_id"],
                hostname=row["hostname"],
                ip_address=row["ip_address"]
            )
            instance = Instance(
                id=row["instance_id"],
                server_id=row["server_id"],
                instance_name=row["instance_name"],
                version=row["version"],
                version_major=row["version_major"],
                edition=row["edition"],
                product_level=row["product_level"]
            )
            results.append((server, instance))
        
        return results
