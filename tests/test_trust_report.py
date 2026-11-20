"""Tests for Ghost-OS Asymmetric Cryptographic Trust Report Subsystem."""

import base64
import json
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi.testclient import TestClient

from ghost_core.api.server import app, SESSION_TOKEN
from ghost_core.compatibility.matrix import CompatibilityEvaluator
from ghost_core.reporting.trust_report import GhostTrustReport
from ghost_core.schemas.scan import (
    BatterySpec,
    CpuSpec,
    DiagnosticResult,
    DiagnosticStatus,
    GpuSpec,
    HardwareSpec,
    MemoryModule,
    MemorySpec,
    MotherboardSpec,
    NetworkInterface,
    NormalizedScanPayload,
    PlatformEnum,
    StorageDevice,
)
from ghost_vault.db import GhostVaultDB


@pytest.fixture
def sample_normalized_scan() -> NormalizedScanPayload:
    fingerprint = NormalizedScanPayload.generate_fingerprint(
        salt="test_salt_12345",
        motherboard_uuid="ASUS-MB-VIVO-99112233",
        cpu_id="CPU-INTEL-13700H-BFEBFBFF",
        primary_storage_serial="SAMSUNG-MZVL21T0-S676NF0W",
    )
    return NormalizedScanPayload(
        schema_version="1.0.0",
        scan_id="w-scan-trust-test-001",
        machine_fingerprint=fingerprint,
        platform=PlatformEnum.WINDOWS,
        os_version="Microsoft Windows 11 Pro 10.0.22631",
        timestamp_utc="2026-11-15T00:00:00Z",
        compatibility_matrix=CompatibilityEvaluator.evaluate_capabilities(PlatformEnum.WINDOWS),
        hardware=HardwareSpec(
            cpu=CpuSpec(
                model="13th Gen Intel Core i7-13700H",
                architecture="x86_64",
                physical_cores=14,
                logical_threads=20,
                base_clock_mhz=2400.0,
                max_clock_mhz=5000.0,
                temp_c=45.0,
            ),
            memory=MemorySpec(
                total_bytes=34359738368,
                slots_used=2,
                slots_total=2,
                modules=[
                    MemoryModule(
                        slot="ChannelA-DIMM0",
                        capacity_bytes=17179869184,
                        speed_mhz=4800,
                        type="DDR5",
                        manufacturer="Samsung",
                        serial_number="SAM-88776655",
                    ),
                    MemoryModule(
                        slot="ChannelB-DIMM0",
                        capacity_bytes=17179869184,
                        speed_mhz=4800,
                        type="DDR5",
                        manufacturer="Samsung",
                        serial_number="SAM-88776656",
                    ),
                ],
            ),
            storage=[
                StorageDevice(
                    device_id="\\\\.\\PhysicalDrive0",
                    model="Samsung SSD 980 PRO 1TB",
                    serial_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
                    interface="NVMe",
                    capacity_bytes=1000204886016,
                    smart_status="PASSED",
                    temp_c=36.0,
                    wear_level_pct=2.0,
                    power_on_hours=500,
                )
            ],
            gpu=[
                GpuSpec(
                    name="NVIDIA GeForce RTX 4060 Laptop GPU",
                    vendor="NVIDIA",
                    vram_bytes=8589934592,
                    driver_version="551.23",
                    temp_c=40.0,
                )
            ],
            motherboard=MotherboardSpec(
                manufacturer="ASUSTeK COMPUTER INC.",
                product="Vivobook Pro 15",
                bios_version="K6502VU.301",
                bios_date="2024-04-10",
                secure_boot_enabled=True,
            ),
            battery=BatterySpec(
                present=True,
                design_capacity_mwh=70000.0,
                full_charge_capacity_mwh=68600.0,
                health_pct=98.0,
                cycle_count=42,
                status="Full",
            ),
            network=[
                NetworkInterface(
                    interface="Wi-Fi 6E",
                    mac_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                    type="Wireless",
                    link_speed_mbps=866,
                    status="Connected",
                )
            ],
        ),
        diagnostics=[
            DiagnosticResult(
                test_name="SMART_HEALTH",
                status=DiagnosticStatus.PASS,
                metric_value=0.0,
                threshold=1.0,
                evidence="All NVMe health indicators normal",
                recommendation="No action needed",
            ),
            DiagnosticResult(
                test_name="BATTERY_WEAR",
                status=DiagnosticStatus.PASS,
                metric_value=2.0,
                threshold=20.0,
                evidence="Battery degradation at 2%",
                recommendation="Battery in pristine health",
            ),
        ],
    )


def test_trust_report_asymmetric_ed25519_generation(sample_normalized_scan):
    """Verifies that trust report is generated with valid asymmetric Ed25519 digital signature."""
    payload_dict = sample_normalized_scan.model_dump()
    report = GhostTrustReport.generate(
        scan_payload=payload_dict,
        health_scores={"overall": 96, "summary": "Pristine enterprise grade"},
        inspector_name="Lead Hardware Auditor",
        algorithm="Ed25519",
    )

    assert "report_uuid" in report
    assert "created_at_utc" in report
    assert report["certification_evaluation"]["overall_health_score"] == 96
    assert "Grade A+" in report["certification_evaluation"]["asset_grade"]
    assert report["auditor_metadata"]["inspector"] == "Lead Hardware Auditor"

    sig = report["cryptographic_signature"]
    assert sig["algorithm"] == "Ed25519"
    assert sig["status"] == "CRYPTOGRAPHICALLY_VERIFIED"
    assert "public_key_b64" in sig
    assert "signature_b64" in sig
    assert len(sig["signature_b64"]) > 40

    # Verify signature passes
    assert GhostTrustReport.verify_signature(report) is True


def test_trust_report_ed25519_public_verification(sample_normalized_scan):
    """Verifies independent public verification using ONLY the embedded public key."""
    payload_dict = sample_normalized_scan.model_dump()
    key = ed25519.Ed25519PrivateKey.generate()
    report = GhostTrustReport.generate(
        scan_payload=payload_dict,
        health_scores={"overall": 92, "summary": "Grade A hardware"},
        private_key=key,
        algorithm="Ed25519",
    )

    # Verify using the report's embedded public key
    assert GhostTrustReport.verify_signature(report) is True

    # Also verify explicitly by instantiating Ed25519PublicKey independently
    pub_bytes = base64.b64decode(report["cryptographic_signature"]["public_key_b64"])
    independent_pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
    assert GhostTrustReport.verify_signature(report, public_key_override=independent_pub) is True


def test_trust_report_tamper_detection(sample_normalized_scan):
    """Verifies that altering any field in the trust report breaks Ed25519 signature verification."""
    payload_dict = sample_normalized_scan.model_dump()
    report = GhostTrustReport.generate(
        scan_payload=payload_dict,
        health_scores={"overall": 80, "summary": "Good condition"},
    )
    assert GhostTrustReport.verify_signature(report) is True

    # Tamper with overall health score
    tampered_report = json.loads(json.dumps(report))
    tampered_report["certification_evaluation"]["overall_health_score"] = 99
    assert GhostTrustReport.verify_signature(tampered_report) is False

    # Tamper with storage serial
    tampered_report2 = json.loads(json.dumps(report))
    tampered_report2["hardware_provenance"]["storage_units"][0]["serial_number"] = "COUNTERFEIT-SERIAL"
    assert GhostTrustReport.verify_signature(tampered_report2) is False


def test_trust_report_hmac_fallback(sample_normalized_scan):
    """Verifies that HMAC-SHA256 fallback algorithm remains operational when requested."""
    payload_dict = sample_normalized_scan.model_dump()
    report = GhostTrustReport.generate(
        scan_payload=payload_dict,
        health_scores={"overall": 88, "summary": "HMAC fallback test"},
        algorithm="HMAC-SHA256",
        signing_key="MyHMACSecret123",
    )
    assert report["cryptographic_signature"]["algorithm"] == "HMAC-SHA256"
    assert GhostTrustReport.verify_signature(report, signing_key="MyHMACSecret123") is True
    assert GhostTrustReport.verify_signature(report, signing_key="WrongKey") is False


def test_trust_report_grading():
    """Verifies letter grade computation across score boundaries."""
    assert "Grade A+" in GhostTrustReport.calculate_grade(97)
    assert "Grade A" in GhostTrustReport.calculate_grade(92)
    assert "Grade B" in GhostTrustReport.calculate_grade(85)
    assert "Grade C" in GhostTrustReport.calculate_grade(65)
    assert "Grade F" in GhostTrustReport.calculate_grade(35)


def test_trust_report_html_and_json_export(sample_normalized_scan, tmp_path):
    """Verifies standalone HTML and JSON export formats with asymmetric seal."""
    payload_dict = sample_normalized_scan.model_dump()
    report = GhostTrustReport.generate(
        scan_payload=payload_dict,
        health_scores={"overall": 95, "summary": "Verified Grade A+"},
    )

    json_path = str(tmp_path / "test_report.json")
    json_out = GhostTrustReport.export_json(report, output_path=json_path)
    parsed = json.loads(json_out)
    assert parsed["report_uuid"] == report["report_uuid"]

    html_path = str(tmp_path / "test_report.html")
    html_out = GhostTrustReport.export_html(report, output_path=html_path)
    assert "GHOST-OS TRUST CERTIFICATE" in html_out
    assert "Ed25519" in html_out
    assert report["machine_fingerprint"] in html_out
    assert "Samsung SSD 980 PRO" in html_out


def test_trust_report_api_endpoints(sample_normalized_scan, tmp_path):
    """Verifies API endpoints for trust report generation and export."""
    vault_file = str(tmp_path / "vault.enc")
    recovery_file = str(tmp_path / "rec.txt")
    v = GhostVaultDB.create_new(vault_file, "TestSecret123", recovery_file_path=recovery_file)

    scan_id = v.ingest_scan(
        payload=sample_normalized_scan,
        overall_health_score=95,
        score_breakdown={"overall": 95, "cpu": 100, "storage": 90, "summary": "Clean"},
    )

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {SESSION_TOKEN}"}

    # Unlock vault in server state
    client.post("/api/v1/vault/unlock", json={"secret": "TestSecret123", "vault_path": vault_file}, headers=headers)

    # Test GET trust report
    resp = client.get(f"/api/v1/scans/{scan_id}/trust-report", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["certification_evaluation"]["overall_health_score"] == 95
    assert "cryptographic_signature" in data
    assert data["cryptographic_signature"]["algorithm"] == "Ed25519"
    assert GhostTrustReport.verify_signature(data) is True

    # Test GET trust report export HTML
    resp_html = client.get(f"/api/v1/scans/{scan_id}/trust-report/export?format=html", headers=headers)
    assert resp_html.status_code == 200
    assert "text/html" in resp_html.headers["content-type"]
    assert "GHOST-OS TRUST CERTIFICATE" in resp_html.text
    assert "Ed25519" in resp_html.text

    # Test GET trust report export JSON
    resp_json = client.get(f"/api/v1/scans/{scan_id}/trust-report/export?format=json", headers=headers)
    assert resp_json.status_code == 200
    assert resp_json.json()["report_uuid"] == data["report_uuid"]
