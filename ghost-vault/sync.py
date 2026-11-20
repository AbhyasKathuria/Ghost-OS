"""Off-USB Vault Replication, Cloud/NAS Escrow, and Disaster Recovery for Ghost-OS.

Ensures that if the physical USB flash drive is lost, stolen, or mechanically fails,
all historical machine inventory and diagnostic audits can be 100% recovered from
an encrypted escrow backup.
"""

import hashlib
import json
import os
import shutil
import time
from typing import Dict, List, Optional, Tuple


class VaultSyncManager:
    @staticmethod
    def export_encrypted_escrow_backup(
        vault_dir: str,
        backup_destination_dir: str,
    ) -> Tuple[bool, str, Dict[str, str]]:
        """Creates a timestamped, integrity-verified encrypted backup on external/secondary storage."""
        if not os.path.exists(vault_dir):
            return False, f"Source vault directory not found: {vault_dir}", {}

        os.makedirs(backup_destination_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_filename = f"ghost_vault_backup_{timestamp}.enc"
        manifest_filename = f"backup_manifest_{timestamp}.json"

        src_enc = os.path.join(vault_dir, "vault.enc")
        if not os.path.exists(src_enc):
            return False, f"Active vault container missing: {src_enc}", {}

        dst_enc = os.path.join(backup_destination_dir, backup_filename)
        shutil.copy2(src_enc, dst_enc)

        # Compute SHA-256 hash for cryptographic verification
        with open(dst_enc, "rb") as f:
            enc_hash = hashlib.sha256(f.read()).hexdigest()

        manifest = {
            "timestamp": timestamp,
            "backup_file": backup_filename,
            "enc_sha256": enc_hash,
            "size_bytes": os.path.getsize(dst_enc),
            "status": "VALID_ENCRYPTED_SNAPSHOT",
        }

        manifest_path = os.path.join(backup_destination_dir, manifest_filename)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return True, f"Successfully created encrypted escrow snapshot: {backup_filename}", manifest

    @staticmethod
    def restore_from_escrow_backup(
        backup_file: str,
        target_vault_dir: str,
        expected_manifest_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Restores an encrypted vault snapshot to a newly formatted or replacement USB drive."""
        if not os.path.exists(backup_file):
            return False, "Specified backup payload file does not exist."

        # If manifest provided, verify hash first
        if expected_manifest_path and os.path.exists(expected_manifest_path):
            try:
                with open(expected_manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                with open(backup_file, "rb") as f:
                    curr_enc_hash = hashlib.sha256(f.read()).hexdigest()
                if curr_enc_hash != manifest.get("enc_sha256"):
                    return False, "Integrity check failed: Backup file hash does not match manifest."
            except Exception as e:
                return False, f"Manifest verification error: {e}"

        os.makedirs(target_vault_dir, exist_ok=True)
        dst_enc = os.path.join(target_vault_dir, "vault.enc")

        shutil.copy2(backup_file, dst_enc)
        return True, "Vault successfully restored to target USB directory. Ready for unlocking."
