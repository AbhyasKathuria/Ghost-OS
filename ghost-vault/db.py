"""Ghost Vault Database Management Layer.

Provides in-memory SQLite hydration, zero host disk footprint, atomic encrypted
disk persistence with fsync, rolling backups, and cross-platform audit logging.
"""

from datetime import datetime, timezone
import json
import os
import shutil
import sqlite3
from typing import Any, Dict, List, Optional

from ghost_core.schemas.scan import DiagnosticStatus, NormalizedScanPayload
from ghost_vault.crypto import (
    VaultCryptoError,
    encrypt_bytes,
    generate_recovery_key,
    pack_vault,
    unlock_vault,
)

SCHEMA_DDL = """
-- Machines Registry
CREATE TABLE IF NOT EXISTS machines (
    machine_fingerprint TEXT PRIMARY KEY,
    first_seen_utc TEXT NOT NULL,
    last_seen_utc TEXT NOT NULL,
    asset_tag TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Machine Identifiers & Anchors
CREATE TABLE IF NOT EXISTS machine_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_fingerprint TEXT NOT NULL,
    anchor_type TEXT NOT NULL,
    anchor_value TEXT NOT NULL,
    FOREIGN KEY(machine_fingerprint) REFERENCES machines(machine_fingerprint) ON DELETE CASCADE
);

-- Scan Sessions
CREATE TABLE IF NOT EXISTS scan_sessions (
    scan_id TEXT PRIMARY KEY,
    machine_fingerprint TEXT NOT NULL,
    platform TEXT NOT NULL,
    os_version TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    overall_health_score INTEGER NOT NULL,
    raw_payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(machine_fingerprint) REFERENCES machines(machine_fingerprint) ON DELETE CASCADE
);

-- Hardware Components Normalized Snapshots
CREATE TABLE IF NOT EXISTS hardware_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    category TEXT NOT NULL,
    component_index INTEGER NOT NULL DEFAULT 0,
    details_json TEXT NOT NULL,
    FOREIGN KEY(scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
);

-- Diagnostic Results
CREATE TABLE IF NOT EXISTS diagnostic_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    test_name TEXT NOT NULL,
    status TEXT NOT NULL,
    metric_value REAL,
    threshold REAL,
    evidence TEXT,
    recommendation TEXT,
    FOREIGN KEY(scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
);

-- Health Scores
CREATE TABLE IF NOT EXISTS health_scores (
    scan_id TEXT PRIMARY KEY,
    overall_score INTEGER NOT NULL,
    cpu_score INTEGER NOT NULL,
    ram_score INTEGER NOT NULL,
    storage_score INTEGER NOT NULL,
    battery_score INTEGER NOT NULL,
    thermal_score INTEGER NOT NULL,
    summary TEXT,
    FOREIGN KEY(scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
);

-- Maintenance & Service Records
CREATE TABLE IF NOT EXISTS maintenance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_fingerprint TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    technician_name TEXT,
    action_type TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(machine_fingerprint) REFERENCES machines(machine_fingerprint) ON DELETE CASCADE
);

-- Audit Events
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_scan_sessions_fingerprint ON scan_sessions(machine_fingerprint);
CREATE INDEX IF NOT EXISTS idx_diagnostic_results_scan ON diagnostic_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_hardware_components_scan ON hardware_components(scan_id);
"""


class GhostVaultDB:
    """Manages an in-memory SQLite database backed by an encrypted disk container."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        vault_path: str,
        master_key: bytes,
        vault_header: Dict[str, Any],
        recovery_key: Optional[str] = None,
    ):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._vault_path = os.path.abspath(vault_path)
        self._master_key = master_key
        self._vault_header = vault_header
        self._recovery_key = recovery_key
        self._is_open = True

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def recovery_key(self) -> Optional[str]:
        return self._recovery_key

    @property
    def vault_path(self) -> str:
        return self._vault_path

    @classmethod
    def create_new(
        cls,
        vault_path: str,
        password: str,
        recovery_key: Optional[str] = None,
        recovery_file_path: Optional[str] = None,
        time_cost: int = 2,
        memory_cost: int = 65536,
        parallelism: int = 2,
    ) -> "GhostVaultDB":
        """Initializes a brand new encrypted vault file and populates the schema."""
        vault_path = os.path.abspath(vault_path)
        os.makedirs(os.path.dirname(vault_path), exist_ok=True)

        if not recovery_key:
            recovery_key = generate_recovery_key()

        # Create in-memory database and run DDL
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_DDL)
        conn.commit()

        # Serialize memory DB
        plaintext_db = conn.serialize()

        # Pack into encrypted container
        container_bytes, master_key, final_recovery_key = pack_vault(
            plaintext_db=plaintext_db,
            password=password,
            recovery_key=recovery_key,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

        # Write container atomically
        cls._atomic_write(vault_path, container_bytes)

        # Optionally escrow recovery key to file
        if recovery_file_path:
            os.makedirs(os.path.dirname(os.path.abspath(recovery_file_path)), exist_ok=True)
            with open(recovery_file_path, "w", encoding="utf-8") as f:
                f.write(f"GHOST-OS VAULT EMERGENCY RECOVERY KEY\n")
                f.write(f"Created UTC: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"Key: {final_recovery_key}\n")
                f.write(f"\nKeep this key offline in a secure physical location.\n")

        # Parse header from container
        _, _, header = unlock_vault(container_bytes, password)

        instance = cls(
            conn=conn,
            vault_path=vault_path,
            master_key=master_key,
            vault_header=header,
            recovery_key=final_recovery_key,
        )
        instance.log_audit_event("vault_created", f"Initialized new encrypted vault at {vault_path}")
        instance.flush()
        return instance

    @classmethod
    def open_vault(cls, vault_path: str, secret: str) -> "GhostVaultDB":
        """Opens an existing encrypted vault file and hydratess it into RAM."""
        vault_path = os.path.abspath(vault_path)
        if not os.path.exists(vault_path):
            raise FileNotFoundError(f"Vault container does not exist: {vault_path}")

        with open(vault_path, "rb") as f:
            container_bytes = f.read()

        plaintext_db, master_key, header = unlock_vault(container_bytes, secret)

        # Hydrate directly into memory
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.deserialize(plaintext_db)
        conn.row_factory = sqlite3.Row

        # Ensure schema migrations or missing tables are created
        conn.executescript(SCHEMA_DDL)
        conn.commit()

        instance = cls(
            conn=conn,
            vault_path=vault_path,
            master_key=master_key,
            vault_header=header,
        )
        instance.log_audit_event("vault_unlocked", f"Decrypted into memory from {vault_path}")
        return instance

    def flush(self) -> None:
        """Serializes the in-memory SQLite database, encrypts it, and writes atomically with fsync."""
        if not self._is_open:
            raise VaultCryptoError("Cannot flush closed vault")

        # Commit pending changes
        self._conn.commit()

        # Serialize in-memory database to bytes
        db_bytes = self._conn.serialize()

        # Encrypt with master key
        enc_payload = encrypt_bytes(db_bytes, self._master_key)

        # Assemble container
        magic = b"GHOST_VAULT_V1\n"
        separator = b"\n--GHOST_PAYLOAD_START--\n"
        header_bytes = json.dumps(self._vault_header, indent=2).encode("utf-8")
        container_bytes = magic + header_bytes + separator + enc_payload

        # Rotate backups prior to atomic replace
        self._rotate_backups()

        # Write to .tmp and atomic rename
        self._atomic_write(self._vault_path, container_bytes)

    def _rotate_backups(self) -> None:
        """Maintains rolling encrypted backups (vault.bak.1 and vault.bak.2)."""
        if not os.path.exists(self._vault_path):
            return

        vault_dir = os.path.dirname(self._vault_path)
        bak_dir = os.path.join(vault_dir, "backups")
        os.makedirs(bak_dir, exist_ok=True)

        bak1 = os.path.join(bak_dir, "vault.bak.1")
        bak2 = os.path.join(bak_dir, "vault.bak.2")

        try:
            if os.path.exists(bak1):
                if os.path.exists(bak2):
                    os.remove(bak2)
                shutil.move(bak1, bak2)

            shutil.copy2(self._vault_path, bak1)
        except Exception:
            # Non-fatal if backup rotation fails (e.g. read-only fallback)
            pass

    @staticmethod
    def _atomic_write(target_path: str, data: bytes) -> None:
        """Writes data to a temporary file, fsyncs, and performs an atomic replace."""
        tmp_path = f"{target_path}.tmp.{os.getpid()}"
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename on Windows/Linux
        os.replace(tmp_path, target_path)

    def close(self) -> None:
        """Flushes state to disk and closes memory connection."""
        if self._is_open:
            try:
                self.flush()
            except Exception:
                pass
            self._conn.close()
            self._is_open = False

    # --------------------------------------------------------------------------
    # Scan Ingestion & Query Operations
    # --------------------------------------------------------------------------

    def ingest_scan(
        self,
        payload: NormalizedScanPayload,
        overall_health_score: int = 100,
        score_breakdown: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Ingests a normalized hardware scan, updates machine registry, and records components."""
        if not self._is_open:
            raise VaultCryptoError("Vault is closed")

        cursor = self._conn.cursor()
        now_utc = payload.timestamp_utc

        # 1. Update or Insert Machines table
        cursor.execute(
            """
            INSERT INTO machines (machine_fingerprint, first_seen_utc, last_seen_utc, created_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(machine_fingerprint) DO UPDATE SET
                last_seen_utc = excluded.last_seen_utc
            """,
            (payload.machine_fingerprint, now_utc, now_utc),
        )

        # 2. Record Hardware Anchors in machine_identifiers
        anchors = [
            ("motherboard_uuid", payload.hardware.motherboard.product),
            ("cpu_id", payload.hardware.cpu.model),
        ]
        if payload.hardware.storage:
            anchors.append(("primary_storage_serial", payload.hardware.storage[0].serial_hash))

        for anchor_type, anchor_val in anchors:
            cursor.execute(
                """
                INSERT INTO machine_identifiers (machine_fingerprint, anchor_type, anchor_value)
                VALUES (?, ?, ?)
                """,
                (payload.machine_fingerprint, anchor_type, str(anchor_val)),
            )

        # 3. Insert Scan Session
        cursor.execute(
            """
            INSERT INTO scan_sessions (
                scan_id, machine_fingerprint, platform, os_version,
                timestamp_utc, overall_health_score, raw_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.scan_id,
                payload.machine_fingerprint,
                payload.platform.value,
                payload.os_version,
                now_utc,
                overall_health_score,
                payload.model_dump_json(),
            ),
        )

        # 4. Insert Normalized Hardware Components
        hw = payload.hardware
        cursor.execute(
            "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
            (payload.scan_id, "cpu", 0, hw.cpu.model_dump_json()),
        )
        cursor.execute(
            "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
            (payload.scan_id, "memory", 0, hw.memory.model_dump_json()),
        )
        cursor.execute(
            "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
            (payload.scan_id, "motherboard", 0, hw.motherboard.model_dump_json()),
        )
        cursor.execute(
            "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
            (payload.scan_id, "battery", 0, hw.battery.model_dump_json()),
        )

        for idx, storage_dev in enumerate(hw.storage):
            cursor.execute(
                "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
                (payload.scan_id, "storage", idx, storage_dev.model_dump_json()),
            )

        for idx, gpu_dev in enumerate(hw.gpu):
            cursor.execute(
                "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
                (payload.scan_id, "gpu", idx, gpu_dev.model_dump_json()),
            )

        for idx, net_iface in enumerate(hw.network):
            cursor.execute(
                "INSERT INTO hardware_components (scan_id, category, component_index, details_json) VALUES (?, ?, ?, ?)",
                (payload.scan_id, "network", idx, net_iface.model_dump_json()),
            )

        # 5. Insert Diagnostic Results
        for diag in payload.diagnostics:
            cursor.execute(
                """
                INSERT INTO diagnostic_results (
                    scan_id, test_name, status, metric_value, threshold, evidence, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.scan_id,
                    diag.test_name,
                    diag.status.value,
                    diag.metric_value,
                    diag.threshold,
                    diag.evidence,
                    diag.recommendation,
                ),
            )

        # 6. Insert Health Scores
        scores = score_breakdown or {
            "overall": overall_health_score,
            "cpu": 100,
            "ram": 100,
            "storage": 100,
            "battery": 100,
            "thermal": 100,
            "summary": "Baseline hardware scan",
        }
        cursor.execute(
            """
            INSERT INTO health_scores (
                scan_id, overall_score, cpu_score, ram_score, storage_score,
                battery_score, thermal_score, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.scan_id,
                scores.get("overall", overall_health_score),
                scores.get("cpu", 100),
                scores.get("ram", 100),
                scores.get("storage", 100),
                scores.get("battery", 100),
                scores.get("thermal", 100),
                scores.get("summary", ""),
            ),
        )

        self._conn.commit()

        # Log audit event and flush atomically to disk
        self.log_audit_event("scan_ingested", f"Ingested scan {payload.scan_id} for {payload.machine_fingerprint}")
        self.flush()

        return payload.scan_id

    def get_machine(self, machine_fingerprint: str) -> Optional[Dict[str, Any]]:
        """Retrieves summary details for a machine by its fingerprint."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM machines WHERE machine_fingerprint = ?", (machine_fingerprint,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)

        cur.execute("SELECT count(*) as total_scans FROM scan_sessions WHERE machine_fingerprint = ?", (machine_fingerprint,))
        res["total_scans"] = cur.fetchone()["total_scans"]

        cur.execute(
            "SELECT overall_health_score, timestamp_utc FROM scan_sessions WHERE machine_fingerprint = ? ORDER BY timestamp_utc DESC LIMIT 1",
            (machine_fingerprint,),
        )
        latest = cur.fetchone()
        if latest:
            res["latest_health_score"] = latest["overall_health_score"]
            res["latest_scan_utc"] = latest["timestamp_utc"]

        return res

    def list_machines(self, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all registered machines, with optional filtering, including latest score and friendly name."""
        cur = self._conn.cursor()
        query = """
            SELECT 
                m.machine_fingerprint,
                m.first_seen_utc,
                m.last_seen_utc,
                m.asset_tag,
                m.notes,
                count(s.scan_id) as scan_count,
                max(s.timestamp_utc) as latest_scan_utc,
                (SELECT s2.overall_health_score FROM scan_sessions s2 WHERE s2.machine_fingerprint = m.machine_fingerprint ORDER BY s2.timestamp_utc DESC LIMIT 1) as latest_health_score,
                (SELECT s2.raw_payload_json FROM scan_sessions s2 WHERE s2.machine_fingerprint = m.machine_fingerprint ORDER BY s2.timestamp_utc DESC LIMIT 1) as latest_payload_json
            FROM machines m
            LEFT JOIN scan_sessions s ON m.machine_fingerprint = s.machine_fingerprint
        """
        params: List[Any] = []
        if search_query:
            q = f"%{search_query.strip()}%"
            query += " WHERE m.machine_fingerprint LIKE ? OR m.asset_tag LIKE ? OR m.notes LIKE ?"
            params.extend([q, q, q])
        query += " GROUP BY m.machine_fingerprint ORDER BY latest_scan_utc DESC"
        cur.execute(query, params)

        results = []
        for row in cur.fetchall():
            d = dict(row)
            if not d.get("asset_tag") and d.get("latest_payload_json"):
                try:
                    pj = json.loads(d["latest_payload_json"])
                    hw = pj.get("hardware", {})
                    mb = hw.get("motherboard", {})
                    prod = mb.get("product")
                    mfg = mb.get("manufacturer")
                    if prod:
                        d["asset_tag"] = f"{mfg} {prod}".strip() if mfg and mfg not in prod else prod.strip()
                except Exception:
                    pass
            d.pop("latest_payload_json", None)
            if d.get("latest_health_score") is None:
                d["latest_health_score"] = 100
            results.append(d)
        return results

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a scan session by scan_id including raw payload and diagnostics."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM scan_sessions WHERE scan_id = ?", (scan_id,))
        row = cur.fetchone()
        if not row:
            return None
        scan = dict(row)
        scan["raw_payload"] = json.loads(scan["raw_payload_json"])

        cur.execute("SELECT * FROM health_scores WHERE scan_id = ?", (scan_id,))
        hs = cur.fetchone()
        scan["health_scores"] = dict(hs) if hs else None

        cur.execute("SELECT * FROM diagnostic_results WHERE scan_id = ?", (scan_id,))
        scan["diagnostics"] = [dict(d) for d in cur.fetchall()]

        return scan

    def get_machine_scans(self, machine_fingerprint: str) -> List[Dict[str, Any]]:
        """Retrieves chronological scan history for a machine."""
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT s.scan_id, s.machine_fingerprint, s.platform, s.os_version,
                   s.timestamp_utc, s.overall_health_score, h.summary
            FROM scan_sessions s
            LEFT JOIN health_scores h ON s.scan_id = h.scan_id
            WHERE s.machine_fingerprint = ?
            ORDER BY s.timestamp_utc DESC
            """,
            (machine_fingerprint,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_latest_scan(self, machine_fingerprint: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest complete scan for a machine."""
        scans = self.get_machine_scans(machine_fingerprint)
        if not scans:
            return None
        return self.get_scan(scans[0]["scan_id"])

    def add_maintenance_record(
        self,
        machine_fingerprint: str,
        action_type: str,
        technician_name: str,
        notes: str,
    ) -> int:
        """Records a maintenance or service action for a machine."""
        now_utc = datetime.now(timezone.utc).isoformat()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO maintenance_records (machine_fingerprint, timestamp_utc, technician_name, action_type, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (machine_fingerprint, now_utc, technician_name, action_type, notes),
        )
        self._conn.commit()
        record_id = cur.lastrowid
        self.log_audit_event("maintenance_logged", f"Recorded {action_type} on machine {machine_fingerprint}")
        self.flush()
        return record_id

    def list_maintenance_records(self, machine_fingerprint: str) -> List[Dict[str, Any]]:
        """Lists maintenance history for a machine."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM maintenance_records WHERE machine_fingerprint = ? ORDER BY timestamp_utc DESC",
            (machine_fingerprint,),
        )
        return [dict(row) for row in cur.fetchall()]

    def update_machine_asset_tag(
        self,
        machine_fingerprint: str,
        asset_tag: str,
        notes: Optional[str] = None,
    ) -> None:
        """Updates asset tracking metadata for a machine."""
        cur = self._conn.cursor()
        if notes is not None:
            cur.execute(
                "UPDATE machines SET asset_tag = ?, notes = ? WHERE machine_fingerprint = ?",
                (asset_tag, notes, machine_fingerprint),
            )
        else:
            cur.execute(
                "UPDATE machines SET asset_tag = ? WHERE machine_fingerprint = ?",
                (asset_tag, machine_fingerprint),
            )
        self._conn.commit()
        self.log_audit_event("machine_updated", f"Updated asset tag for {machine_fingerprint} to {asset_tag}")
        self.flush()

    def log_audit_event(self, event_type: str, details: str) -> None:
        """Appends an immutable audit event."""
        now_utc = datetime.now(timezone.utc).isoformat()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO audit_events (event_type, timestamp_utc, details) VALUES (?, ?, ?)",
            (event_type, now_utc, details),
        )
        self._conn.commit()

    def list_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns recent audit logs."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]
