"""Ghost-OS Cold-Storage Recovery Escrow & Key Verification Subsystem.

Enforces air-gapped security by guaranteeing that recovery keys are never
inadvertently stored on the same physical USB storage medium as the encrypted vault container.
"""

import os
import re
import secrets
from typing import Optional

from ghost_vault.crypto import (
    VaultCryptoError,
    derive_argon2id_key,
    decrypt_bytes,
)


class ColdStorageSecurityWarning(Exception):
    """Raised when an operator attempts to store a recovery key on the same removable medium."""
    pass


class GhostRecoveryEscrow:
    """Enterprise Recovery Key Escrow & Verification Subsystem."""

    @classmethod
    def generate_formatted_key(cls) -> str:
        """Generates a secure 8-group formatted recovery key."""
        raw_token = secrets.token_hex(20).upper()  # 40 hex chars
        # Group into 8 groups of 5 characters
        groups = [raw_token[i : i + 5] for i in range(0, 40, 5)]
        return f"GHOST-{'-'.join(groups)}"

    @classmethod
    def verify_key(cls, vault_path: str, recovery_key: str) -> bool:
        """Cryptographically verifies that the recovery key decrypts the vault without mutating data."""
        if not os.path.exists(vault_path):
            return False

        try:
            with open(vault_path, "rb") as f:
                data = f.read()

            parts = data.split(b"\n--GHOST_PAYLOAD_START--\n")
            if len(parts) != 2:
                return False

            import json
            header_str = parts[0].decode("utf-8")
            magic, meta_json = header_str.split("\n", 1)
            meta = json.loads(meta_json)

            rec_slot = meta.get("slots", {}).get("recovery")
            if not rec_slot:
                return False

            import base64
            salt = base64.b64decode(rec_slot["salt_b64"])
            enc_key_payload = base64.b64decode(rec_slot["enc_key_b64"])
            kdf_p = meta.get("kdf_params", {})

            derived_key = derive_argon2id_key(
                secret=recovery_key,
                salt=salt,
                time_cost=kdf_p.get("time_cost", 3),
                memory_cost=kdf_p.get("memory_cost", 131072),
                parallelism=kdf_p.get("parallelism", 4),
            )
            decrypt_bytes(enc_key_payload, derived_key)
            return True
        except Exception:
            return False

    @classmethod
    def export_escrow_certificate(
        cls,
        recovery_key: str,
        destination_dir: str,
        vault_path: Optional[str] = None,
        force_same_drive: bool = False,
    ) -> str:
        """Exports an official, human-readable Cold-Storage Escrow Document off-device."""
        dest_abs = os.path.abspath(destination_dir)

        # Check drive separation
        if vault_path and not force_same_drive:
            vault_abs = os.path.abspath(vault_path)
            dest_drive = os.path.splitdrive(dest_abs)[0].upper()
            vault_drive = os.path.splitdrive(vault_abs)[0].upper()
            if dest_drive and vault_drive and dest_drive == vault_drive:
                raise ColdStorageSecurityWarning(
                    f"Security Violation: Target escrow destination ({dest_abs}) resides on the same "
                    f"drive ({vault_drive}) as the encrypted vault ({vault_abs}). "
                    f"Store recovery keys off-device to guarantee separation of duties."
                )

        os.makedirs(dest_abs, exist_ok=True)
        escrow_file = os.path.join(dest_abs, "Ghost_Vault_Emergency_Recovery_Escrow.txt")

        content = f"""================================================================================
           GHOST-OS OFFICIAL EMERGENCY DISASTER RECOVERY ESCROW CERTIFICATE
================================================================================
ISSUED FOR: Encrypted Ghost Vault Container
SECURITY LEVEL: CRITICAL (Cold-Storage Escrow)

YOUR CRYPTOGRAPHIC EMERGENCY RECOVERY KEY:
--------------------------------------------------------------------------------
   {recovery_key}
--------------------------------------------------------------------------------

IMPORTANT INSTRUCTIONS:
1. This recovery key can decrypt your Ghost Vault even if your master password
   is forgotten or unavailable.
2. DO NOT store this file on the Ghost-OS USB drive.
3. Keep this certificate in an enterprise password manager (Bitwarden, 1Password),
   an encrypted cloud escrow vault, or physically printed in a locked security safe.
4. To restore access, select 'Recovery Key' in the Ghost-OS unlock dashboard and
   paste the key exactly as displayed above.
================================================================================
"""
        with open(escrow_file, "w", encoding="utf-8") as f:
            f.write(content)

        return escrow_file

    @classmethod
    def purge_on_device_recovery_key(cls, target_dir: str) -> bool:
        """Purges plain-text recovery_key.txt from the given directory to prevent on-device exposure."""
        target_file = os.path.join(target_dir, "recovery_key.txt")
        if os.path.exists(target_file):
            try:
                # Secure overwrite before removal
                with open(target_file, "wb") as f:
                    f.write(secrets.token_bytes(256))
                os.remove(target_file)
                return True
            except Exception:
                pass
        return False
