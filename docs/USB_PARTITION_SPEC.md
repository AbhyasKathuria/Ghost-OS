# Ghost-OS USB Partition Specification & Layout

## Overview
Ghost-OS is packaged onto a single high-speed USB flash drive (or external NVMe enclosure) providing multi-mode utility:
1. **Windows Companion Execution:** When plugged into a running Windows machine, the user runs `Ghost-Companion.exe` straight from the shared exFAT volume without installation.
2. **Direct UEFI Boot:** Boots a minimal, customized Linux OS with instant hardware diagnostic tools.
3. **Ghost Vault:** Shared, application-level encrypted file container storing the SQLite database, scan history, AI models, and exported PDF reports.

---

## 1. Partition Scheme (GPT - GUID Partition Table)

> [!IMPORTANT]
> **Windows Mount Order Architecture:** On removable media (USB flash drives with the Removable Media Bit set), Windows Explorer historically mounts only the first partition. Placing the shared exFAT `GhostVault` volume on **Partition 1** guarantees automatic drive letter assignment across all Windows versions. Concurrently, UEFI firmware specification (Section 13.3.3) mandates that firmware search all partition table entries for the ESP GUID (`c12a7328-f81f-11d2-ba4b-00a0c93ec93b`), allowing **Partition 2** to serve as the bootable EFI partition without conflict.

| Partition # | Label | File System | Size | Purpose | Flags / GUID |
|---|---|---|---|---|---|
| **1** | `GhostVault` | exFAT | Remaining Space (~28GB - 2TB) | Shared Windows/Linux accessible storage (Mounts 1st in Windows) | Microsoft basic data (`ebd0a0a2-b9e5-4433-87c0-68b6b72699c7`) |
| **2** | `GHOST_BOOT` | FAT32 | 512 MB | UEFI ESP boot partition (GRUB2, kernel, initramfs, Asahi m1n1) | `boot`, `esp` (`c12a7328-f81f-11d2-ba4b-00a0c93ec93b`) |
| **3** | `GHOST_SYS` | ext4 (SquashFS container) | ~4.0 GB | Bootable Linux Live OS system image (read-only rootfs) | Linux filesystem (`0fc63daf-8483-4772-8e79-3d69d8477de4`) |

---

## 2. Directory Layout on the Shared `GhostVault` (exFAT) Partition

```text
/Volumes/GhostVault/  (or E:\ on Windows, /mnt/ghostvault on Linux)
├── Ghost-Companion.exe          # Single-file self-contained Windows runner (.NET 8 + embedded Core)
├── Launch-GhostOS.cmd           # 1-click launcher setting DOTNET_BUNDLE_EXTRACT_BASE_DIR to USB
├── autorun.inf                  # AutoRun declaration for supporting hardware
├── Ghost-Linux-Launcher.sh      # Portable runner for Linux desktop live sessions
├── GhostVault/                  # Encrypted Persistence Store
│   ├── vault.enc                # Encrypted SQLite database container (Argon2id 128 MiB + XChaCha20-Poly1305)
│   ├── recovery_key.txt         # Emergency recovery key (store off-USB in enterprise deployments)
│   └── backups/
│       ├── vault.bak.1
│       └── vault.bak.2
├── models/                      # Quantized GGUF models (for offline AI Copilot)
│   └── qwen2.5-3b-instruct-q4_k_m.gguf
├── reports/                     # Exported PDF, HTML, and CSV diagnostic reports
│   └── 2026-11/
└── tools/
    ├── win64/                   # Standalone win-x64 tools (portable smartctl.exe)
    └── linux64/                 # Linux standalone CLI helpers
```

---

## 3. Automated Partitioning Script (Linux reference)

```bash
#!/usr/bin/env bash
set -euo pipefail

TARGET_DEV="${1:-}"
if [ -z "$TARGET_DEV" ] || [ ! -b "$TARGET_DEV" ]; then
    echo "Usage: sudo ./format-usb.sh /dev/sdX"
    exit 1
fi

echo "WARNING: All data on $TARGET_DEV will be destroyed!"
read -p "Type YES to proceed: " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    exit 1
fi

# Wipe partition table
wipefs -a "$TARGET_DEV"
sgdisk --zap-all "$TARGET_DEV"

# Create partitions:
# 1: exFAT Vault (0700) - First partition for Windows Removable Drive compatibility
# 2: 512MB EFI (EF00) - UEFI ESP boot partition
# 3: 4GB Linux Live System (8300) - ext4 partition holding live/filesystem.squashfs
sgdisk -n 2:2048:+512M -t 2:ef00 -c 2:"GHOST_BOOT" "$TARGET_DEV"
sgdisk -n 3:0:+4G      -t 3:8300 -c 3:"GHOST_SYS"  "$TARGET_DEV"
sgdisk -n 1:0:0        -t 1:0700 -c 1:"GhostVault" "$TARGET_DEV"

# Format filesystems
mkfs.exfat -n "GhostVault" "${TARGET_DEV}1"
mkfs.vfat -F 32 -n "GHOST_BOOT" "${TARGET_DEV}2"
mkfs.ext4 -L "GHOST_SYS" "${TARGET_DEV}3"

echo "Ghost-OS USB drive successfully initialized with Windows-compatible partition layout!"
```
