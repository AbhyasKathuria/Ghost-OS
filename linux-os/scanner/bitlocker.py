"""BitLocker Volume Detection and Safe Mount Assistant for Ghost-OS Linux Boot Mode.

Enables safe, read-only inspection and recovery of BitLocker-encrypted Windows partitions:
1. Detects BitLocker signatures via blkid / lsblk.
2. Formats diagnostic status for security compliance.
3. Prepares dislocker read-only mount commands with 48-digit recovery key escrow.
"""

import subprocess
from typing import Dict, List, Optional, Tuple
from ghost_core.schemas.scan import DiagnosticResult, DiagnosticStatus


class BitLockerAssistant:
    @staticmethod
    def detect_bitlocker_partitions() -> List[Dict[str, str]]:
        """Scans block devices for BitLocker signatures."""
        encrypted_partitions: List[Dict[str, str]] = []
        try:
            res = subprocess.run(
                ["lsblk", "-o", "NAME,FSTYPE,UUID,SIZE,MOUNTPOINT", "-J"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                import json
                data = json.loads(res.stdout)
                for dev in data.get("blockdevices", []):
                    BitLockerAssistant._check_device(dev, encrypted_partitions)
        except Exception:
            pass

        return encrypted_partitions

    @staticmethod
    def _check_device(dev: dict, out_list: list):
        fstype = dev.get("fstype", "") or ""
        if "bitlocker" in fstype.lower():
            out_list.append({
                "name": dev.get("name", ""),
                "uuid": dev.get("uuid", "unknown"),
                "size": dev.get("size", "unknown"),
                "status": "LOCKED",
            })
        for child in dev.get("children", []):
            BitLockerAssistant._check_device(child, out_list)

    @staticmethod
    def evaluate_bitlocker_state(partitions: List[Dict[str, str]]) -> DiagnosticResult:
        """Emits diagnostic results describing Windows volume BitLocker protection."""
        if not partitions:
            return DiagnosticResult(
                test_name="Storage Volume BitLocker Protection",
                status=DiagnosticStatus.PASS,
                metric_value=0.0,
                threshold=0.0,
                evidence="No BitLocker-locked volumes detected on primary storage.",
                recommendation="Volumes are unencrypted or standard filesystem (ext4/NTFS/exFAT).",
            )

        names = [p["name"] for p in partitions]
        return DiagnosticResult(
            test_name="Storage Volume BitLocker Protection",
            status=DiagnosticStatus.WARN,
            metric_value=float(len(partitions)),
            threshold=0.0,
            evidence=f"Detected {len(partitions)} BitLocker-encrypted volume(s): {', '.join(names)}. Data protected at rest by AES-128/256.",
            recommendation="To access or recover files in Boot Mode, provide the 48-digit BitLocker recovery key via the Ghost Vault Recovery Assistant.",
        )

    @staticmethod
    def build_dislocker_mount_command(device_node: str, mount_point: str, recovery_key: str) -> str:
        """Constructs an authenticated, read-only dislocker command line."""
        clean_key = recovery_key.strip().replace(" ", "")
        return (
            f"dislocker -r -V {device_node} -p{clean_key} -- /tmp/dislocker-file && "
            f"mount -o loop,ro /tmp/dislocker-file/dislocker-file {mount_point}"
        )
