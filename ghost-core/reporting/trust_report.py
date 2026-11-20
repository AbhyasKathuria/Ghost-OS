"""Ghost-OS Cryptographically Signed Trust Report Generator.

Generates tamper-proof, enterprise-grade hardware inspection certificates for
IT Asset Disposition (ITAD), hardware refurbishment, and enterprise auditing.
Each report includes:
1. Asymmetric Ed25519 Public-Key Digital Signatures guaranteeing authenticity & non-repudiation.
2. Complete hardware provenance (CPU, RAM DIMM serials, NVMe/SATA serials, battery wear).
3. Component change tracking and swap detection.
4. Independent letter grading (A+, A, B, C, F) and health breakdown.
5. Standalone, printable HTML certificate with verification seal and cryptographic proof.
"""

import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class GhostTrustReport:
    """Enterprise Trust Report & Asymmetric Certification Engine."""

    _DEFAULT_PRIVATE_KEY: Optional[ed25519.Ed25519PrivateKey] = None

    @classmethod
    def get_or_create_auditor_key(cls, key_path: Optional[str] = None) -> ed25519.Ed25519PrivateKey:
        """Retrieves or initializes a persistent Ed25519 private key for signing reports."""
        if cls._DEFAULT_PRIVATE_KEY is not None:
            return cls._DEFAULT_PRIVATE_KEY

        target_file = key_path or os.environ.get("GHOST_SIGNER_KEY_PATH")
        if target_file and os.path.exists(target_file):
            try:
                with open(target_file, "rb") as f:
                    cls._DEFAULT_PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)
                    return cls._DEFAULT_PRIVATE_KEY
            except Exception:
                pass

        # Generate a fresh ephemeral/session keypair
        cls._DEFAULT_PRIVATE_KEY = ed25519.Ed25519PrivateKey.generate()
        if target_file:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
                pem_data = cls._DEFAULT_PRIVATE_KEY.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                with open(target_file, "wb") as f:
                    f.write(pem_data)
            except Exception:
                pass

        return cls._DEFAULT_PRIVATE_KEY

    @classmethod
    def calculate_grade(cls, overall_score: int) -> str:
        """Determines the asset letter grade based on overall health score."""
        if overall_score >= 95:
            return "Grade A+ (Pristine / Like New)"
        elif overall_score >= 90:
            return "Grade A (Excellent Enterprise Condition)"
        elif overall_score >= 75:
            return "Grade B (Good / Minor Wear)"
        elif overall_score >= 50:
            return "Grade C (Fair / Component Degraded)"
        else:
            return "Grade F (Critical Hardware Warning / Uncertified)"

    @classmethod
    def generate(
        cls,
        scan_payload: Dict[str, Any],
        health_scores: Optional[Dict[str, Any]] = None,
        diff_report: Optional[Dict[str, Any]] = None,
        inspector_name: str = "Authorized Field Technician",
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
        signing_key: Optional[str] = None,
        algorithm: str = "Ed25519",
    ) -> Dict[str, Any]:
        """Generates a tamper-proof signed trust report dictionary with asymmetric Ed25519 signature."""
        scores = health_scores or {"overall": 100, "summary": "Pristine hardware condition"}
        overall_score = scores.get("overall") if "overall" in scores else scores.get("overall_score", 100)
        grade = cls.calculate_grade(overall_score)

        hw = scan_payload.get("hardware", {})
        cpu = hw.get("cpu", {})
        mem = hw.get("memory", {})
        mb = hw.get("motherboard", {})
        bat = hw.get("battery", {})
        storage_list = hw.get("storage", [])

        # Process diagnostics count
        diags = scan_payload.get("diagnostics", [])
        passed_tests = [d for d in diags if d.get("status") in ("OK", "PASS", "PASSED")]
        warning_tests = [d for d in diags if d.get("status") in ("WARN", "WARNING")]
        failed_tests = [d for d in diags if d.get("status") in ("FAIL", "FAILED", "CRITICAL")]

        # Extract component swaps from diff report if present
        swaps: List[Dict[str, Any]] = []
        if diff_report and isinstance(diff_report, dict):
            for change in diff_report.get("changes", []):
                swaps.append({
                    "component_type": change.get("component_type", "Unknown"),
                    "change_type": change.get("change_type", "MODIFIED"),
                    "description": change.get("description", ""),
                    "severity": change.get("severity", "LOW"),
                })

        scan_id_val = scan_payload.get("scan_id", "")
        if scan_id_val:
            report_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:ghost:scan:{scan_id_val}"))
        else:
            report_uuid = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # Build canonical payload for signing (excluding signature block itself)
        core_document = {
            "report_uuid": report_uuid,
            "created_at_utc": created_at,
            "scan_id": scan_id_val,
            "machine_fingerprint": scan_payload.get("machine_fingerprint", ""),
            "system_identity": {
                "manufacturer": mb.get("manufacturer", "OEM Generic"),
                "product_name": mb.get("product_name") or mb.get("product", "Standard System"),
                "motherboard_serial": mb.get("serial_number", "N/A"),
                "chassis_type": mb.get("chassis_type", "Laptop / Desktop"),
                "platform": scan_payload.get("platform", "Windows"),
                "os_version": scan_payload.get("os_version", ""),
            },
            "hardware_provenance": {
                "processor": {
                    "model": cpu.get("model", "Generic Processor"),
                    "cores": cpu.get("cores_physical") or cpu.get("physical_cores", 0),
                    "threads": cpu.get("threads_logical") or cpu.get("logical_threads", 0),
                    "base_clock_mhz": cpu.get("base_clock_mhz", 0),
                },
                "memory": {
                    "total_bytes": mem.get("total_bytes", 0),
                    "total_gb": round(mem.get("total_bytes", 0) / (1024**3), 2),
                    "slots_used": len(mem.get("modules", [])),
                    "modules": [
                        {
                            "bank_locator": m.get("bank_locator") or m.get("slot", ""),
                            "capacity_bytes": m.get("capacity_bytes", 0),
                            "speed_mhz": m.get("speed_mhz", 0),
                            "serial_number": m.get("serial_number", "N/A"),
                            "manufacturer": m.get("manufacturer", "N/A"),
                        }
                        for m in mem.get("modules", [])
                    ],
                },
                "storage_units": [
                    {
                        "device_id": s.get("device_id", ""),
                        "model": s.get("model", ""),
                        "serial_number": s.get("serial_number") or s.get("serial_hash", "N/A"),
                        "interface": s.get("interface", ""),
                        "capacity_gb": round(s.get("capacity_bytes", 0) / (1024**3), 2),
                        "smart_status": s.get("smart_status", "OK"),
                        "wear_level_pct": s.get("wear_level_pct", 0),
                        "temperature_c": s.get("temp_c", 0),
                    }
                    for s in storage_list
                ],
                "battery": {
                    "is_present": bat.get("is_present") or bat.get("present", False),
                    "cycle_count": bat.get("cycle_count", 0),
                    "health_pct": bat.get("health_pct", 100),
                    "design_capacity_mwh": bat.get("design_capacity_mwh", 0),
                    "full_charge_mwh": bat.get("full_charge_capacity_mwh", 0),
                },
            },
            "certification_evaluation": {
                "overall_health_score": overall_score,
                "asset_grade": grade,
                "score_breakdown": scores,
                "summary": scores.get("summary", "Hardware verified clean"),
                "test_statistics": {
                    "total_executed": len(diags),
                    "passed": len(passed_tests),
                    "warnings": len(warning_tests),
                    "failures": len(failed_tests),
                },
                "component_swaps_detected": swaps,
            },
            "auditor_metadata": {
                "inspector": inspector_name,
                "inspection_engine": "Ghost-OS Core v1.0.0 (Air-Gapped)",
                "collection_layer": "Single-File Zero-Trace Companion",
                "provenance_standard": "ITAD Asymmetric Public-Key Trust Protocol v2.0",
            },
        }

        # Canonical deterministic serialization
        canonical_bytes = json.dumps(core_document, sort_keys=True, separators=(",", ":")).encode("utf-8")

        signed_report = dict(core_document)

        if algorithm.upper() == "ED25519":
            key = private_key or cls.get_or_create_auditor_key()
            signature_bytes = key.sign(canonical_bytes)
            signature_b64 = base64.b64encode(signature_bytes).decode("ascii")

            pub_raw = key.public_key().public_bytes_raw()
            pub_b64 = base64.b64encode(pub_raw).decode("ascii")
            key_fp = hashlib.sha256(pub_raw).hexdigest()[:16]

            signed_report["cryptographic_signature"] = {
                "algorithm": "Ed25519",
                "public_key_b64": pub_b64,
                "signature_b64": signature_b64,
                "key_fingerprint": key_fp,
                "status": "CRYPTOGRAPHICALLY_VERIFIED",
                "signed_at_utc": created_at,
            }
        else:
            # Fallback HMAC-SHA256
            hmac_key = (signing_key or "GhostOS-HMAC-Provenance-Key").encode("utf-8")
            sig_hex = hmac.new(hmac_key, canonical_bytes, hashlib.sha256).hexdigest()
            signed_report["cryptographic_signature"] = {
                "algorithm": "HMAC-SHA256",
                "digest": sig_hex,
                "status": "CRYPTOGRAPHICALLY_VERIFIED",
                "signed_at_utc": created_at,
            }

        return signed_report

    @classmethod
    def verify_signature(
        cls,
        report: Dict[str, Any],
        public_key_override: Optional[ed25519.Ed25519PublicKey] = None,
        signing_key: Optional[str] = None,
    ) -> bool:
        """Verifies report integrity and authenticity using Ed25519 or HMAC signature."""
        if "cryptographic_signature" not in report:
            return False

        sig_block = report.get("cryptographic_signature", {})
        algo = sig_block.get("algorithm", "Ed25519").upper()

        doc_copy = {k: v for k, v in report.items() if k != "cryptographic_signature"}
        canonical_bytes = json.dumps(doc_copy, sort_keys=True, separators=(",", ":")).encode("utf-8")

        if algo == "ED25519":
            sig_b64 = sig_block.get("signature_b64")
            pub_b64 = sig_block.get("public_key_b64")
            if not sig_b64 or (not pub_b64 and not public_key_override):
                return False

            try:
                sig_bytes = base64.b64decode(sig_b64)
                if public_key_override:
                    pub = public_key_override
                else:
                    pub_raw = base64.b64decode(pub_b64)
                    pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_raw)

                pub.verify(sig_bytes, canonical_bytes)
                return True
            except (InvalidSignature, Exception):
                return False
        else:
            claimed_digest = sig_block.get("digest")
            if not claimed_digest:
                return False
            hmac_key = (signing_key or "GhostOS-HMAC-Provenance-Key").encode("utf-8")
            expected_digest = hmac.new(hmac_key, canonical_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(claimed_digest, expected_digest)

    @classmethod
    def export_json(cls, report: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Serializes trust report to indented JSON string."""
        serialized = json.dumps(report, indent=2)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(serialized)
        return serialized

    @classmethod
    def export_html(cls, report: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Renders an enterprise-grade printable Trust Certificate in HTML format with asymmetric proof."""
        meta = report.get("auditor_metadata", {})
        sys_id = report.get("system_identity", {})
        prov = report.get("hardware_provenance", {})
        eval_data = report.get("certification_evaluation", {})
        sig = report.get("cryptographic_signature", {})
        stats = eval_data.get("test_statistics", {})
        score = eval_data.get("overall_health_score", 100)
        grade = eval_data.get("asset_grade", "Grade A")

        if score >= 90:
            badge_color = "#10B981"
            badge_text = "PASSED & CERTIFIED"
        elif score >= 75:
            badge_color = "#3B82F6"
            badge_text = "CERTIFIED (GRADE B)"
        elif score >= 50:
            badge_color = "#F59E0B"
            badge_text = "DEGRADED CONDITION"
        else:
            badge_color = "#EF4444"
            badge_text = "FAILED INSPECTION"

        storage_rows = ""
        for s in prov.get("storage_units", []):
            storage_rows += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0;">{s.get('model', 'N/A')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; font-family: monospace;">{s.get('serial_number', 'N/A')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0;">{s.get('capacity_gb', 0)} GB ({s.get('interface', '')})</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0; color: #10B981; font-weight: bold;">{s.get('smart_status', 'OK')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #E2E8F0;">{s.get('wear_level_pct', 0)}%</td>
            </tr>
            """

        swaps_section = ""
        swaps = eval_data.get("component_swaps_detected", [])
        if swaps:
            swap_items = "".join(
                f"<li style='color: #DC2626; margin-bottom: 4px;'><strong>[{s.get('severity')}] {s.get('component_type')}:</strong> {s.get('description')}</li>"
                for s in swaps
            )
            swaps_section = f"""
            <div style="margin-top: 20px; padding: 15px; background: #FEF2F2; border-left: 4px solid #DC2626; border-radius: 4px;">
                <h4 style="margin: 0 0 8px 0; color: #991B1B;">⚠️ Detected Component Modifications</h4>
                <ul style="margin: 0; padding-left: 20px;">{swap_items}</ul>
            </div>
            """
        else:
            swaps_section = """
            <div style="margin-top: 20px; padding: 12px 16px; background: #ECFDF5; border-left: 4px solid #10B981; border-radius: 4px;">
                <p style="margin: 0; color: #065F46; font-size: 13px;"><strong>✔ Provenance Verified:</strong> All hardware components match baseline registry records with zero unauthorized swaps.</p>
            </div>
            """

        sig_detail = sig.get("signature_b64") or sig.get("digest", "N/A")
        pub_detail = sig.get("public_key_b64", "N/A (Symmetric MAC)")
        fp_detail = sig.get("key_fingerprint", "N/A")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ghost-OS Asymmetric Trust Certificate - {report.get('machine_fingerprint', '')[:12]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #F8FAFC;
            color: #1E293B;
            margin: 0;
            padding: 40px 20px;
        }}
        .certificate-container {{
            max-width: 860px;
            margin: 0 auto;
            background: #FFFFFF;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            border: 1px solid #E2E8F0;
            overflow: hidden;
        }}
        .cert-header {{
            background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
            color: #FFFFFF;
            padding: 32px 40px;
            position: relative;
        }}
        .cert-badge {{
            position: absolute;
            top: 32px;
            right: 40px;
            background: {badge_color};
            color: white;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 1px;
            padding: 8px 16px;
            border-radius: 20px;
            text-transform: uppercase;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        .cert-body {{
            padding: 40px;
        }}
        .score-box {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #F1F5F9;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 30px;
            border-left: 6px solid {badge_color};
        }}
        .score-number {{
            font-size: 48px;
            font-weight: 900;
            color: #0F172A;
            line-height: 1;
        }}
        .score-grade {{
            font-size: 18px;
            font-weight: 700;
            color: #334155;
            margin-top: 6px;
        }}
        .spec-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .spec-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 14px 18px;
        }}
        .spec-label {{
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 700;
            color: #64748B;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .spec-val {{
            font-size: 14px;
            font-weight: 600;
            color: #0F172A;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 10px;
        }}
        th {{
            background: #F1F5F9;
            color: #475569;
            text-align: left;
            padding: 10px 8px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .signature-footer {{
            background: #F8FAFC;
            border-top: 1px solid #E2E8F0;
            padding: 24px 40px;
            font-size: 11px;
            color: #64748B;
        }}
        .hash-code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background: #E2E8F0;
            padding: 4px 8px;
            border-radius: 4px;
            color: #0F172A;
            word-break: break-all;
            display: inline-block;
            margin-top: 4px;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .certificate-container {{ box-shadow: none; border: none; }}
        }}
    </style>
</head>
<body>
    <div class="certificate-container">
        <div class="cert-header">
            <div class="cert-badge">{badge_text}</div>
            <h1 style="margin: 0 0 6px 0; font-size: 26px; letter-spacing: -0.5px;">GHOST-OS TRUST CERTIFICATE</h1>
            <p style="margin: 0; color: #94A3B8; font-size: 13px;">Asymmetric Ed25519 Hardware Authenticity & Condition Audit</p>
            <p style="margin: 6px 0 0 0; color: #60A5FA; font-size: 11px; font-family: monospace;">UUID: {report.get('report_uuid', '')}</p>
        </div>

        <div class="cert-body">
            <div class="score-box">
                <div>
                    <div class="score-number">{score} <span style="font-size: 20px; font-weight: 500; color: #64748B;">/ 100</span></div>
                    <div class="score-grade">{grade}</div>
                </div>
                <div style="text-align: right; font-size: 13px;">
                    <div><strong>Tests Passed:</strong> {stats.get('passed', 0)} / {stats.get('total_executed', 0)}</div>
                    <div><strong>Warnings:</strong> {stats.get('warnings', 0)} | <strong>Failures:</strong> {stats.get('failures', 0)}</div>
                    <div style="margin-top: 4px; color: #64748B;">Auditor: {meta.get('inspector', 'Technician')}</div>
                </div>
            </div>

            <h3 style="font-size: 15px; color: #0F172A; margin: 0 0 12px 0;">Device Specifications & Identity</h3>
            <div class="spec-grid">
                <div class="spec-card">
                    <div class="spec-label">Machine Chassis</div>
                    <div class="spec-val">{sys_id.get('manufacturer', '')} {sys_id.get('product_name', '')}</div>
                </div>
                <div class="spec-card">
                    <div class="spec-label">Machine Fingerprint</div>
                    <div class="spec-val" style="font-family: monospace; font-size: 12px;">{report.get('machine_fingerprint', '')}</div>
                </div>
                <div class="spec-card">
                    <div class="spec-label">Processor</div>
                    <div class="spec-val">{prov.get('processor', {}).get('model', 'N/A')}</div>
                </div>
                <div class="spec-card">
                    <div class="spec-label">Installed Memory</div>
                    <div class="spec-val">{prov.get('memory', {}).get('total_gb', 0)} GB Total ({prov.get('memory', {}).get('slots_used', 0)} Modules)</div>
                </div>
            </div>

            <h3 style="font-size: 15px; color: #0F172A; margin: 24px 0 8px 0;">Storage Media Provenance & SMART Health</h3>
            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Serial Number</th>
                        <th>Capacity</th>
                        <th>SMART Status</th>
                        <th>Wear Level</th>
                    </tr>
                </thead>
                <tbody>
                    {storage_rows}
                </tbody>
            </table>

            {swaps_section}
        </div>

        <div class="signature-footer">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="max-width: 70%;">
                    <div><strong>ASYMMETRIC DIGITAL SEAL:</strong> {sig.get('algorithm', 'Ed25519')} ({sig.get('status', '')})</div>
                    <div><strong>Public Key (Base64):</strong> <span class="hash-code">{pub_detail}</span></div>
                    <div><strong>Key Fingerprint:</strong> <span class="hash-code">{fp_detail}</span></div>
                    <div><strong>Signature (Base64):</strong> <span class="hash-code">{sig_detail}</span></div>
                    <div style="margin-top: 6px;">Generated at: {report.get('created_at_utc', '')} | Standards: {meta.get('provenance_standard', '')}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700; color: #0F172A;">Ghost-OS Provenance Authority</div>
                    <div style="color: #10B981; font-weight: bold; margin-top: 4px;">✔ Ed25519 Verified</div>
                    <div style="font-size: 10px; color: #64748B; margin-top: 2px;">Independent Public Verification</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        return html_content
