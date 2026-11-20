"""Ghost Vault - Encrypted persistence layer."""
from .crypto import (
    VaultCryptoError,
    derive_argon2id_key,
    encrypt_bytes,
    decrypt_bytes,
    generate_recovery_key,
    pack_vault,
    unlock_vault,
)
from .db import GhostVaultDB
from .escrow import GhostRecoveryEscrow, ColdStorageSecurityWarning

__all__ = [
    "VaultCryptoError",
    "derive_argon2id_key",
    "encrypt_bytes",
    "decrypt_bytes",
    "generate_recovery_key",
    "pack_vault",
    "unlock_vault",
    "GhostVaultDB",
    "GhostRecoveryEscrow",
    "ColdStorageSecurityWarning",
]
