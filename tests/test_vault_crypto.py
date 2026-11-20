"""Gate 1 Verification: Vault Cryptography, Persistence & History Tests.

Verifies:
1. Argon2id key derivation & authenticated encryption (XChaCha20-Poly1305 / SecretBox)
2. Tampering & corrupted envelope detection
3. Vault creation and unlocking with password
4. Vault unlocking with offline recovery key escrow
5. Invalid password rejection
6. Atomic write resilience and rolling backup rotation
7. Normalized scan ingestion, machine registry, history queries, and audit logging
"""

import json
import os
import shutil
import tempfile
import pytest

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
from ghost_vault.crypto import (
    VaultCryptoError,
    derive_argon2id_key,
    encrypt_bytes,
    decrypt_bytes,
    generate_recovery_key,
    pack_vault,
    unlock_vault,
)
from ghost_vault.db import GhostVaultDB


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="ghost_vault_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_scan_payload() -> NormalizedScanPayload:
    fingerprint = NormalizedScanPayload.generate_fingerprint(
        salt="test_vault_salt_123",
        motherboard_uuid="MB-UUID-998877",
        cpu_id="CPU-INTEL-13700H",
        primary_storage_serial="SAMSUNG-NVME-SN8821",
    )
    return NormalizedScanPayload(
        schema_version="1.0.0",
        scan_id="c0a80101-1111-2222-3333-444455556666",
        machine_fingerprint=fingerprint,
        platform=PlatformEnum.WINDOWS,
        os_version="Microsoft Windows 11 Pro 10.0.22631",
        timestamp_utc="2026-11-13T07:30:00Z",
        compatibility_matrix={
            "cpu": "supported",
            "ram": "supported",
            "gpu": "supported",
            "storage_smart": "supported",
            "battery": "supported",
            "thermals": "supported",
            "fans": "limited",
        },
        hardware=HardwareSpec(
            cpu=CpuSpec(
                model="13th Gen Intel Core i7-13700H",
                architecture="x86_64",
                physical_cores=14,
                logical_threads=20,
                base_clock_mhz=2400.0,
                max_clock_mhz=5000.0,
                temp_c=48.0,
            ),
            memory=MemorySpec(
                total_bytes=17179869184,
                slots_used=2,
                slots_total=2,
                modules=[
                    MemoryModule(
                        slot="ChannelA-DIMM0",
                        capacity_bytes=8589934592,
                        speed_mhz=4800,
                        type="DDR5",
                        manufacturer="Micron",
                    ),
                    MemoryModule(
                        slot="ChannelB-DIMM0",
                        capacity_bytes=8589934592,
                        speed_mhz=4800,
                        type="DDR5",
                        manufacturer="Micron",
                    ),
                ],
            ),
            storage=[
                StorageDevice(
                    device_id="\\\\.\\PhysicalDrive0",
                    model="SAMSUNG MZVL21T0HCLR-00B00",
                    serial_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    interface="NVMe",
                    capacity_bytes=1024209543168,
                    smart_status="PASSED",
                    temp_c=40.5,
                    wear_level_pct=2.0,
                    power_on_hours=1450,
                )
            ],
            gpu=[
                GpuSpec(
                    name="Intel Iris Xe Graphics",
                    vendor="Intel",
                    vram_bytes=1073741824,
                    driver_version="31.0.101.4575",
                    temp_c=44.0,
                )
            ],
            motherboard=MotherboardSpec(
                manufacturer="ASUSTeK COMPUTER INC.",
                product="UX3404VC",
                bios_version="UX3404VC.308",
                bios_date="2024-03-15",
                secure_boot_enabled=True,
            ),
            battery=BatterySpec(
                present=True,
                design_capacity_mwh=70000.0,
                full_charge_capacity_mwh=65800.0,
                health_pct=94.0,
                cycle_count=87,
                status="Discharging",
            ),
            network=[
                NetworkInterface(
                    interface="Wi-Fi 6E",
                    mac_hash="01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
                    type="Wireless",
                    link_speed_mbps=866,
                    status="Connected",
                )
            ],
        ),
        diagnostics=[
            DiagnosticResult(
                test_name="SMART Overall Health",
                status=DiagnosticStatus.PASS,
                metric_value=0.0,
                threshold=0.0,
                evidence="All NVMe health indicators within nominal range.",
                recommendation="None",
            )
        ],
    )


def test_argon2id_derivation_and_aead():
    """Verifies Argon2id key derivation determinism and authenticated encryption/decryption."""
    salt = os.urandom(16)
    password = "SuperSecretMasterPassword!2026"

    key1 = derive_argon2id_key(password, salt, time_cost=1, memory_cost=8192, parallelism=1)
    key2 = derive_argon2id_key(password, salt, time_cost=1, memory_cost=8192, parallelism=1)
    assert key1 == key2
    assert len(key1) == 32

    plaintext = b"Ghost-OS Offline Vault Payload"
    ciphertext = encrypt_bytes(plaintext, key1)
    assert ciphertext != plaintext

    decrypted = decrypt_bytes(ciphertext, key1)
    assert decrypted == plaintext


def test_tampering_triggers_crypto_error():
    """Verifies that altering even a single bit of ciphertext triggers authentication failure."""
    salt = os.urandom(16)
    key = derive_argon2id_key("CorrectPassword", salt, time_cost=1, memory_cost=8192, parallelism=1)
    plaintext = b"Critical Hardware Forensics Data"
    ciphertext = bytearray(encrypt_bytes(plaintext, key))

    # Tamper with the last byte
    ciphertext[-1] ^= 0x01

    with pytest.raises(VaultCryptoError):
        decrypt_bytes(bytes(ciphertext), key)


def test_vault_pack_and_unlock_with_recovery_key():
    """Tests dual-slot container unlocking via both password and recovery key."""
    password = "AdminVaultPassword_99!"
    recovery_key = generate_recovery_key()
    assert len(recovery_key.split("-")) == 8

    plaintext_db = b"SQLite format 3\x00MockDatabaseBytes12345"
    container, master_key, final_recovery_key = pack_vault(
        plaintext_db=plaintext_db,
        password=password,
        recovery_key=recovery_key,
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
    )

    # 1. Unlock via Password
    dec_db_1, mkey1, header1 = unlock_vault(container, password)
    assert dec_db_1 == plaintext_db
    assert mkey1 == master_key

    # 2. Unlock via Recovery Key
    dec_db_2, mkey2, header2 = unlock_vault(container, recovery_key)
    assert dec_db_2 == plaintext_db
    assert mkey2 == master_key

    # 3. Wrong password fails
    with pytest.raises(VaultCryptoError):
        unlock_vault(container, "WrongPasswordEntirely")


def test_vault_lifecycle_and_atomic_persistence(temp_dir, sample_scan_payload):
    """Tests GhostVaultDB initialization, in-memory hydration, atomic writes, and rolling backups."""
    vault_path = os.path.join(temp_dir, "GhostVault", "vault.enc")
    recovery_file = os.path.join(temp_dir, "GhostVault", "recovery_key.txt")
    password = "TestVaultPassword#2026"

    # 1. Create new vault
    vault = GhostVaultDB.create_new(
        vault_path=vault_path,
        password=password,
        recovery_file_path=recovery_file,
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
    )
    assert vault.is_open
    assert os.path.exists(vault_path)
    assert os.path.exists(recovery_file)

    # Verify recovery key file contents
    with open(recovery_file, "r", encoding="utf-8") as rf:
        rf_text = rf.read()
        assert "GHOST-OS VAULT EMERGENCY RECOVERY KEY" in rf_text

    # 2. Ingest scan into in-memory DB
    scan_id = vault.ingest_scan(
        payload=sample_scan_payload,
        overall_health_score=95,
        score_breakdown={
            "overall": 95,
            "cpu": 98,
            "ram": 100,
            "storage": 96,
            "battery": 94,
            "thermal": 92,
            "summary": "ASUS Zenbook 14 in excellent condition.",
        },
    )
    assert scan_id == sample_scan_payload.scan_id

    # Add a maintenance log
    vault.add_maintenance_record(
        machine_fingerprint=sample_scan_payload.machine_fingerprint,
        action_type="fan_cleaned",
        technician_name="Lead Engineer",
        notes="Cleaned cooling vents and verified exhaust thermals.",
    )

    # Update asset tag
    vault.update_machine_asset_tag(
        machine_fingerprint=sample_scan_payload.machine_fingerprint,
        asset_tag="ASUS-ZENBOOK-001",
        notes="Primary diagnostic testbed",
    )

    # Verify query on in-memory instance
    machine = vault.get_machine(sample_scan_payload.machine_fingerprint)
    assert machine is not None
    assert machine["asset_tag"] == "ASUS-ZENBOOK-001"
    assert machine["latest_health_score"] == 95

    # 3. Explicit flush & backup rotation
    vault.flush()
    bak1 = os.path.join(temp_dir, "GhostVault", "backups", "vault.bak.1")
    assert os.path.exists(bak1)

    # Close the vault
    vault.close()
    assert not vault.is_open

    # 4. Re-open vault from disk using password
    reopened = GhostVaultDB.open_vault(vault_path, password)
    assert reopened.is_open

    reopened_machine = reopened.get_machine(sample_scan_payload.machine_fingerprint)
    assert reopened_machine is not None
    assert reopened_machine["asset_tag"] == "ASUS-ZENBOOK-001"
    assert reopened_machine["notes"] == "Primary diagnostic testbed"

    # Query scans and history
    scans = reopened.get_machine_scans(sample_scan_payload.machine_fingerprint)
    assert len(scans) == 1
    assert scans[0]["scan_id"] == sample_scan_payload.scan_id
    assert scans[0]["overall_health_score"] == 95

    # Query latest scan full details
    latest = reopened.get_latest_scan(sample_scan_payload.machine_fingerprint)
    assert latest is not None
    assert latest["raw_payload"]["hardware"]["cpu"]["model"] == "13th Gen Intel Core i7-13700H"
    assert len(latest["diagnostics"]) == 1
    assert latest["diagnostics"][0]["test_name"] == "SMART Overall Health"

    # Query maintenance records
    maint_records = reopened.list_maintenance_records(sample_scan_payload.machine_fingerprint)
    assert len(maint_records) == 1
    assert maint_records[0]["action_type"] == "fan_cleaned"
    assert maint_records[0]["technician_name"] == "Lead Engineer"

    # Query audit logs
    audit_events = reopened.list_audit_events()
    assert len(audit_events) >= 3
    event_types = [e["event_type"] for e in audit_events]
    assert "scan_ingested" in event_types
    assert "vault_unlocked" in event_types

    reopened.close()


def test_unlock_with_recovery_key_from_escrow_file(temp_dir, sample_scan_payload):
    """Verifies that an escrowed recovery key file can unlock the database independently."""
    vault_path = os.path.join(temp_dir, "GhostVault", "vault.enc")
    recovery_file = os.path.join(temp_dir, "GhostVault", "recovery_key.txt")
    password = "OriginalPassword!999"

    vault = GhostVaultDB.create_new(
        vault_path=vault_path,
        password=password,
        recovery_file_path=recovery_file,
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
    )
    vault.ingest_scan(sample_scan_payload, overall_health_score=88)
    vault.close()

    # Read recovery key from file
    with open(recovery_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        key_line = [l for l in lines if l.startswith("Key: ")][0]
        escrowed_key = key_line.replace("Key: ", "").strip()

    # Unlock vault using only the escrowed recovery key
    reopened = GhostVaultDB.open_vault(vault_path, escrowed_key)
    assert reopened.is_open
    machine = reopened.get_machine(sample_scan_payload.machine_fingerprint)
    assert machine is not None
    assert machine["latest_health_score"] == 88
    reopened.close()


def test_ghost_recovery_escrow_verification_and_cold_storage(temp_dir):
    """Verifies GhostRecoveryEscrow verification, off-device export, and cold storage separation."""
    from ghost_vault.escrow import GhostRecoveryEscrow, ColdStorageSecurityWarning

    vault_path = os.path.join(temp_dir, "vault.enc")
    recovery_file = os.path.join(temp_dir, "rec.txt")
    v = GhostVaultDB.create_new(
        vault_path=vault_path,
        password="TestPassWord!123",
        recovery_file_path=recovery_file,
        time_cost=1,
        memory_cost=8192,
        parallelism=1,
    )
    rec_key = v.recovery_key
    v.close()

    # 1. Verify key
    assert GhostRecoveryEscrow.verify_key(vault_path=vault_path, recovery_key=rec_key) is True
    assert GhostRecoveryEscrow.verify_key(vault_path=vault_path, recovery_key="INVALID-KEY-123") is False

    # 2. Test cold-storage check (same drive check)
    same_dir = os.path.join(temp_dir, "sub_escrow")
    with pytest.raises(ColdStorageSecurityWarning):
        GhostRecoveryEscrow.export_escrow_certificate(
            recovery_key=rec_key,
            destination_dir=same_dir,
            vault_path=vault_path,
            force_same_drive=False,
        )

    # 3. Test forced or off-device export
    escrow_cert = GhostRecoveryEscrow.export_escrow_certificate(
        recovery_key=rec_key,
        destination_dir=same_dir,
        vault_path=vault_path,
        force_same_drive=True,
    )
    assert os.path.exists(escrow_cert)
    with open(escrow_cert, "r", encoding="utf-8") as f:
        cert_text = f.read()
    assert rec_key in cert_text
    assert "Cold-Storage Escrow" in cert_text

    # 4. Test on-device key purge
    assert os.path.exists(recovery_file)
    purged = GhostRecoveryEscrow.purge_on_device_recovery_key(temp_dir)
    # The file in temp_dir was named rec.txt, create recovery_key.txt to test purge
    rec_usb = os.path.join(temp_dir, "recovery_key.txt")
    with open(rec_usb, "w") as f:
        f.write("key-on-usb")
    assert GhostRecoveryEscrow.purge_on_device_recovery_key(temp_dir) is True
    assert not os.path.exists(rec_usb)
