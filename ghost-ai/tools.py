"""Ghost-AI Strictly Scoped Read-Only Vault Query & Diagnostic Tools.

Provides deterministic function calling tools over the active decrypted SQLite database
for offline RAG intelligence, preventing hallucination by anchoring directly to vault facts.
"""

import json
from typing import Any, Dict, List, Optional
from ghost_core.diagnostics.diff import HardwareDiffEngine
from ghost_core.schemas.scan import NormalizedScanPayload
from ghost_vault.db import GhostVaultDB

# Known SMART attribute reference database
SMART_KNOWLEDGE_BASE = {
    "percentage_used": {
        "title": "NVMe Flash Wear / Percentage Used",
        "description": "Vendor-neutral estimate of the percentage of NVM subsystem life that has been consumed (0% = new, 100% = rated write endurance reached).",
        "critical_threshold": 90,
        "action": "If >= 90%, plan drive replacement. Flash blocks may exceed rated program-erase endurance cycles.",
    },
    "available_spare": {
        "title": "NVMe Available Spare Blocks",
        "description": "Normalized percentage (0-100%) of the remaining spare capacity available for handling block retirement.",
        "critical_threshold": 10,
        "action": "If < 10%, drive is exhausting redundant NAND cells. Immediate backup and replacement required.",
    },
    "critical_warning": {
        "title": "NVMe Critical Warning Flags",
        "description": "Bitmask indicating reliability degradation: spare below threshold, temperature threshold exceeded, NVM subsystem reliability degraded, media read-only, or volatile memory backup device failed.",
        "critical_threshold": 0,
        "action": "Any non-zero bit indicates severe hardware danger. Back up critical data immediately.",
    },
    "media_errors": {
        "title": "Media and Data Integrity Errors",
        "description": "Number of occurrences where unrecoverable data integrity errors occurred (uncorrectable ECC errors, CRC errors).",
        "critical_threshold": 0,
        "action": "If > 0, physical flash cells are corrupted. Run filesystem consistency check and replace SSD.",
    },
    "reallocated_sector_count": {
        "title": "SATA Reallocated Sectors Count (Attribute 05)",
        "description": "Count of bad physical sectors that have been remapped to spare sectors.",
        "critical_threshold": 5,
        "action": "Any rising count of reallocated sectors indicates active platter surface breakdown.",
    },
    "temperature": {
        "title": "Drive Operating Temperature",
        "description": "Internal composite controller and NAND temperature measured by thermal sensors.",
        "critical_threshold": 70,
        "action": "Temperatures > 70°C throttle throughput and accelerate flash wear. Improve heatsink contact.",
    },
}


class VaultInspectionTools:
    """Read-only querying tools over decrypted in-memory SQLite database."""

    def __init__(self, vault: GhostVaultDB):
        self.vault = vault

    def get_machine_history(self, machine_fingerprint: str) -> Dict[str, Any]:
        """Retrieves machine specifications, scan timeline, and health scores."""
        machine = self.vault.get_machine(machine_fingerprint)
        if not machine:
            return {"error": f"Machine fingerprint '{machine_fingerprint}' not found in vault registry."}

        scans = self.vault.get_machine_scans(machine_fingerprint)
        latest_scan = self.vault.get_latest_scan(machine_fingerprint)
        maint_records = self.vault.list_maintenance_records(machine_fingerprint)

        return {
            "machine": machine,
            "total_scans": len(scans),
            "latest_scan_utc": machine.get("latest_scan_utc"),
            "latest_health_score": machine.get("latest_health_score"),
            "hardware_summary": latest_scan.get("raw_payload", {}).get("hardware") if latest_scan else None,
            "recent_scans": scans[:5],
            "maintenance_records": maint_records,
        }

    def find_warnings(self, severity: str = "ALL", machine_fingerprint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Finds active warnings and failing diagnostic assertions across the fleet or a specific machine."""
        cur = self.vault._conn.cursor()
        query = """
            SELECT d.test_name, d.status, d.metric_value, d.threshold, d.evidence, d.recommendation,
                   s.scan_id, s.machine_fingerprint, s.timestamp_utc, s.platform
            FROM diagnostic_results d
            JOIN scan_sessions s ON d.scan_id = s.scan_id
            WHERE 1=1
        """
        params: List[Any] = []

        sev_up = severity.upper()
        if sev_up in ("WARN", "FAIL"):
            query += " AND d.status = ?"
            params.append(sev_up)
        else:
            query += " AND d.status IN ('WARN', 'FAIL')"

        if machine_fingerprint:
            query += " AND s.machine_fingerprint = ?"
            params.append(machine_fingerprint)

        query += " ORDER BY s.timestamp_utc DESC LIMIT 50"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def compare_scans(
        self,
        machine_fingerprint: str,
        scan1: Optional[str] = None,
        scan2: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Computes hardware change deltas and degradation alerts between two historical scans."""
        scans = self.vault.get_machine_scans(machine_fingerprint)
        if len(scans) < 2 and (not scan1 or not scan2):
            return {
                "error": f"Machine '{machine_fingerprint}' only has {len(scans)} scan. At least 2 scans are needed to detect changes."
            }

        id_target = scan2 or scans[0]["scan_id"]
        id_baseline = scan1 or scans[1]["scan_id"]

        rec_base = self.vault.get_scan(id_baseline)
        rec_target = self.vault.get_scan(id_target)

        if not rec_base or not rec_target:
            return {"error": "One or both specified scan records could not be found."}

        p_base = NormalizedScanPayload.model_validate(rec_base["raw_payload"])
        p_target = NormalizedScanPayload.model_validate(rec_target["raw_payload"])

        diff = HardwareDiffEngine.compare_scans(baseline=p_base, current=p_target)
        return diff.model_dump()

    def explain_smart_attribute(self, attribute_name_or_id: str) -> Dict[str, Any]:
        """Returns deep engineering explanation and recommended actions for a storage SMART indicator."""
        clean = attribute_name_or_id.lower().replace(" ", "_").replace("-", "_")

        for key, info in SMART_KNOWLEDGE_BASE.items():
            if key in clean or clean in key:
                return {
                    "attribute": key,
                    "title": info["title"],
                    "description": info["description"],
                    "critical_threshold": info["critical_threshold"],
                    "recommended_action": info["action"],
                }

        return {
            "attribute": attribute_name_or_id,
            "title": "General SMART Telemetry Attribute",
            "description": "Standard self-monitoring analysis and reporting metric tracked by drive firmware.",
            "critical_threshold": "Vendor-specific",
            "recommended_action": "Check vendor-specific raw attributes for escalating normalized value decreases.",
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns OpenAPI/JSON function calling schemas for LLM tool selection."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_machine_history",
                    "description": "Retrieves verified hardware specifications, scan history, health scores, and service logs for a machine by its fingerprint.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "machine_fingerprint": {
                                "type": "string",
                                "description": "The 64-character SHA-256 machine fingerprint."
                            }
                        },
                        "required": ["machine_fingerprint"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_warnings",
                    "description": "Finds all active warning (WARN) or failure (FAIL) diagnostic results across machines in the vault.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "severity": {
                                "type": "string",
                                "enum": ["ALL", "WARN", "FAIL"],
                                "description": "Filter by severity level."
                            },
                            "machine_fingerprint": {
                                "type": "string",
                                "description": "Optional specific machine fingerprint to filter by."
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "compare_scans",
                    "description": "Computes exact hardware changes, component replacements, and degradation alerts between two scans.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "machine_fingerprint": {
                                "type": "string",
                                "description": "The machine fingerprint."
                            },
                            "scan1": {
                                "type": "string",
                                "description": "Baseline scan ID (older scan)."
                            },
                            "scan2": {
                                "type": "string",
                                "description": "Target scan ID (newer scan)."
                            }
                        },
                        "required": ["machine_fingerprint"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "explain_smart_attribute",
                    "description": "Explains the physical and logical meaning of an SSD/HDD SMART attribute and what technician action is required.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "attribute_name_or_id": {
                                "type": "string",
                                "description": "Name or ID of the SMART attribute (e.g., 'percentage_used', 'media_errors', 'available_spare')."
                            }
                        },
                        "required": ["attribute_name_or_id"]
                    }
                }
            }
        ]
