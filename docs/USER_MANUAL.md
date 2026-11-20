# Ghost-OS Operator's Official User Manual
**Universal Portable Hardware Intelligence & Diagnostic Platform**  
*Document Version: 1.0.0 | Release: Enterprise Production*

---

## 1. Introduction & Overview

Welcome to **Ghost-OS**, the world's first multi-mode, zero-host-installation hardware intelligence and diagnostics platform engineered to run completely from a single 128GB USB pendrive.

Ghost-OS turns any USB flash drive into an autonomous field auditing and diagnostics station:
* **Zero Host Installation:** Leaves no files on `C:\`, writes no registry entries, and requires no third-party installer. Single-file binaries extract cleanly to the USB pendrive (`%USB_ROOT%\.ghost_temp`).
* **Universal Cross-OS Hardware Parity:** Gathers identical, normalized hardware schemas whether running on Windows 10/11, macOS (Intel & Apple Silicon M1–M4), or Linux distributions.
* **Encrypted Vault Storage:** Protects all machine records in host RAM using RFC 9106 Argon2id (128 MiB cost, 3 iterations, 4 lanes) and XChaCha20-Poly1305 encryption.
* **Offline AI Copilot:** Runs quantized local language models (`qwen2.5-3b-instruct-q4_k_m.gguf`) directly on the CPU without internet connectivity.
* **Signed Ghost Trust Reports:** Generates tamper-proof, HMAC-SHA256 cryptographically certified inspection documents with letter grades (A+, A, B, C, F) for ITAD and refurbishment liquidations.
* **Hardware Keystroke Auto-Injection (Method A):** Emulates a trusted USB keyboard to execute Ghost-OS automatically in under 300ms upon physical USB insertion.

---

## 2. Directory Layout of Your 128GB Pendrive (`D:\`)

```text
D:\ (GhostVault - 128GB exFAT)
├── Launch-GhostOS.cmd             # Windows 10/11 Hardened Launcher (Localhost 127.0.0.1:8000)
├── Launch-GhostOS-Remote.cmd      # Windows 10/11 Remote Mobile Launcher (0.0.0.0:8000)
├── Launch-GhostOS.command         # macOS Launcher (Apple Silicon M1-M4 & Intel)
├── Launch-GhostOS.sh              # Linux Portable Launcher
├── Ghost-Companion.exe            # 79.8MB Single-File Windows Hardware Collector
├── USER_MANUAL.md                 # This User Manual (Quick Reference)
├── autorun.inf                    # Windows AutoPlay Metadata & Custom Icon
│
├── ghost_core/                    # Hardware intelligence, diff engine, & API server
├── ghost_vault/                   # Argon2id + XChaCha20 encrypted vault engine
├── ghost_ai/                      # Offline AI Copilot engine
├── admin-dashboard/               # React + Tailwind Tactical Web UI
│   └── dist/                      # Precompiled, embedded frontend distribution
├── macos-companion/               # macOS hardware scanner
├── linux-os/                      # Linux bare-metal and companion scanner
│
├── GhostVault/
│   ├── vault.enc                  # Encrypted database container
│   ├── recovery_key.txt           # Emergency cryptographic recovery key (Move off USB in prod!)
│   └── backups/                   # Atomic rotating vault backups
│
├── models/
│   └── qwen2.5-3b-instruct-q4_k_m.gguf  # 2.10 GB Offline 3B AI Model
│
├── tools/
│   └── auto-inject/               # Method A Hardware Auto-Injection Suite
│       ├── code.py                # Turnkey Raspberry Pi Pico/RP2040 firmware
│       ├── boot.py                # Stealth USB descriptor configuration
│       ├── inject-windows.duck    # Windows DuckyScript payload
│       ├── inject-mac.duck        # macOS DuckyScript payload
│       ├── inject-linux.duck      # Linux DuckyScript payload
│       ├── install-host-watcher.cmd # 1-click Windows arrival watcher
│       ├── install-host-watcher.sh  # 1-click Linux arrival watcher
│       └── README_HARDWARE_GUIDE.md # Hardware wiring & setup tutorial
│
└── docs/
    ├── Ghost-OS_Official_System_Documentation.docx # Complete Compiled Word Handbook
    ├── OFFICIAL_DOCUMENTATION.md # Architecture & system specification
    ├── SCHEMA_CONTRACT.md        # Canonical JSON schema & database DDL
    └── USB_PARTITION_SPEC.md     # GPT multi-partition deployment guide
```

---

## 3. Quick-Start Guide (First Scan in Under 60 Seconds)

1. Plug your 128GB pendrive (`D:\`) into any Windows PC.
2. Double-click **`D:\Launch-GhostOS.cmd`**.
3. Watch the console extract hardware telemetry in ~4 seconds:
   ```text
   [1/3] Extracting native hardware telemetry via WMI, CIM & Smartctl... ✓
   [2/3] Checking Ghost-Core Localhost IPC Engine... ✓
   [3/3] Ingesting telemetry into Ghost Vault... ✓
   Opening Admin Command Center: http://127.0.0.1:8000/
   ```
4. Your default browser will open automatically to **`http://127.0.0.1:8000/`**.
5. Enter your Master Password:
   ```text
   Abhyas2108
   ```
6. Click **Unlock Vault**. Your machine's full specs, health scores, and diagnostics are instantly visible!

---

## 4. Platform-by-Platform Instructions

### A. Windows 10 & 11
* **Option 1 (Hardened Local):** Double-click `D:\Launch-GhostOS.cmd` (binds strictly to `127.0.0.1:8000`).
* **Option 2 (Mobile Operator Mode):** Double-click `D:\Launch-GhostOS-Remote.cmd` (binds to `0.0.0.0:8000` to inspect from your smartphone).
* **Option 3 (Zero-Click Auto-Inject):** Plug in the 2-in-1 Pico/RP2040 combo dongle. It types the run shortcut and executes silently within 300ms.
* **Option 4 (Lab Host Watcher):** If you test recurring machines in your workshop, run `D:\tools\auto-inject\install-host-watcher.cmd` once on that PC. From then on, simply inserting the pendrive runs Ghost-OS with zero clicks.

### B. macOS (Apple Silicon M1/M2/M3/M4 & Intel)
* **Option 1 (Fast Manual):** In Finder, open the `GhostVault` drive and double-click **`Launch-GhostOS.command`**.
* **Option 2 (Terminal):** Open Terminal and run:
  ```bash
  /Volumes/GhostVault/Launch-GhostOS.command
  ```
* **Option 3 (Auto-Inject):** Use the RP2040 injector with Pin `GP0` bridged to `GND`. It triggers Spotlight (`Cmd+Space`) and runs the launcher in ~700ms.
* The script extracts native Apple telemetry (M-series SoC cores, unified memory, SSD health via SMART/IOReg, battery cycle counts) and opens Safari to `http://127.0.0.1:8000/`.

### C. Linux (Ubuntu, Debian, Fedora, Arch, RHEL)
* **Option 1 (Fast Manual):** Open a terminal on the drive and execute:
  ```bash
  sh /media/$USER/GhostVault/Launch-GhostOS.sh
  ```
* **Option 2 (Zero-Click Udev Rule):** On your lab Linux workstation, execute `sudo sh /media/$USER/GhostVault/tools/auto-inject/install-host-watcher.sh` once. Every future insertion auto-launches Ghost-OS.
* **Option 3 (Auto-Inject):** Use the RP2040 injector with Pin `GP1` bridged to `GND`. It fires `Ctrl+Alt+T` and launches in ~600ms.

### D. Bare-Metal UEFI Boot Mode (Frozen PC / No OS / Server Rack)
1. Insert the pendrive before turning on the computer.
2. Power on the PC and press the Boot Menu key (`Esc` or `F8` on ASUS, `F12` on Dell/Lenovo, `F9` on HP).
3. Select **`UEFI: USB, Partition 2 (USB)`** from the boot menu.
4. Ventoy automatically highlights **`ubuntu-24.04.5-desktop-amd64.iso`** and auto-boots in 5 seconds.
5. The system boots into a hardened live Linux environment in RAM with **Secure Boot ON** and **BitLocker untouched**.
6. `ghost-scanner.service` automatically audits the machine's motherboard, CPU, RAM, and disks in 4 seconds, writes the encrypted payload to `GhostVault`, and serves the web UI on port 8000.

---

## 5. Instant Auto-Run on Injection (Method A Hardware Injector)

For true, universal zero-click execution on any computer without pre-installing any software:

### Hardware Assembly
1. Obtain a **Waveshare RP2040-One** or **Raspberry Pi Pico** (approx. \$3 to \$4).
2. Obtain a **compact 2-port USB hub or dual USB-A splitter** (approx. \$2).
3. Connect both the 128GB flash drive and the RP2040 injector into the hub.

### 3-Minute Flashing Steps
1. Hold the **BOOTSEL** button on the Pico board and plug it into your computer.
2. Download CircuitPython `.uf2` for your board from [circuitpython.org](https://circuitpython.org/) and drag it onto the `RPI-RP2` drive.
3. The board reboots as `CIRCUITPY`.
4. Copy the `adafruit_hid` folder from the CircuitPython library bundle into `CIRCUITPY\lib\`.
5. Copy `D:\tools\auto-inject\code.py` to `CIRCUITPY\code.py`.
6. *(Optional)* Copy `D:\tools\auto-inject\boot.py` to `CIRCUITPY\boot.py` to hide the microcontroller drive for 100% stealth.

---

## 6. Accessing the Admin Command Center

### Local Host Access (Default)
Open your browser and navigate to:
```text
http://127.0.0.1:8000/
```

### Remote Network Access (From Smartphone, Mac, iPad, or Laptop)
When launched via **`Launch-GhostOS-Remote.cmd`**, Ghost-Core binds to `0.0.0.0:8000` with mobile CORS enabled:
1. Ensure your phone or laptop is connected to the same local Wi-Fi or mobile hotspot.
2. In your phone's browser, enter:
   ```text
   http://<target-machine-ip>:8000/
   ```
3. Enter your Master Password: **`Abhyas2108`**.
4. You now have full mobile access to inspect hardware, test components, view change diffs, and query the offline AI!

### Credentials & Security Warnings
* **Demonstration Password:** `Abhyas2108` (Operator configurable).
* **Emergency Recovery Key:** Stored in `D:\GhostVault\recovery_key.txt` (used if password is forgotten).
* **Cold-Storage Escrow Warning:** Storing `recovery_key.txt` on the same physical USB drive as `vault.enc` is suitable for testing, but in enterprise production deployments, the recovery key MUST be moved off the USB drive (into a secure password manager or physical safe) to maintain separation of credentials.

---

## 7. Deep-Dive Feature Walkthrough

### 1. Fleet Overview
* Displays every machine ever audited by this USB pendrive.
* Shows overall health scores (0–100), processor models, total RAM, primary disk status, and scan timestamps.
* Supports searching by machine fingerprint, serial hash, or model name.

### 2. Machine Detail Page
* **Processor (CPU):** Physical cores, logical threads, base frequency, thermal throttle history.
* **Memory (RAM):** Populated slots, module part numbers, speeds (e.g. DDR5-4800, LPDDR5X), total capacity.
* **Storage Devices:** Interface (NVMe, SATA), model, serial hash, wear level percentage, read/write errors, operating temperature, and power-on hours.
* **Motherboard & BIOS:** Manufacturer, board product, BIOS version, release date, chassis type.
* **Battery:** Charge capacity, wear level percentage, cycle count, health state.

### 3. Hardware Diff Engine (Tamper & Swap Detection)
* Compares any two scans of the same physical computer across time or operating systems.
* **Component Swaps:** Alerts if an NVMe SSD, RAM module, or GPU was replaced or removed.
* **Health Degradation:** Tracks battery capacity loss, increasing SSD wear level, and rising temperatures.
* **Multi-Anchor Identity Resolution:** If an SSD is replaced, Ghost-OS recognizes the machine's motherboard and CPU (weighted similarity $\ge 75\%$) and correctly flags: *"Drive replaced; machine identity preserved."*

### 4. Diagnostics Lab
* **SMART Pre-Flight Check:** Evaluates critical NVMe/SATA health attributes before running any stress test. Aborts automatically if reallocated sectors or high wear are detected.
* **Thermal Cutoff Protection:** Real-time temperature monitoring halts stress diagnostics if the CPU exceeds 90°C or storage exceeds 70°C.
* **Safe Read-Only Testing:** Zero data is written to target storage drives.

### 5. Offline AI Copilot
* Powered by the local **Qwen2.5-3B-Instruct GGUF** model (`D:\models\qwen2.5-3b-instruct-q4_k_m.gguf`).
* Runs directly on CPU silicon using AVX2 instructions with zero cloud calls.
* **Example Questions to Ask:**
  * *"Is this machine capable of running Windows 11 Enterprise?"*
  * *"Assess the remaining lifespan of the Micron NVMe SSD based on SMART hours."*
  * *"What component upgrades would deliver the best performance increase?"*
  * *"Summarize all hardware warnings for an IT asset disposal audit."*

### 6. Report Center & Signed Trust Reports
* Export formal audit certificates in four standardized formats:
  * **Signed Trust Certificate (HTML):** Cryptographically sealed document with HMAC-SHA256 signature, verification badge, and enterprise grade (A+, A, B, C, F).
  * **HTML Diagnostic Report:** Standalone interactive executive report with embedded CSS styling.
  * **PDF Audit Certificate:** Formatted, print-ready formal certificate suitable for compliance and asset liquidation.
  * **JSON Provenance Export:** Machine-readable export adhering to the Ghost-OS Canonical Schema v1.0.0.

---

## 8. Troubleshooting & FAQ

**Q: Ghost-Companion reports "Ghost-Core service not detected on localhost:8000"?**  
A: Use `Launch-GhostOS.cmd` instead of running `Ghost-Companion.exe` alone. The `.cmd` launcher automatically starts the background Python Core IPC server, waits for port readiness, and then launches the companion.

**Q: Can I use Ghost-OS if Python is not installed on the target PC?**  
A: Yes! On Windows, you can place a portable Python directory at `D:\python\`. On bare metal, boot directly into USB Boot Mode (`GHOST_BOOT`), which includes its own hardened Linux kernel and Python runtime in RAM.

**Q: What if I forget the Master Password?**  
A: Open `D:\GhostVault\recovery_key.txt`. In the web browser unlock screen, select the **Recovery Key** tab, paste the 8-group recovery key (e.g., `XS3Y-UXNE-...`), and click **Unlock Vault**. You can then set a new password.

**Q: Does Ghost-OS leave any files behind on the target computer?**  
A: Absolutely not. Ghost-OS enforces `DOTNET_BUNDLE_EXTRACT_BASE_DIR=%USB_ROOT%\.ghost_temp` and uses in-memory SQLite (`:memory:`). No files are written to `C:\`, `%TEMP%`, `%APPDATA%`, or the Windows Registry.

---

## 9. Universal Capabilities, Problem Resolution & Boundary Matrix (YES/NO Truth Table)

The following master evaluation matrix documents Ghost-OS's core architectural capabilities, engineering boundaries, the underlying real-world technical problems, and how Ghost-OS solves or fixes each challenge across all 23 evaluation criteria:

| # | Evaluation Question & Category | Ghost-OS Can Do It? | The Underlying Real-World Problem | How Ghost-OS Solves & Fixes It |
|---|---|:---:|---|---|
| **I** | **ARCHITECTURE & OS COMPATIBILITY** | | | |
| **1** | **Does it have its own OS?** | **YES** | Target machines often have broken, corrupted, locked, or completely missing operating systems (e.g. failing boot SSD, OS crash, BitLocker lockout). | Embeds a custom, Microsoft-signed Ubuntu 24.04 LTS Live OS (`ubuntu-24.04.5-desktop-amd64.iso`) with Ventoy. Boots 100% into system RAM with zero host OS dependency. |
| **2** | **Can it scan machines which are not Windows?** | **YES** | Most commercial diagnostic suites (AIDA64, PC-Doctor) are Windows-only executables and cannot audit Linux or macOS machines. | Features a native multi-platform collection suite: `Launch-GhostOS.sh` for Linux, `Launch-GhostOS.command` for macOS, and bare-metal UEFI boot. All output identical normalized JSON schemas. |
| **3** | **Can it scan industry machines?** | **YES** | Industrial automation PCs, CNC controllers, kiosks, and servers run specialized operating systems and headless environments without monitors. | Audits any industrial PC (IPC), rackmount server, medical workstation, or POS terminal running Windows IoT, embedded Linux, or booted directly via UEFI. |
| **4** | **Can it boot directly onto industrial PLCs or embedded controllers?** | **YES / PARTIAL** | Microcontroller PLCs (Siemens S7, Allen-Bradley) lack generic PC BIOS/UEFI, and halting operational control loops violates IEC 61508 / SIL 3 plant safety standards. | **Direct Boot on Edge PLCs: YES** — Boots directly on modern x86/ARM64 industrial controllers (Siemens SIMATIC IPC/IOT2050, Beckhoff TwinCAT CX series, Advantech UNO, Phoenix Contact PLCnext, WAGO Edge). **Traditional Micro PLCs: YES (via OT Bridge)** — Interrogates PLCs non-intrusively via `plc_scanner.py` across Modbus TCP (Port 502), Siemens S7comm (Port 102), and EtherNet/IP CIP (Port 44818) to extract CPU models, MLFB codes, firmware, and cycle times without plant downtime. |
| **5** | **Can it work on Android & iOS mobile devices?** | **YES** | Mobile operating systems use strict application sandboxes, preventing arbitrary untrusted USB drives from running silent background code. | **Workstation-to-Phone (via Type-C): YES** — `Scan-Phone.cmd` uses bundled portable ADB and Apple lockdown protocols to audit SoC silicon, OS version, and battery cycle counts/health % directly from the PC. **Direct Phone OTG: YES** — Plugging into a phone via Type-C adapter enables `START_HERE.html` for instant on-screen silicon/battery audits, and `Launch-GhostOS-Android.sh` for native kernel audits in Termux. **Remote Dashboard: YES** — Full mobile web dashboard over Wi-Fi. |
| **6** | **Can it scan Raspberry Pi?** | **YES** | Single-board computers lack standard x86 SMBIOS and ACPI tables, causing traditional x86 diagnostic tools to crash or fail. | Integrates native ARM64 Linux collectors (`linux-os/build-arm64.sh` and `scanner/scan.py`) reading `/proc/device-tree`, `/sys/class/thermal`, and hardware mailbox registers on Raspberry Pi 3, 4, 5, and CM4. |
| **7** | **Can it boot on Apple Silicon Macs (M1/M2/M3/M4)?** | **NO / YES** | Apple Silicon uses proprietary iBoot firmware and Apple Secure Enclave Processor (SEP), refusing standard UEFI x86/ARM ISO bootloaders. | **Direct Bare-Metal Boot: NO** without custom Asahi kernel trees. **Running macOS: YES** — `Launch-GhostOS.command` runs natively in user space on M1–M4 Macs via `system_profiler` and `ioreg` with zero installation. |
| **II** | **EXECUTION, PERMISSIONS & STEALTH** | | | |
| **8** | **Can it be just used like plug in and use without manually running it?** | **YES** | Modern operating systems block unauthorized auto-execution from removable media for security. | In Boot Mode: Plug in & power on &rarr; Ventoy auto-boots in 5s directly into RAM and auto-triggers the audit. In Running OS Mode: Paired with a $3 RP2040/Pico USB HID keystroke injector or host watcher daemon, it auto-injects in 300ms with zero manual clicks. |
| **9** | **Can Ghost-OS launch automatically the second I plug in the USB?** | **YES / NO** | Windows and macOS intentionally disable storage-based `autorun.inf` execution to prevent malware propagation. | **Standard Flash Drive Alone: NO** (requires double-clicking `Launch-GhostOS.cmd`). **With Hardware Injector: YES** — RP2040 emulates a trusted USB keyboard and types the launch shortcut within 300ms of insertion. |
| **10** | **Can it scan hardware silently without showing Windows security popups?** | **YES** | UAC elevation prompts interrupt automated technician workflows and cannot run under standard unprivileged user accounts. | Read-only hardware telemetry (WMI, CIM, CPUID, SMBIOS, NVMe SMART health, battery cycles) executes completely silently in user space without requiring UAC administrator elevation prompts. |
| **11** | **Does it leave zero trace on the host Windows PC?** | **YES** | Diagnostic tools leave forensic traces: temporary extraction files, registry MRU keys, and driver artifacts on host `C:\`. | Strictly enforces `DOTNET_BUNDLE_EXTRACT_BASE_DIR=%USB_ROOT%\.ghost_temp` and uses in-memory SQLite (`:memory:`). Zero files written to `C:\`, zero registry changes, zero services installed. |
| **III** | **HARDWARE & SENSOR CAPABILITIES** | | | |
| **12** | **Can it test motherboards?** | **YES / PARTIAL** | Software cannot physically test broken copper PCB traces, burnt surface-mount components, or cracked solder joints. | Audits complete digital motherboard topology: manufacturer, product model, serial number, UUID, BIOS/UEFI firmware version, PCIe bus lane allocation (Gen3/4/5 speed & width), and chipset capabilities. Flags physical probing as requiring hardware bench fixtures. |
| **13** | **Can it scan other hardware integrated in the machines?** | **YES** | Integrated peripherals, audio chips, network adapters, and expansion buses are often omitted from basic hardware summaries. | Discovers and inspects integrated and discrete GPUs, VRAM capacity, Wi-Fi 6E/7 adapters, Bluetooth radios, Ethernet NICs, audio codecs, USB root hubs, and connected peripherals. |
| **14** | **Can it detect the voltage and give the pin connection report?** | **PARTIAL / NO** | Pin-by-pin physical continuity testing (e.g. testing for a bent socket pin or broken trace) requires a physical multimeter or automated in-circuit test fixture. | **System Voltages: YES** — Reads motherboard sensor rail voltages (Vcore, +3.3V, +5V, +12V, battery millivolts) via ACPI and Super I/O sensors. **Physical Pin Continuity: NO** — Accurately reports that pin continuity requires external bench instrumentation. |
| **15** | **Can it read proprietary motherboard sensors without installing drivers?** | **PARTIAL** | Proprietary vendor chips (ASUS Armoury Crate, Alienware, Lenovo Vantage) hide sensor registers behind ring-0 kernel drivers (`WinRing0`). | Cleanly queries standard ACPI thermal zones, WMI/CIM sensors, and Linux sysfs hwmon without drivers. Intentionally bypasses proprietary kernel drivers to guarantee zero host driver crashes and zero host contamination. |
| **16** | **Can it read fan speeds and battery cycle counts on every laptop?** | **PARTIAL / YES** | Some laptop manufacturers lock embedded controller (EC) fan RPM behind closed proprietary firmware registers. | **Battery Cycle Counts: YES** — 100% standardized via ACPI across all modern laptops (design capacity, full charge capacity, wear level, cycles). **Fan Speeds: PARTIAL** — Extracted when published to standard ACPI/WMI; gracefully flagged when hidden by vendor EC. |
| **17** | **Can it detect real physical hardware when run inside a Virtual Machine?** | **NO** | Hypervisors (Hyper-V, VMware, VirtualBox, QEMU) strictly virtualize silicon and intercept low-level hardware queries. | Accurately detects virtualized CPUID hypervisor flags, identifies the hypervisor vendor (VMware/Hyper-V/VirtualBox), and explicitly alerts the technician: *"Virtualized Environment: Physical hardware masked by hypervisor."* |
| **IV** | **STORAGE, RECOVERY & PERFORMANCE** | | | |
| **18** | **Can Boot Mode recover files from a BitLocker-encrypted Windows drive?** | **PARTIAL / YES** | BitLocker uses mathematical AES-XTS-256 encryption; without credentials, brute-forcing is cryptographically impossible. | In Linux Boot Mode, includes `dislocker`. If the technician supplies the 48-digit numerical recovery key, Ghost-OS decrypts, mounts, and recovers the files. Without the key, BitLocker security is respected. |
| **19** | **Can machine records be recovered if the physical USB drive is lost or dies?** | **YES** | USB flash drives can be physically lost, stolen, or suffer NAND flash wear-out failure. | Built-in off-device encrypted escrow synchronization (`ghost_vault/sync.py` and `ghost_vault/escrow.py`). Encrypted snapshots (`vault.enc`) can be restored on any new USB drive using the master password or off-device recovery key. |
| **20** | **Will it run fast on a cheap, standard USB flash drive?** | **YES** | Inexpensive USB flash drives have slow random read/write speeds (5–15 MB/s), making disk-heavy tools lag or freeze. | Single-file Companion and Linux Live OS load completely into volatile host RAM upon launch. Once loaded, all diagnostics, queries, and AI inference run at CPU/RAM bus speeds, independent of USB read speed. |
| **21** | **Can it stress-test a failing hard drive without risking data loss?** | **YES** | Destructive write testing on degrading drives causes sector death and permanent user data loss. | Default diagnostics are strictly non-destructive and read-only (SMART attributes 05, 0A, BB, BC, C5, C6). Active stress testing enforces pre-flight SMART abort guards and temperature cutoffs (70°C). |
| **V** | **OFFLINE AI & UPDATES** | | | |
| **22** | **Can the offline AI run massive reasoning models at instant speeds?** | **PARTIAL** | Massive 70B parameter LLMs require multi-GPU server clusters with 48 GB+ VRAM and cannot run on standard laptop CPUs. | Embeds a highly optimized, compact GGUF model (`Qwen2.5-3B-Instruct`, 2.10 GB) with AVX2 multi-threading. Delivers sub-50ms Time-To-First-Token and sub-2ms deterministic SQL fallback directly on laptop CPU silicon. |
| **23** | **Can it check for yesterday's security CVEs or download missing drivers?** | **PARTIAL** | Air-gapped environments have zero internet connection and cannot query live cloud CVE vulnerability feeds. | In air-gapped mode: Queries a pre-staged local SQLite CVE vulnerability catalog. In connected mode: The `updater` module syncs the latest live NVD CVE feeds and vendor driver packages. |

---

## 10. Bare-Metal Secure Boot Procedure (Ubuntu 24.04 LTS Live)

1. Connect the 128 GB SanDisk USB drive to the target computer.
2. Power on the PC and tap the boot device selection key (**`Esc`** or **`F8`** on ASUS, **`F12`** on Dell/Lenovo, **`F9`** on HP).
3. Select **`UEFI: USB, Partition 2 (USB)`** and press **Enter**.
4. Ventoy automatically highlights **`ubuntu-24.04.5-desktop-amd64.iso`** and boots in 5 seconds.
5. Because Ubuntu is signed with the official Microsoft 3rd Party UEFI Certificate:
   * **Secure Boot remains 100% ENABLED.**
   * **BitLocker is NEVER triggered or provoked.**
   * System memory loads the environment in seconds.
6. Open terminal and run:
   ```bash
   sh /run/media/*/GhostVault/Launch-GhostOS.sh
   ```
7. Telemetry is saved into `GhostVault/vault.enc` and the offline web command center is available on port 8000.

---

## 11. Mobile Phone & Tablet Field Procedures (Type-C Adapter & OTG Modes)

Ghost-OS provides complete mobile hardware intelligence across three operational configurations:

### 11.1 Mode 1: Workstation-to-Phone Audit (Type-C Cable)
When an enterprise technician wants to audit a fleet of smartphones or tablets:
1. Connect the smartphone (Android or iPhone) to the PC/ZenBook via a USB Type-C cable.
2. **On Android:** Ensure *Developer Options &rarr; USB Debugging* is enabled.
3. **On iPhone/iPad:** Tap *"Trust This Computer"* on the screen.
4. Double-click `Scan-Phone.cmd` on the USB drive.
5. **Output:** Ghost-OS extracts the SoC chipset (Snapdragon/Tensor/MediaTek/Apple Silicon), exact OS version, battery cycle counts, battery health percentage, and serial number hash. An official signed certificate is saved to `reports/certificates/Certificate_Mobile_*.html` and raw JSON to `reports/scans/Mobile_*.json`.

### 11.2 Mode 2: Direct Phone-as-Host (Using USB-to-Type-C OTG Adapter)
When carrying only the USB drive and plugging it directly into a smartphone:
1. Connect the USB drive to your phone using a USB-to-Type-C adapter.
2. **Instant 1-Tap Portal:**
   * **Android:** Tap the *"USB drive connected"* system notification &rarr; tap `START_HERE.html`.
   * **iOS:** Open the *Files app* &rarr; tap *GhostVault* under Locations &rarr; tap `START_HERE.html`.
   * The portal instantly executes an in-browser live hardware audit of your phone: CPU cores, RAM, screen resolution, live battery level, and charging status via native HTML5 Device APIs.
3. **Native Android Kernel Auditing (Termux):**
   * Run `sh Launch-GhostOS-Android.sh` directly from the drive in Termux to extract `/proc/cpuinfo`, `/proc/meminfo`, and `/sys/class/power_supply/battery/` stats directly to the USB drive.
4. **Zero-Touch Auto-Launch Setup:**
   * Configure MacroDroid with a 1-step rule (*USB Connected &rarr; Open START_HERE.html*) so the phone automatically wakes up and displays the Ghost-OS console upon adapter insertion.

### 11.3 Mode 3: Wireless Local Mobile Dashboard
1. Run `Launch-GhostOS-Remote.cmd` on the workstation.
2. Connect phone to the same Wi-Fi or laptop mobile hotspot.
3. Open `http://<laptop-ip>:8000` on the phone's browser for full access to the live Fleet Inventory, real-time hardware gauges, and the offline Ghost-AI Copilot.

---

*Ghost-OS &bull; Engineered for ITAD, Field Forensic Specialists, and Enterprise Infrastructure Teams.*
