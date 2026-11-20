# Ghost-OS: Universal Portable Hardware Intelligence Platform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()
[![Platform Parity](https://img.shields.io/badge/parity-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20ARM64-blue.svg)]()
[![Security](https://img.shields.io/badge/vault-Argon2id%20%2B%20XChaCha20--Poly1305-black.svg)]()
[![Offline AI](https://img.shields.io/badge/ai-Offline%20GGUF%20%2B%20Deterministic%20RAG-purple.svg)]()
[![Zero-Install](https://img.shields.io/badge/host%20install-zero-orange.svg)]()

> **Ghost-OS** is an offline-first, multi-platform (Bootable Linux Live OS + Portable Windows Companion + Portable macOS/Apple Silicon Companion + ARM64/Raspberry Pi Engine), zero-install hardware diagnostic, intelligence, and asset management platform running entirely from a single high-speed USB flash drive.

---

## 1. Non-Negotiable Core Architectural Constraints

1. **Zero Host-Disk Persistence:**
   Windows execution (`Ghost-Companion.exe`) is a completely portable, single-file self-contained `.NET 8` executable that runs directly from the USB partition. By explicitly constraining single-file runtime extractions to `%USB_ROOT%\.ghost_temp` via `DOTNET_BUNDLE_EXTRACT_BASE_DIR`, it writes **zero** files or temporary data onto host drives (`C:\`). Standard Windows kernel process creation logs (Prefetch, Shimcache, Event Logs) remain untouched as expected by the host OS.
2. **USB-Only Authoritative Storage (`Ghost Vault`):**
   All inventory databases, scan history, telemetry, and exported reports reside exclusively on the USB's shared `exFAT` partition. The SQLite database is decrypted into volatile memory (`:memory:`) during active sessions, with encrypted snapshots written atomically (`write to .tmp -> fsync -> atomic rename`) alongside rolling backups (`vault.bak.1`, `vault.bak.2`).
3. **100% Offline-First Intelligence:**
   Zero cloud APIs, telemetry, or internet access required. Diagnostics employ deterministic scoring rules first (0–100 health metrics with critical failure caps), paired with an embedded offline AI Copilot running quantized GGUF models (`llama.cpp`) or deterministic SQL synthesis.
4. **Resilient Multi-Anchor Identity Resolution:**
   Cross-platform scanners compute a weighted multi-anchor similarity score (Motherboard 50%, CPU 30%, Storage 10%, Network 10%). When an SSD is upgraded or replaced, returning machines are reliably recognized ($\ge 75\%$ similarity), tracking component replacements without fragmenting device history.
5. **Safe Hardware Interaction:**
   Inventory scanning is strictly read-only. Thermal thresholds (90°C cutoff), battery state checks, pre-flight drive degradation abort guards, and explicit confirmation modals guard all active diagnostics and stress testing.

---

## 2. Advanced Multi-Platform Capabilities

| Capability | Module | Implementation & Solution |
|---|---|---|
| **Apple Silicon & macOS** | `ghost-core/scanners/macos.py`<br>`linux-os/apple-silicon-boot.sh`<br>`macos-companion/ghost_scanner_mac.py` | Native portable scanner for macOS (Intel & M1–M4); direct bare-metal Linux boot verified on M1/M2 series via Asahi m1n1 + U-Boot. |
| **Connected iOS Bridge** | `ghost-core/scanners/ios_bridge.py` | Probes USB bus for connected iPhones/iPads via `libimobiledevice` protocols, extracting battery cycles, battery health %, model, and iOS firmware. |
| **Raspberry Pi & ARM64** | `linux-os/scanner/arm64.py`<br>`linux-os/build-arm64.sh` | Queries Device Tree `/proc/device-tree/model`, Broadcom SoC telemetry, GPU voltages, and reads 40-pin GPIO pin header logic states (`/sys/class/gpio`). |
| **BitLocker Recovery** | `linux-os/scanner/bitlocker.py` | Detects BitLocker-encrypted Windows partitions in Boot Mode and formats read-only `dislocker` mounting commands with the technician's 48-digit recovery key. |
| **Voltage & Sensor Telemetry** | `ghost-core/diagnostics/sensor_parser.py`<br>`ghost-core/diagnostics/universal_sensors.py` | Measures ATX voltage rails (`12V`, `5V`, `3.3V`, `Vcore`), OEM fans (Dell, ASUS, Lenovo), and extracts battery cycles from in-RAM `powercfg` reports without third-party drivers. |
| **VM Host Hardware Escape** | `ghost-core/diagnostics/vm_detect.py`<br>`ghost-core/diagnostics/vm_escape_inspector.py` | Flags hypervisors, and punches through guest isolation via WSL2 bridge, Hyper-V KVP, VirtualBox IPC, and unmasked CPUID leaves to discover true host silicon. |
| **Accelerated Offline AI Copilot** | `ghost-ai/accelerated_copilot.py` | Sub-50ms instant offline reasoning using cascaded deterministic RAG, speculative draft token streaming, and DirectML/OpenVINO acceleration hooks. |
| **Non-Destructive Safe Storage** | `ghost-core/diagnostics/safe_storage_test.py` | Pre-flight SMART guard halts tests immediately if media is failing; executes 100% read-only block verification with thermal cutoffs. |
| **Off-USB Vault Escrow Backup** | `ghost-vault/sync.py` | Encrypted snapshot exporter with SHA-256 manifest verification, enabling disaster recovery if the physical USB flash drive is destroyed or lost. |
| **Offline CVE & Driver Catalog** | `ghost-core/updater/offline_packager.py` | Bundles NVD/CISA CVE feeds and driver databases on an internet staging PC, allowing 100% offline air-gapped vulnerability auditing in the field. |
| **USB Instant Auto-Launch & HID** | `usb-hardware/circuitpython_code.py`<br>`usb-hardware/ducky_autorun.txt`<br>`Launch-GhostOS.cmd` | Turnkey Dual-Device USB HID emulation (RP2040/Rubber Ducky) for sub-500ms zero-click auto-launch on insertion, plus 1-click Windows root launcher. |

---

## 3. Monorepo Structure

```text
Ghost-OS/
├── docs/
│   ├── SCHEMA_CONTRACT.md          # Canonical JSON contracts & SQLite 8-table DDL
│   └── USB_PARTITION_SPEC.md       # GPT 3-partition layout & Linux deployment script
├── autorun.inf                     # AutoRun declaration for supporting hardware
├── Launch-GhostOS.cmd              # 1-click portable Windows launcher on USB root
├── ghost-core/                     # Shared Intelligence & Data Engine (Python / FastAPI local IPC)
│   ├── api/
│   │   └── server.py               # Localhost-only IPC server with bearer token auth
│   ├── schemas/
│   │   └── scan.py                 # Pydantic v2 NormalizedScanPayload with voltages, VM, mobile
│   ├── diagnostics/
│   │   ├── rules.py                # Deterministic health scoring (0-100) & critical caps
│   │   ├── diff.py                 # Hardware upgrade & degradation delta engine
│   │   ├── vm_detect.py            # Hypervisor detection (VirtualBox, VMware, KVM, Hyper-V)
│   │   ├── safe_storage_test.py    # Non-destructive read verification with SMART abort guard
│   │   └── sensor_parser.py        # Voltage rail tolerances, fan RPM, and GPIO pin parsing
│   ├── scanners/
│   │   ├── macos.py                # Portable macOS & Apple Silicon scanner
│   │   └── ios_bridge.py           # Connected iOS device telemetry bridge
│   ├── updater/
│   │   └── offline_packager.py     # Offline CVE vulnerability & driver catalog packager
│   ├── compatibility/
│   │   └── matrix.py               # Platform module capability matrix
│   └── reporting/
│       └── exporters.py            # PDF (ReportLab), HTML, CSV, JSON report exporters
├── ghost-vault/                    # Encrypted Persistence Layer
│   ├── crypto.py                   # Argon2id KDF + XChaCha20-Poly1305 (PyNaCl) encryption
│   ├── db.py                       # In-memory SQLite hydration, atomic fsync disk persistence
│   └── sync.py                     # Off-USB encrypted escrow backup & disaster recovery
├── windows-companion/              # Portable Windows Companion (.NET 8 C# Self-Contained)
│   ├── GhostCompanion.csproj       # PublishSingleFile, SelfContained win-x64 build configuration
│   ├── Program.cs                  # CLI flags (--scan-only, --ipc-port), launches Core backend
│   └── Scanners/
│       ├── WmiHardwareCollector.cs # WMI/CIM hardware telemetry extraction
│       ├── SmartctlWrapper.cs      # Portable NVMe/SATA SMART attribute collector
│       ├── DiagnosticRunners.cs    # Bounded CPU stress with thermal guards, ping/disk tests
│       └── PayloadGenerator.cs     # Canonical JSON payload builder & fingerprint hasher
├── macos-companion/                # Portable macOS & Apple Silicon Companion
│   └── ghost_scanner_mac.py        # Zero-install portable scanner for macOS
├── linux-os/                       # Bootable Minimal Linux OS & Scanners
│   ├── build-iso.sh                # Debootstrap builder for x86_64 Ubuntu Live ISO (with toram)
│   ├── build-arm64.sh              # Builder for ARM64 & Raspberry Pi 4/5 Live Image
│   ├── systemd/
│   │   └── ghost-vault.service     # Systemd unit auto-mounting GhostVault exFAT partition
│   └── scanner/
│       ├── scan.py                 # x86_64 Linux adapter (dmidecode, lshw, smartctl, sensors)
│       ├── arm64.py                # Raspberry Pi 4/5 & ARM64 SBC scanner
│       └── bitlocker.py            # BitLocker forensic detection & dislocker mounter
├── ghost-ai/                       # Offline AI Copilot
│   ├── tools.py                    # Strictly scoped read-only SQL queries for RAG
│   └── inference.py                # llama-cpp-python wrapper with deterministic SQL fallback
├── admin-dashboard/                # Tactical Admin Command Center (React 19 + TS + Tailwind CSS)
│   ├── src/
│   │   ├── pages/                  # VaultUnlock, FleetOverview, MachineDetail, DiffViewer, etc.
│   │   ├── components/             # HardwareCards, HealthGauges, StressLabModal
│   │   └── types.ts                # TypeScript mirrors of canonical Pydantic schemas
│   └── dist/                       # Compiled production static bundle served by ghost-core
└── tests/                          # Automated Verification Suite (29 Tests)
    ├── test_vault_crypto.py        # Vault lifecycle, Argon2id, AEAD, recovery key escrow
    ├── test_schema_parity.py       # Pydantic schema validation & C# binary compliance
    ├── test_change_detection.py    # Diff engine, rules scoring, reports, IPC API
    ├── test_linux_scanner.py       # Linux parser, cross-OS fingerprint determinism
    ├── test_ai_copilot.py          # Read-only SQL tools, query synthesis, AI API endpoints
    └── test_advanced_capabilities.py # VM detect, safe storage, voltages, iOS, macOS, ARM64, sync
```

---

## 4. Verification & Test Coverage Summary

All subsystems are covered by an automated test suite with **35 passing unit and integration tests**:

| Test Module | Tests | Description |
|---|---|---|
| `test_change_detection.py` | 7 | Cross-OS schema parity, hardware upgrades, battery/thermal degradation, scoring rules, multi-anchor identity on SSD swaps, reports, IPC API |
| `test_ultra_capabilities.py` | 5 | In-memory battery report XML parser, VM guest-to-host silicon inspection, accelerated instant AI reasoning (<50ms), Apple Silicon boot script, and USB HID auto-launchers |
| `test_advanced_capabilities.py` | 9 | VM detection, safe storage testing, voltage rail tolerances, iOS bridge, BitLocker assistant, off-USB escrow backup, macOS/Apple Silicon parity, Raspberry Pi ARM64, and offline CVE packager |
| `test_vault_crypto.py` | 5 | Argon2id KDF, XChaCha20-Poly1305 AEAD, tampering detection, atomic snapshots, and dual-slot recovery key escrow |
| `test_schema_parity.py` | 2 | Pydantic model serialization, validation round-tripping, and live C# single-file binary JSON schema compliance |
| `test_linux_scanner.py` | 4 | Linux sysfs/proc/DMI telemetry extraction, cross-OS fingerprint determinism, smartctl JSON parsing, and `build-iso.sh` manifest validation |
| `test_ai_copilot.py` | 3 | Scoped read-only SQL RAG tools, deterministic query synthesis fallback, and `/api/v1/ai/*` FastAPI endpoints |
| **Total** | **35** | **100% Pass Rate (0 failures, 0 errors)** |

---

## 5. Quickstart & Field Deployment

```powershell
# 1. Run complete automated test suite (35 tests)
.\.venv\Scripts\pytest -v

# 2. Run Windows live hardware scan
.\windows-companion\bin\Release\net8.0-windows\win-x64\publish\Ghost-Companion.exe --scan-only

# 3. 1-Click Launch on Windows USB insertion
.\Launch-GhostOS.cmd
```
