# Ghost-OS Canonical Schema & Database Contract

## Overview
Ghost-OS is a dual-mode, zero-install hardware intelligence and diagnostic platform running directly from a USB stick.
To guarantee cross-OS parity, both Windows Companion Mode and Bootable Linux Mode emit identical normalized JSON payloads conforming to `ghost-core/schemas/scan.py`.

---

## 1. Canonical Scan Payload Schema (JSON Contract v1.0.0)

```json
{
  "schema_version": "1.0.0",
  "scan_id": "4b6b669e-56e1-45ce-8c50-b8c7b80a2211",
  "machine_fingerprint": "a5d89f78b8796dc23985ec280b1548e3cf3406f9d2d0f865f1ef1e8310f8fa55",
  "platform": "Windows",
  "os_version": "Microsoft Windows 11 Pro 10.0.22631",
  "timestamp_utc": "2026-11-13T07:24:00Z",
  "compatibility_matrix": {
    "cpu": "supported",
    "ram": "supported",
    "gpu": "supported",
    "storage_smart": "supported",
    "battery": "supported",
    "thermals": "supported",
    "fans": "limited"
  },
  "hardware": {
    "cpu": {
      "model": "13th Gen Intel(R) Core(TM) i7-13700H",
      "architecture": "x86_64",
      "physical_cores": 14,
      "logical_threads": 20,
      "base_clock_mhz": 2400.0,
      "max_clock_mhz": 5000.0,
      "temp_c": 48.5
    },
    "memory": {
      "total_bytes": 17179869184,
      "slots_used": 2,
      "slots_total": 2,
      "modules": [
        {
          "slot": "ChannelA-DIMM0",
          "capacity_bytes": 8589934592,
          "speed_mhz": 4800,
          "type": "DDR5",
          "manufacturer": "Micron"
        },
        {
          "slot": "ChannelB-DIMM0",
          "capacity_bytes": 8589934592,
          "speed_mhz": 4800,
          "type": "DDR5",
          "manufacturer": "Micron"
        }
      ]
    },
    "storage": [
      {
        "device_id": "\\\\.\\PhysicalDrive0",
        "model": "SAMSUNG MZVL21T0HCLR-00B00",
        "serial_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "interface": "NVMe",
        "capacity_bytes": 1024209543168,
        "smart_status": "PASSED",
        "temp_c": 41.0,
        "wear_level_pct": 2.0,
        "power_on_hours": 1420
      }
    ],
    "gpu": [
      {
        "name": "Intel(R) Iris(R) Xe Graphics",
        "vendor": "Intel",
        "vram_bytes": 1073741824,
        "driver_version": "31.0.101.4575",
        "temp_c": 45.0
      }
    ],
    "motherboard": {
      "manufacturer": "ASUSTeK COMPUTER INC.",
      "product": "UX3404VC",
      "bios_version": "UX3404VC.308",
      "bios_date": "2024-03-15",
      "secure_boot_enabled": true
    },
    "battery": {
      "present": true,
      "design_capacity_mwh": 70000,
      "full_charge_capacity_mwh": 65800,
      "health_pct": 94.0,
      "cycle_count": 87,
      "status": "Discharging"
    },
    "network": [
      {
        "interface": "Wi-Fi",
        "mac_hash": "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b",
        "type": "Wireless",
        "link_speed_mbps": 866,
        "status": "Connected"
      }
    ]
  },
  "diagnostics": [
    {
      "test_name": "SMART Overall Health",
      "status": "PASS",
      "metric_value": 0.0,
      "threshold": 0.0,
      "evidence": "All critical NVMe attributes within vendor tolerances.",
      "recommendation": "None"
    }
  ]
}
```

---

## 2. Multi-Anchor Machine Identity & Component Swap Resolution

To resolve the component replacement dilemma (e.g., when a primary SSD is upgraded or replaced), Ghost-OS employs a weighted multi-anchor similarity algorithm rather than relying solely on a fragile single hash:

$$\text{Similarity Score} = w_{\text{mb}} \cdot S_{\text{mb}} + w_{\text{cpu}} \cdot S_{\text{cpu}} + w_{\text{disk}} \cdot S_{\text{disk}} + w_{\text{net}} \cdot S_{\text{net}}$$

| Hardware Anchor | Weight | Criteria | Description |
|---|:---:|---|---|
| **Motherboard Signature** | **50%** | Vendor & Product String match | Baseboard chassis identity (resilient against storage/RAM swaps) |
| **CPU Silicon & Topology** | **30%** | Model string & Physical core count | Processor identity |
| **Primary Storage Serial** | **10%** | Cryptographic hash match | Primary boot media |
| **Network Interface MACs** | **10%** | Intersection of hashed MACs | Physical network controllers |

* **Score $\ge 75\%$:** Evaluated as `SAME_DEVICE_COMPONENT_SWAP`. The scan is associated with the machine's historical identity in the Ghost Vault, and the `HardwareDiffEngine` automatically alerts the technician to the replaced SSD or swapped RAM.
* **Score $= 100\%$:** Evaluated as `EXACT_MATCH`.
* **Score $< 75\%$:** Evaluated as `DIFFERENT_MACHINE`.

---

## 3. Vault Relational Schema (SQLite DDL)

The Ghost Vault SQLite schema stores historic machine baselines, component inventories, diagnostic telemetry, and audit events.

```sql
-- Machines registry
CREATE TABLE IF NOT EXISTS machines (
    machine_fingerprint TEXT PRIMARY KEY,
    first_seen_utc TEXT NOT NULL,
    last_seen_utc TEXT NOT NULL,
    asset_tag TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Machine Identifiers & Anchors
CREATE TABLE IF NOT EXISTS machine_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_fingerprint TEXT NOT NULL,
    anchor_type TEXT NOT NULL, -- 'motherboard_uuid', 'cpu_id', 'storage_serial_hash'
    anchor_value TEXT NOT NULL,
    FOREIGN KEY(machine_fingerprint) REFERENCES machines(machine_fingerprint) ON DELETE CASCADE
);

-- Scan Sessions
CREATE TABLE IF NOT EXISTS scan_sessions (
    scan_id TEXT PRIMARY KEY,
    machine_fingerprint TEXT NOT NULL,
    platform TEXT NOT NULL, -- 'Windows' | 'Linux'
    os_version TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    overall_health_score INTEGER NOT NULL,
    raw_payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(machine_fingerprint) REFERENCES machines(machine_fingerprint) ON DELETE CASCADE
);

-- Hardware Components Normalized Snapshots
CREATE TABLE IF NOT EXISTS hardware_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    category TEXT NOT NULL, -- 'cpu', 'memory', 'storage', 'gpu', 'motherboard', 'battery', 'network'
    component_index INTEGER NOT NULL DEFAULT 0,
    details_json TEXT NOT NULL,
    FOREIGN KEY(scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
);

-- Diagnostic Results
CREATE TABLE IF NOT EXISTS diagnostic_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    test_name TEXT NOT NULL,
    status TEXT NOT NULL, -- 'PASS' | 'WARN' | 'FAIL'
    metric_value REAL,
    threshold REAL,
    evidence TEXT,
    recommendation TEXT,
    FOREIGN KEY(scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
);

-- Health Scores
CREATE TABLE IF NOT EXISTS health_scores (
    scan_id TEXT PRIMARY KEY,
    overall_score INTEGER NOT NULL, -- 0 to 100
    cpu_score INTEGER NOT NULL,
    ram_score INTEGER NOT NULL,
    storage_score INTEGER NOT NULL,
    battery_score INTEGER NOT NULL,
    thermal_score INTEGER NOT NULL,
    summary TEXT,
    FOREIGN KEY(scan_id) REFERENCES scan_sessions(scan_id) ON DELETE CASCADE
);

-- Maintenance & Service Records
CREATE TABLE IF NOT EXISTS maintenance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_fingerprint TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    technician_name TEXT,
    action_type TEXT NOT NULL, -- 'thermal_paste_replaced', 'fan_cleaned', 'battery_replaced', 'ram_upgraded', etc.
    notes TEXT,
    FOREIGN KEY(machine_fingerprint) REFERENCES machines(machine_fingerprint) ON DELETE CASCADE
);

-- Audit Events
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL, -- 'vault_unlocked', 'vault_flushed', 'scan_ingested', 'report_exported'
    timestamp_utc TEXT NOT NULL,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_scan_sessions_fingerprint ON scan_sessions(machine_fingerprint);
CREATE INDEX IF NOT EXISTS idx_diagnostic_results_scan ON diagnostic_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_hardware_components_scan ON hardware_components(scan_id);
```
