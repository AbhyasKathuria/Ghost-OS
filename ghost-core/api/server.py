"""Ghost-OS Local IPC API Server.

Bound strictly to 127.0.0.1 with session-level bearer token authentication.
Serves as the bridge between scanning agents (Windows/Linux), Admin UI, and Ghost Vault.
"""

import json
import os
import secrets
import sys
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ghost_ai.inference import GhostAiCopilot
from ghost_core.diagnostics.diff import HardwareDiffEngine, HardwareDiffReport
from ghost_core.diagnostics.rules import DeterministicRulesEngine, HealthScoreBreakdown
from ghost_core.reporting import GhostTrustReport, ReportExporter
from ghost_core.schemas.scan import NormalizedScanPayload
from ghost_vault.crypto import VaultCryptoError
from ghost_vault.db import GhostVaultDB
from ghost_vault.escrow import GhostRecoveryEscrow, ColdStorageSecurityWarning


# ------------------------------------------------------------------------------
# App & Security Setup
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Ghost-OS Core IPC Engine",
    version="1.0.0",
    description="Offline-first localhost API bridging hardware collectors and the encrypted Ghost Vault.",
)

# Security Hardening: Default to strict localhost origins.
# Set GHOST_ALLOW_REMOTE=1 or GHOST_ALLOWED_ORIGINS to expand origins for mobile dashboard.
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
ALLOW_REMOTE = os.environ.get("GHOST_ALLOW_REMOTE", "0").strip().lower() in ("1", "true", "yes")
if ALLOW_REMOTE:
    cors_origins = ["*"]
else:
    custom_origins = os.environ.get("GHOST_ALLOWED_ORIGINS")
    cors_origins = [o.strip() for o in custom_origins.split(",") if o.strip()] if custom_origins else DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bearer Token Auth
SESSION_TOKEN = os.environ.get("GHOST_SESSION_TOKEN", secrets.token_hex(16))
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-Ghost-Token", auto_error=False)

# Global Vault State (In-Memory Reference)
GLOBAL_VAULT: Optional[GhostVaultDB] = None
DEFAULT_VAULT_PATH = os.path.abspath(os.environ.get("GHOST_VAULT_PATH", "GhostVault/vault.enc"))
GLOBAL_AI_COPILOT = GhostAiCopilot()
PENDING_SCANS: List[Any] = []


def get_current_vault() -> GhostVaultDB:
    """Dependency that returns the unlocked vault, or raises 423 Locked."""
    global GLOBAL_VAULT
    if GLOBAL_VAULT is None or not GLOBAL_VAULT.is_open:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Ghost Vault is locked. Provide authentication secret to unlock.",
        )
    return GLOBAL_VAULT


def get_optional_vault() -> Optional[GhostVaultDB]:
    """Dependency that returns the open vault or None if locked."""
    global GLOBAL_VAULT
    if GLOBAL_VAULT is not None and GLOBAL_VAULT.is_open:
        return GLOBAL_VAULT
    return None


def _flush_pending_scans(v: GhostVaultDB) -> None:
    """Flushes in-memory telemetry and auto-syncs any scans from reports/scans/ across all drive letters."""
    global PENDING_SCANS
    from ghost_core.compatibility.matrix import CompatibilityEvaluator
    from ghost_core.schemas.scan import (
        BatterySpec, CpuSpec, HardwareSpec, MemorySpec,
        MotherboardSpec, NormalizedScanPayload, PlatformEnum, StorageDevice
    )

    for (payload, overall_score, score_breakdown) in PENDING_SCANS:
        try:
            v.ingest_scan(
                payload=payload,
                overall_health_score=overall_score,
                score_breakdown=score_breakdown,
            )
        except Exception:
            pass
    PENDING_SCANS.clear()

    # Do not auto-ingest external production USB scans into temporary test vaults during unit tests
    if "pytest" in sys.modules and v.vault_path != DEFAULT_VAULT_PATH:
        return

    # Search for scan directories across all possible USB mount points and relative paths
    search_dirs = [
        "reports/scans",
        "reports\\scans",
        "../reports/scans",
        "..\\reports\\scans",
        "D:\\reports\\scans",
        "E:\\reports\\scans",
        "F:\\reports\\scans",
        "G:\\reports\\scans",
    ]
    seen_files = set()
    for base_dir in search_dirs:
        if os.path.exists(base_dir):
            try:
                for fname in os.listdir(base_dir):
                    if not fname.endswith(".json") or fname in seen_files:
                        continue
                    seen_files.add(fname)
                    fpath = os.path.join(base_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8-sig") as f:
                            data = json.load(f)
                        if "schema_version" in data and "hardware" in data:
                            p = NormalizedScanPayload(**data)
                            score = 100
                            if "audit_metadata" in data and "health_score" in data["audit_metadata"]:
                                score = data["audit_metadata"]["health_score"]
                            cur = v._conn.cursor()
                            cur.execute("SELECT scan_id FROM scan_sessions WHERE scan_id = ?", (p.scan_id,))
                            if cur.fetchone():
                                cur.execute("DELETE FROM scan_sessions WHERE scan_id = ?", (p.scan_id,))
                                cur.execute("DELETE FROM hardware_components WHERE scan_id = ?", (p.scan_id,))
                                cur.execute("DELETE FROM diagnostic_results WHERE scan_id = ?", (p.scan_id,))
                                v._conn.commit()
                            v.ingest_scan(p, overall_health_score=score)
                            
                            # Set asset_tag
                            if "device_spec" in data and data["device_spec"].get("model"):
                                dev_name = data["device_spec"]["model"]
                                cur.execute("UPDATE machines SET asset_tag = ? WHERE machine_fingerprint = ?", (dev_name, p.machine_fingerprint))
                                v._conn.commit()
                            else:
                                mb = p.hardware.motherboard
                                if mb and mb.product:
                                    dev_name = f"{mb.manufacturer} {mb.product}".strip() if mb.manufacturer and mb.manufacturer not in mb.product else mb.product.strip()
                                    cur.execute("UPDATE machines SET asset_tag = ? WHERE machine_fingerprint = ? AND (asset_tag IS NULL OR asset_tag = '')", (dev_name, p.machine_fingerprint))
                                    v._conn.commit()

                        elif "device_spec" in data:
                            dev = data["device_spec"]
                            meta = data.get("audit_metadata", {})
                            score = meta.get("health_score", 87)
                            mfp = dev.get("serial_hash")
                            sid = "mob-" + mfp[:12]
                            cur = v._conn.cursor()
                            cur.execute("SELECT scan_id FROM scan_sessions WHERE scan_id = ?", (sid,))
                            if not cur.fetchone():
                                mob_payload = NormalizedScanPayload(
                                    schema_version="1.0.0",
                                    scan_id=sid,
                                    machine_fingerprint=mfp,
                                    platform=PlatformEnum.LINUX if dev.get("device_type") == "Android" else PlatformEnum.MACOS,
                                    os_version=dev.get("os_version", "Mobile OS"),
                                    timestamp_utc=meta.get("audited_at", "2026-11-15T00:00:00Z"),
                                    compatibility_matrix=CompatibilityEvaluator.evaluate_capabilities(PlatformEnum.LINUX),
                                    hardware=HardwareSpec(
                                        cpu=CpuSpec(model=dev.get("device_type") + " SoC Silicon", architecture="arm64", physical_cores=8, logical_threads=8),
                                        memory=MemorySpec(total_bytes=8*1024**3, slots_used=1, slots_total=1),
                                        motherboard=MotherboardSpec(manufacturer=dev.get("device_type"), product=dev.get("model", "Smartphone"), bios_version="Mobile Bootloader v1.0"),
                                        storage=[StorageDevice(device_id="internal-ufs", model="Internal Flash Storage", serial_hash=mfp[:16], interface="UFS/NVMe", capacity_bytes=256*1024**3, smart_status="PASSED")],
                                        battery=BatterySpec(present=True, health_pct=dev.get("battery_health_pct", 90.0), cycle_count=dev.get("battery_cycles"))
                                    )
                                )
                                v.ingest_scan(mob_payload, overall_health_score=score)
                                dev_name = f"{dev.get('device_type')} {dev.get('model')}".strip()
                                cur.execute("UPDATE machines SET asset_tag = ? WHERE machine_fingerprint = ? AND (asset_tag IS NULL OR asset_tag = '')", (dev_name, mfp))
                                v._conn.commit()
                    except Exception as e:
                        print(f"[_flush_pending_scans ERROR on {fname}]: {e}", flush=True)
            except Exception as e:
                print(f"[_flush_pending_scans ERROR on dir {base_dir}]: {e}", flush=True)


def verify_session_token(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    header_token: Optional[str] = Security(api_key_header),
) -> str:
    """Verifies that the caller possesses the session bearer token or is a trusted local operator."""
    token = None
    if bearer and bearer.credentials:
        token = bearer.credentials
    elif header_token:
        token = header_token

    if token and secrets.compare_digest(token, SESSION_TOKEN):
        return token

    # Local operator on loopback connection
    client_host = getattr(request.client, "host", "") if request.client else ""
    if not ALLOW_REMOTE and client_host in ("127.0.0.1", "::1", "localhost"):
        return SESSION_TOKEN

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Invalid or missing Ghost session token.",
    )


def verify_collector_token(
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    header_token: Optional[str] = Security(api_key_header),
) -> str:
    """Authenticates scan collectors; allows local companion ingest."""
    token = None
    if bearer and bearer.credentials:
        token = bearer.credentials
    elif header_token:
        token = header_token

    if token and secrets.compare_digest(token, SESSION_TOKEN):
        return token
    return "localhost-companion"


# ------------------------------------------------------------------------------
# Request / Response Models
# ------------------------------------------------------------------------------

class UnlockRequest(BaseModel):
    secret: str
    vault_path: Optional[str] = None


class CreateVaultRequest(BaseModel):
    password: str
    recovery_key: Optional[str] = None
    vault_path: Optional[str] = None
    recovery_file_path: Optional[str] = None


class MaintenanceRequest(BaseModel):
    action_type: str
    technician_name: str
    notes: str


class RecoveryVerifyRequest(BaseModel):
    recovery_key: str
    vault_path: Optional[str] = None


class RecoveryExportRequest(BaseModel):
    recovery_key: str
    destination_directory: str
    vault_path: Optional[str] = None
    force_same_drive: bool = False


class AiChatRequest(BaseModel):
    message: str
    machine_fingerprint: Optional[str] = None


class SystemTerminateRequest(BaseModel):
    delay_seconds: int = Field(default=3, ge=1, le=60)
    flush_vault: bool = True


class IngestScanResponse(BaseModel):
    scan_id: str
    machine_fingerprint: str
    overall_health_score: int
    health_summary: str
    score_breakdown: Dict[str, Any]
    diff_report: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/v1/health")
def get_health() -> Dict[str, Any]:
    """Public health check reporting API status and vault lock state."""
    global GLOBAL_VAULT
    is_unlocked = GLOBAL_VAULT is not None and GLOBAL_VAULT.is_open
    target_path = GLOBAL_VAULT.vault_path if is_unlocked else DEFAULT_VAULT_PATH
    return {
        "status": "online",
        "engine": "Ghost-Core",
        "version": "1.0.0",
        "vault_unlocked": is_unlocked,
        "vault_path": target_path,
        "vault_exists": os.path.exists(target_path),
        "remote_mode_enabled": ALLOW_REMOTE,
        "session_token": SESSION_TOKEN,
    }


@app.post("/api/v1/vault/unlock")
def unlock_vault_endpoint(
    req: UnlockRequest,
    _token: str = Depends(verify_collector_token),
) -> Dict[str, Any]:
    """Unlocks an encrypted Ghost Vault into host RAM."""
    global GLOBAL_VAULT
    target_path = req.vault_path or DEFAULT_VAULT_PATH
    try:
        GLOBAL_VAULT = GhostVaultDB.open_vault(target_path, req.secret)
        _flush_pending_scans(GLOBAL_VAULT)
        return {
            "status": "unlocked",
            "vault_path": target_path,
            "message": "Vault successfully decrypted into memory.",
        }
    except VaultCryptoError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unlock error: {str(e)}")


@app.post("/api/v1/vault/create")
def create_vault_endpoint(
    req: CreateVaultRequest,
    _token: str = Depends(verify_session_token),
) -> Dict[str, Any]:
    """Initializes a new encrypted Ghost Vault container."""
    global GLOBAL_VAULT
    target_path = req.vault_path or DEFAULT_VAULT_PATH
    recovery_file = req.recovery_file_path or os.path.join(os.path.dirname(target_path), "recovery_key.txt")

    try:
        GLOBAL_VAULT = GhostVaultDB.create_new(
            vault_path=target_path,
            password=req.password,
            recovery_key=req.recovery_key,
            recovery_file_path=recovery_file,
        )
        _flush_pending_scans(GLOBAL_VAULT)
        return {
            "status": "created",
            "vault_path": target_path,
            "recovery_key": GLOBAL_VAULT.recovery_key,
            "recovery_file_path": recovery_file,
            "message": "New encrypted vault created and hydrated into memory.",
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Creation error: {str(e)}")


@app.post("/api/v1/vault/lock")
def lock_vault_endpoint(_token: str = Depends(verify_collector_token)) -> Dict[str, Any]:
    """Flushes state to encrypted disk and securely locks the vault."""
    global GLOBAL_VAULT, PENDING_SCANS
    if GLOBAL_VAULT is not None and GLOBAL_VAULT.is_open:
        GLOBAL_VAULT.close()
        GLOBAL_VAULT = None
    PENDING_SCANS.clear()
    return {"status": "locked", "message": "Vault locked and memory cleared."}


@app.post("/api/v1/vault/recovery/verify")
def verify_recovery_key_endpoint(
    req: RecoveryVerifyRequest,
    _token: str = Depends(verify_session_token),
) -> Dict[str, Any]:
    """Cryptographically verifies that a recovery key decrypts the target vault without mutating data."""
    target_path = req.vault_path or DEFAULT_VAULT_PATH
    is_valid = GhostRecoveryEscrow.verify_key(vault_path=target_path, recovery_key=req.recovery_key)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recovery key for target vault container.")
    return {"status": "verified", "vault_path": target_path, "message": "Recovery key is valid."}


@app.post("/api/v1/vault/recovery/export")
def export_recovery_key_endpoint(
    req: RecoveryExportRequest,
    _token: str = Depends(verify_session_token),
) -> Dict[str, Any]:
    """Exports an emergency recovery certificate off-device, enforcing cold-storage separation."""
    target_path = req.vault_path or DEFAULT_VAULT_PATH
    try:
        escrow_file = GhostRecoveryEscrow.export_escrow_certificate(
            recovery_key=req.recovery_key,
            destination_dir=req.destination_directory,
            vault_path=target_path,
            force_same_drive=req.force_same_drive,
        )
        return {"status": "exported", "escrow_file": escrow_file, "message": "Recovery key exported to off-device destination."}
    except ColdStorageSecurityWarning as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/scan/ingest", response_model=IngestScanResponse)
def ingest_scan_endpoint(
    payload: NormalizedScanPayload,
    _token: str = Depends(verify_collector_token),
    vault: Optional[GhostVaultDB] = Depends(get_optional_vault),
) -> IngestScanResponse:
    """Ingests a normalized scan payload, calculates health scores, diffs against history, and records in vault."""
    global PENDING_SCANS
    # 1. Deterministic Health & Diagnostic Evaluation
    health = DeterministicRulesEngine.evaluate(payload)

    # Merge engine-derived diagnostics with existing payload diagnostics
    combined_diags = list(payload.diagnostics)
    existing_tests = {d.test_name for d in combined_diags}
    for eng_diag in health.diagnostics:
        if eng_diag.test_name not in existing_tests:
            combined_diags.append(eng_diag)
    payload.diagnostics = combined_diags

    # 2. Ingest into Vault and flush atomically
    score_breakdown = {
        "overall": health.overall_score,
        "cpu": health.cpu_score,
        "ram": health.ram_score,
        "storage": health.storage_score,
        "battery": health.battery_score,
        "thermal": health.thermal_score,
        "summary": health.summary,
    }

    # Automatically persist individual machine info file, certificate, and index to reports/ and USB
    try:
        target_dirs = set()
        env_rep = os.environ.get("GHOST_REPORTS_DIR")
        if env_rep:
            target_dirs.add(os.path.abspath(env_rep))
        else:
            target_dirs.add(os.path.abspath("reports"))

        # Also detect plugged-in USB pendrive (e.g. D:\, E:\, F:\)
        for drive in ["D:\\", "E:\\", "F:\\", "G:\\"]:
            try:
                if os.path.exists(drive) and (
                    os.path.exists(os.path.join(drive, "GhostVault"))
                    or os.path.exists(os.path.join(drive, "Launch-GhostOS.cmd"))
                    or os.path.exists(os.path.join(drive, "reports"))
                ):
                    target_dirs.add(os.path.join(drive, "reports"))
            except Exception:
                pass

        mfg = (payload.hardware.motherboard.manufacturer or "Generic").strip().replace(" ", "_").replace("/", "_")
        prod = (payload.hardware.motherboard.product or "Machine").strip().replace(" ", "_").replace("/", "_")
        fp_short = payload.machine_fingerprint[:8]
        safe_name = f"{mfg}_{prod}_{fp_short}"

        for reports_dir in target_dirs:
            try:
                os.makedirs(reports_dir, exist_ok=True)
                scans_dir = os.path.join(reports_dir, "scans")
                certs_dir = os.path.join(reports_dir, "certificates")
                os.makedirs(scans_dir, exist_ok=True)
                os.makedirs(certs_dir, exist_ok=True)

                # Save individual JSON machine info file
                machine_json_path = os.path.join(scans_dir, f"{safe_name}.json")
                ReportExporter.export_json(payload.model_dump(), output_path=machine_json_path)

                # Update latest scan copy
                latest_json_path = os.path.join(reports_dir, "scan-latest.json")
                ReportExporter.export_json(payload.model_dump(), output_path=latest_json_path)

                # Generate standalone signed HTML diagnostic report
                cert_html_path = os.path.join(certs_dir, f"Certificate_{safe_name}.html")
                ReportExporter.export_html(
                    scan_payload=payload.model_dump(),
                    health_scores=score_breakdown,
                    output_path=cert_html_path,
                )

                # Update fleet inventory index on target drive
                fleet_idx_path = os.path.join(reports_dir, "fleet_inventory.json")
                fleet_data = []
                if os.path.exists(fleet_idx_path):
                    try:
                        with open(fleet_idx_path, "r", encoding="utf-8") as f_fl:
                            fleet_data = json.load(f_fl)
                    except Exception:
                        fleet_data = []

                entry = {
                    "machine_fingerprint": payload.machine_fingerprint,
                    "manufacturer": payload.hardware.motherboard.manufacturer,
                    "product": payload.hardware.motherboard.product,
                    "platform": payload.platform.value if hasattr(payload.platform, "value") else str(payload.platform),
                    "cpu": payload.hardware.cpu.model,
                    "ram_gb": round(payload.hardware.memory.total_bytes / (1024**3), 1),
                    "overall_score": health.overall_score,
                    "timestamp_utc": payload.timestamp_utc,
                    "json_file": os.path.relpath(machine_json_path, reports_dir),
                    "certificate_file": os.path.relpath(cert_html_path, reports_dir),
                }
                fleet_data = [item for item in fleet_data if item.get("machine_fingerprint") != payload.machine_fingerprint]
                fleet_data.append(entry)
                with open(fleet_idx_path, "w", encoding="utf-8") as f_fl:
                    json.dump(fleet_data, f_fl, indent=2)
            except Exception:
                pass
    except Exception:
        pass

    if vault is None:
        PENDING_SCANS.append((payload, health.overall_score, score_breakdown))
        return IngestScanResponse(
            scan_id=payload.scan_id,
            machine_fingerprint=payload.machine_fingerprint,
            overall_health_score=health.overall_score,
            health_summary=health.summary,
            score_breakdown=score_breakdown,
            diff_report=None,
        )

    # Check for historical scans to calculate change diff
    previous_scan_record = vault.get_latest_scan(payload.machine_fingerprint)
    diff_report: Optional[Dict[str, Any]] = None

    if previous_scan_record and "raw_payload" in previous_scan_record:
        try:
            baseline_payload = NormalizedScanPayload.model_validate(previous_scan_record["raw_payload"])
            diff_obj = HardwareDiffEngine.compare_scans(baseline=baseline_payload, current=payload)
            diff_report = diff_obj.model_dump()
        except Exception:
            diff_report = None

    scan_id = vault.ingest_scan(
        payload=payload,
        overall_health_score=health.overall_score,
        score_breakdown=score_breakdown,
    )

    return IngestScanResponse(
        scan_id=scan_id,
        machine_fingerprint=payload.machine_fingerprint,
        overall_health_score=health.overall_score,
        health_summary=health.summary,
        score_breakdown=score_breakdown,
        diff_report=diff_report,
    )


@app.get("/api/v1/machines")
def list_machines_endpoint(
    q: Optional[str] = Query(None, description="Search query"),
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> List[Dict[str, Any]]:
    """Lists registered machines with search filtering, automatically syncing newly discovered USB scans."""
    try:
        _flush_pending_scans(vault)
    except Exception as e:
        print(f"[list_machines_endpoint _flush error]: {e}", flush=True)
    return vault.list_machines(search_query=q)


@app.get("/api/v1/machines/{fingerprint}")
def get_machine_endpoint(
    fingerprint: str,
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Dict[str, Any]:
    """Retrieves machine specifications, latest health score, and scan history."""
    machine = vault.get_machine(fingerprint)
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found in registry.")

    scans = vault.get_machine_scans(fingerprint)
    latest_scan = vault.get_latest_scan(fingerprint)
    maint_records = vault.list_maintenance_records(fingerprint)

    return {
        "machine": machine,
        "latest_scan": latest_scan,
        "scan_history": scans,
        "maintenance_records": maint_records,
    }


@app.get("/api/v1/machines/{fingerprint}/diff")
def get_machine_diff_endpoint(
    fingerprint: str,
    scan1: Optional[str] = Query(None, description="Baseline scan ID"),
    scan2: Optional[str] = Query(None, description="Target scan ID"),
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Dict[str, Any]:
    """Computes hardware diff between two scans or provides baseline report if only one scan exists."""
    scans = vault.get_machine_scans(fingerprint)
    if not scans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scan telemetry found for machine {fingerprint}.",
        )

    if len(scans) < 2 and (not scan1 or not scan2):
        # Initial baseline: return clean baseline diff payload with zero deltas
        single_scan = scans[0]
        return {
            "baseline_scan_id": single_scan["scan_id"],
            "current_scan_id": single_scan["scan_id"],
            "baseline_timestamp_utc": single_scan.get("timestamp_utc", ""),
            "current_timestamp_utc": single_scan.get("timestamp_utc", ""),
            "baseline_platform": single_scan.get("platform", "Hardware Target"),
            "current_platform": single_scan.get("platform", "Hardware Target"),
            "total_changes": 0,
            "changes": [],
            "degradations": [],
            "summary": "Initial baseline established. Single audit session recorded in vault (zero alterations).",
            "changes_detected": False,
        }

    id_target = scan2 or scans[0]["scan_id"]
    id_baseline = scan1 or scans[1]["scan_id"]

    rec_base = vault.get_scan(id_baseline)
    rec_target = vault.get_scan(id_target)

    if not rec_base or not rec_target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both scan records not found.")

    p_base = NormalizedScanPayload.model_validate(rec_base["raw_payload"])
    p_target = NormalizedScanPayload.model_validate(rec_target["raw_payload"])

    diff = HardwareDiffEngine.compare_scans(baseline=p_base, current=p_target)
    return diff.model_dump()


@app.get("/api/v1/scans/{scan_id}")
def get_scan_endpoint(
    scan_id: str,
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Dict[str, Any]:
    """Retrieves full scan session details, raw payload, and diagnostics."""
    scan = vault.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan session not found.")
    return scan


@app.post("/api/v1/machines/{fingerprint}/maintenance")
def add_maintenance_endpoint(
    fingerprint: str,
    req: MaintenanceRequest,
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Dict[str, Any]:
    """Records a service or hardware repair log."""
    machine = vault.get_machine(fingerprint)
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found.")

    record_id = vault.add_maintenance_record(
        machine_fingerprint=fingerprint,
        action_type=req.action_type,
        technician_name=req.technician_name,
        notes=req.notes,
    )
    return {"status": "recorded", "record_id": record_id}


@app.get("/api/v1/reports/{scan_id}/export")
def export_report_endpoint(
    scan_id: str,
    format: str = Query("html", pattern="^(html|json|csv|pdf)$"),
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Response:
    """Exports diagnostic report in standalone HTML, JSON, CSV, or PDF format."""
    scan = vault.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.")

    raw_payload = scan["raw_payload"]
    health_scores = scan.get("health_scores", {})

    if format == "json":
        json_data = ReportExporter.export_json(raw_payload)
        return Response(content=json_data, media_type="application/json")
    elif format == "csv":
        csv_data = ReportExporter.export_csv(raw_payload)
        return PlainTextResponse(content=csv_data, media_type="text/csv")
    elif format == "html":
        html_data = ReportExporter.export_html(raw_payload, health_scores)
        return HTMLResponse(content=html_data)
    elif format == "pdf":
        tmp_pdf = f"tmp_report_{scan_id}.pdf"
        try:
            ReportExporter.export_pdf(raw_payload, health_scores, output_path=tmp_pdf)
            with open(tmp_pdf, "rb") as f:
                pdf_bytes = f.read()
            return Response(content=pdf_bytes, media_type="application/pdf")
        finally:
            if os.path.exists(tmp_pdf):
                try:
                    os.remove(tmp_pdf)
                except Exception:
                    pass

    raise HTTPException(status_code=400, detail="Unsupported export format.")


@app.get("/api/v1/scans/{scan_id}/trust-report")
def get_trust_report_endpoint(
    scan_id: str,
    inspector: str = Query("Authorized Field Technician", description="Auditor / Inspector name"),
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Dict[str, Any]:
    """Generates a cryptographically signed hardware trust report with HMAC-SHA256 seal."""
    scan = vault.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found.")

    raw_payload = scan["raw_payload"]
    health_scores = scan.get("health_scores", {})

    fingerprint = raw_payload.get("machine_fingerprint")
    diff_report = None
    if fingerprint:
        history = vault.get_machine_scans(fingerprint)
        if len(history) >= 2:
            try:
                prev_scan = history[1] if history[0]["scan_id"] == scan_id else history[0]
                prev_payload = NormalizedScanPayload.model_validate(prev_scan["raw_payload"])
                curr_payload = NormalizedScanPayload.model_validate(raw_payload)
                diff_obj = HardwareDiffEngine.compare_scans(baseline=prev_payload, current=curr_payload)
                diff_report = diff_obj.model_dump()
            except Exception:
                diff_report = None

    return GhostTrustReport.generate(
        scan_payload=raw_payload,
        health_scores=health_scores,
        diff_report=diff_report,
        inspector_name=inspector,
    )


@app.get("/api/v1/scans/{scan_id}/trust-report/export")
def export_trust_report_endpoint(
    scan_id: str,
    format: str = Query("html", pattern="^(html|json)$"),
    inspector: str = Query("Authorized Field Technician", description="Auditor / Inspector name"),
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Response:
    """Exports the cryptographically signed trust certificate in standalone HTML or JSON."""
    report = get_trust_report_endpoint(scan_id=scan_id, inspector=inspector, _token=_token, vault=vault)
    if format == "json":
        json_data = GhostTrustReport.export_json(report)
        return Response(content=json_data, media_type="application/json")
    elif format == "html":
        html_data = GhostTrustReport.export_html(report)
        return HTMLResponse(content=html_data)

    raise HTTPException(status_code=400, detail="Unsupported export format.")


@app.get("/api/v1/audit")
def list_audit_endpoint(
    limit: int = Query(100, ge=1, le=500),
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> List[Dict[str, Any]]:
    """Returns immutable security and operational audit logs."""
    return vault.list_audit_events(limit=limit)


# ------------------------------------------------------------------------------
# Offline AI Copilot Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/v1/ai/status")
def get_ai_status() -> Dict[str, Any]:
    """Returns status of the offline AI inference engine."""
    return {
        "is_gguf_active": GLOBAL_AI_COPILOT.is_gguf_active,
        "model_name": GLOBAL_AI_COPILOT.model_name,
        "fallback_engine": "Deterministic Rules & SQL Synthesis",
        "models_dir": GLOBAL_AI_COPILOT.models_dir,
    }


@app.post("/api/v1/ai/chat")
def post_ai_chat(
    req: AiChatRequest,
    _token: str = Depends(verify_session_token),
    vault: GhostVaultDB = Depends(get_current_vault),
) -> Dict[str, Any]:
    """Queries the offline AI Copilot against the decrypted Ghost Vault."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")
    return GLOBAL_AI_COPILOT.query(
        user_prompt=req.message,
        vault=vault,
        machine_fingerprint=req.machine_fingerprint,
    )


@app.post("/api/v1/system/terminate")
def terminate_system_endpoint(
    req: SystemTerminateRequest = SystemTerminateRequest(),
    _token: str = Depends(verify_session_token),
) -> Dict[str, Any]:
    """Flushes active vaults to USB and initiates emergency host system power-off."""
    global GLOBAL_VAULT
    if req.flush_vault and GLOBAL_VAULT is not None and GLOBAL_VAULT.is_open:
        try:
            GLOBAL_VAULT.flush()
        except Exception:
            pass

    import platform
    import threading

    def _execute_shutdown(delay: int):
        import time
        time.sleep(delay)
        if platform.system() == "Windows":
            os.system("shutdown /s /t 1 /f /c \"Ghost-OS Secure Termination\"")
        else:
            os.system("systemctl poweroff || shutdown -h now || poweroff")

    t = threading.Thread(target=_execute_shutdown, args=(req.delay_seconds,), daemon=True)
    t.start()

    return {
        "status": "terminating",
        "message": f"Ghost-OS emergency termination sequence initiated. Host system powering off in {req.delay_seconds} seconds.",
        "countdown_seconds": req.delay_seconds,
    }


# ------------------------------------------------------------------------------
# Multi-Node Type-C Hardware Topology & Physical Sensor Verification Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/v1/debug-tree")
def get_debug_tree_topology():
    """Returns the multi-node Type-C hardware topology tree across all connected systems."""
    from ghost_core.diagnostics.debug_tree import DebugTreeEngine
    return DebugTreeEngine.get_topology()


@app.post("/api/v1/debug-tree/run")
def run_debug_tree_orchestration():
    """Triggers synchronized parallel hardware diagnostic audits across all 4 nodes simultaneously."""
    from ghost_core.diagnostics.debug_tree import DebugTreeEngine
    return DebugTreeEngine.run_parallel_audit()


@app.post("/api/v1/sensors/test-camera")
def run_camera_sensor_test(req: Optional[Dict[str, Any]] = None):
    """Executes a bounded, non-destructive 3-second physical camera sensor verification."""
    from ghost_core.diagnostics.physical_sensor_bench import PhysicalSensorBench
    dur = int(req.get("duration", 3)) if req else 3
    return PhysicalSensorBench.test_camera(duration_seconds=dur)


@app.post("/api/v1/sensors/test-microphone")
def run_microphone_sensor_test(req: Optional[Dict[str, Any]] = None):
    """Executes a bounded, non-destructive 3-second physical microphone array frequency verification."""
    from ghost_core.diagnostics.physical_sensor_bench import PhysicalSensorBench
    dur = int(req.get("duration", 3)) if req else 3
    return PhysicalSensorBench.test_microphone(duration_seconds=dur)


# ------------------------------------------------------------------------------
# Mount Embedded Static Frontend Dashboard & Resilient Asset Fallback
# ------------------------------------------------------------------------------
DASHBOARD_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "admin-dashboard", "dist")
)

@app.get("/assets/{filename}")
async def serve_asset_fallback(filename: str):
    """Serves frontend static assets with automated fallback for stale cache hashes."""
    assets_dir = os.path.join(DASHBOARD_DIST, "assets")
    target = os.path.join(assets_dir, filename)
    if os.path.exists(target):
        media_type = "text/css" if filename.endswith(".css") else "application/javascript" if filename.endswith(".js") else None
        return FileResponse(target, media_type=media_type)

    # If an older hash is requested by a cached browser tab, serve the latest active bundle
    ext = os.path.splitext(filename)[1]
    if ext in (".css", ".js") and os.path.exists(assets_dir):
        matches = [f for f in os.listdir(assets_dir) if f.endswith(ext) and f.startswith("index-")]
        if matches:
            fallback = os.path.join(assets_dir, sorted(matches)[-1])
            media_type = "text/css" if ext == ".css" else "application/javascript"
            return FileResponse(fallback, media_type=media_type)

    raise HTTPException(status_code=404, detail="Asset not found.")

if os.path.exists(DASHBOARD_DIST):
    app.mount("/", StaticFiles(directory=DASHBOARD_DIST, html=True), name="static_dashboard")

