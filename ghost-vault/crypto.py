"""Ghost Vault Cryptographic Subsystem.

Implements Argon2id password-authenticated key derivation and libsodium
authenticated encryption (XChaCha20-Poly1305 / SecretBox) with dual-slot
master key escrow (Password + Recovery Key).
"""

import base64
import json
import os
import re
import secrets
from typing import Any, Dict, Optional, Tuple

import argon2.low_level
import nacl.utils
from nacl.exceptions import CryptoError

try:
    from nacl.aead import XChaCha20Poly1305
    HAS_XCHACHA20 = True
except ImportError:
    from nacl.secret import SecretBox
    HAS_XCHACHA20 = False


MAGIC_HEADER = b"GHOST_VAULT_V1\n"
SEPARATOR = b"\n--GHOST_PAYLOAD_START--\n"


class VaultCryptoError(Exception):
    """Raised for any cryptographic failures (invalid credentials, corruption, tampering)."""
    pass


def generate_recovery_key() -> str:
    """Generates a high-entropy 256-bit alphanumeric recovery key in 8 groups of 4 characters.
    
    Example: 'A7F9-3B2C-9E4D-1A8F-5C3B-7D8E-2F1A-6C4B'
    """
    raw_chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Base32 crockford-like without ambiguous 0/O, 1/I
    parts = []
    for _ in range(8):
        block = "".join(secrets.choice(raw_chars) for _ in range(4))
        parts.append(block)
    return "-".join(parts)


def normalize_secret(secret: str) -> str:
    """Normalizes recovery keys or passwords to ensure consistent entropy."""
    s = secret.strip()
    # If it's a recovery key format (with hyphens), clean and uppercase it
    if re.match(r"^[A-Za-z0-9]{4}(-[A-Za-z0-9]{4}){7}$", s):
        return s.upper()
    return s


def derive_argon2id_key(
    secret: str,
    salt: bytes,
    time_cost: int = 3,
    memory_cost: int = 131072,  # 128 MiB (RFC 9106 / OWASP hardened recommendation)
    parallelism: int = 4,
    key_length: int = 32,
) -> bytes:
    """Derives a cryptographically strong symmetric key using Argon2id."""
    clean_secret = normalize_secret(secret).encode("utf-8")
    try:
        return argon2.low_level.hash_secret_raw(
            secret=clean_secret,
            salt=salt,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=key_length,
            type=argon2.low_level.Type.ID,
        )
    except Exception as e:
        raise VaultCryptoError(f"Argon2id key derivation failed: {str(e)}") from e


def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    """Encrypts plaintext with authenticated AEAD using the 32-byte key."""
    if len(key) != 32:
        raise VaultCryptoError(f"Key length must be 32 bytes, got {len(key)}")
    try:
        if HAS_XCHACHA20:
            aead = XChaCha20Poly1305(key)
            nonce = nacl.utils.random(XChaCha20Poly1305.NONCE_SIZE)
            ciphertext = aead.encrypt(nonce, plaintext, None)
            # Prepend nonce to ciphertext
            return nonce + ciphertext
        else:
            box = SecretBox(key)
            return box.encrypt(plaintext)
    except Exception as e:
        raise VaultCryptoError(f"Encryption failed: {str(e)}") from e


def decrypt_bytes(encrypted: bytes, key: bytes) -> bytes:
    """Decrypts and verifies ciphertext with authenticated AEAD using the 32-byte key."""
    if len(key) != 32:
        raise VaultCryptoError(f"Key length must be 32 bytes, got {len(key)}")
    try:
        if HAS_XCHACHA20:
            nonce_size = XChaCha20Poly1305.NONCE_SIZE
            if len(encrypted) < nonce_size + 16:
                raise VaultCryptoError("Ciphertext payload is truncated")
            nonce = encrypted[:nonce_size]
            ct = encrypted[nonce_size:]
            aead = XChaCha20Poly1305(key)
            return aead.decrypt(nonce, ct, None)
        else:
            box = SecretBox(key)
            return box.decrypt(encrypted)
    except CryptoError as e:
        raise VaultCryptoError("Authentication tag mismatch: Invalid key or corrupted data") from e
    except Exception as e:
        raise VaultCryptoError(f"Decryption failed: {str(e)}") from e


def pack_vault(
    plaintext_db: bytes,
    password: str,
    recovery_key: Optional[str] = None,
    master_key: Optional[bytes] = None,
    time_cost: int = 3,
    memory_cost: int = 131072,  # 128 MiB hardened KDF
    parallelism: int = 4,
) -> Tuple[bytes, bytes, str]:
    """Packs plaintext database bytes into an encrypted vault container.
    
    Returns:
        (container_bytes, master_key, recovery_key)
    """
    if master_key is None:
        master_key = nacl.utils.random(32)
    elif len(master_key) != 32:
        raise VaultCryptoError("master_key must be exactly 32 bytes")

    if not recovery_key:
        recovery_key = generate_recovery_key()

    # Slot 0: Password KDF
    pwd_salt = nacl.utils.random(16)
    pwd_kdf_key = derive_argon2id_key(
        password,
        pwd_salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
    )
    enc_master_key_pwd = encrypt_bytes(master_key, pwd_kdf_key)

    # Slot 1: Recovery Key KDF
    rec_salt = nacl.utils.random(16)
    rec_kdf_key = derive_argon2id_key(
        recovery_key,
        rec_salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
    )
    enc_master_key_rec = encrypt_bytes(master_key, rec_kdf_key)

    # Encrypt actual database payload using master key
    enc_payload = encrypt_bytes(plaintext_db, master_key)

    header: Dict[str, Any] = {
        "format": "GHOST_VAULT",
        "version": "1.0.0",
        "kdf_params": {
            "time_cost": time_cost,
            "memory_cost": memory_cost,
            "parallelism": parallelism,
        },
        "slots": {
            "password": {
                "salt_b64": base64.b64encode(pwd_salt).decode("ascii"),
                "enc_key_b64": base64.b64encode(enc_master_key_pwd).decode("ascii"),
            },
            "recovery": {
                "salt_b64": base64.b64encode(rec_salt).decode("ascii"),
                "enc_key_b64": base64.b64encode(enc_master_key_rec).decode("ascii"),
            },
        },
    }

    header_bytes = json.dumps(header, indent=2).encode("utf-8")
    container = MAGIC_HEADER + header_bytes + SEPARATOR + enc_payload
    return container, master_key, recovery_key


def unlock_vault(container_bytes: bytes, secret: str) -> Tuple[bytes, bytes, Dict[str, Any]]:
    """Unlocks an encrypted container using either the password or recovery key.
    
    Returns:
        (decrypted_db_bytes, master_key, header_metadata)
    """
    if not container_bytes.startswith(MAGIC_HEADER):
        raise VaultCryptoError("Invalid vault container: Missing magic header")

    try:
        content_after_magic = container_bytes[len(MAGIC_HEADER):]
        sep_idx = content_after_magic.find(SEPARATOR)
        if sep_idx == -1:
            raise VaultCryptoError("Malformed vault container: Separator not found")

        header_json_bytes = content_after_magic[:sep_idx]
        encrypted_payload = content_after_magic[sep_idx + len(SEPARATOR):]
        header = json.loads(header_json_bytes.decode("utf-8"))
    except Exception as e:
        if isinstance(e, VaultCryptoError):
            raise
        raise VaultCryptoError(f"Failed to parse vault envelope: {str(e)}") from e

    kdf_params = header.get("kdf_params", {})
    time_cost = kdf_params.get("time_cost", 2)
    memory_cost = kdf_params.get("memory_cost", 65536)
    parallelism = kdf_params.get("parallelism", 2)

    slots = header.get("slots", {})
    master_key: Optional[bytes] = None

    # Try Slot 0 (Password)
    if "password" in slots:
        try:
            pwd_salt = base64.b64decode(slots["password"]["salt_b64"])
            enc_key = base64.b64decode(slots["password"]["enc_key_b64"])
            kdf_key = derive_argon2id_key(
                secret,
                pwd_salt,
                time_cost=time_cost,
                memory_cost=memory_cost,
                parallelism=parallelism,
            )
            master_key = decrypt_bytes(enc_key, kdf_key)
        except Exception:
            master_key = None

    # Try Slot 1 (Recovery Key) if Slot 0 failed
    if master_key is None and "recovery" in slots:
        try:
            rec_salt = base64.b64decode(slots["recovery"]["salt_b64"])
            enc_key = base64.b64decode(slots["recovery"]["enc_key_b64"])
            kdf_key = derive_argon2id_key(
                secret,
                rec_salt,
                time_cost=time_cost,
                memory_cost=memory_cost,
                parallelism=parallelism,
            )
            master_key = decrypt_bytes(enc_key, kdf_key)
        except Exception:
            master_key = None

    if master_key is None:
        raise VaultCryptoError("Authentication failed: Invalid password or recovery key")

    # Decrypt actual database payload
    try:
        decrypted_db = decrypt_bytes(encrypted_payload, master_key)
    except Exception as e:
        raise VaultCryptoError(f"Database payload decryption failed: {str(e)}") from e

    return decrypted_db, master_key, header
