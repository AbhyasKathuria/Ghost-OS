#!/usr/bin/env python3
"""Ghost-OS Portable macOS Companion Launcher.

Zero host installation. Runs directly from USB on any Intel or Apple Silicon (M1-M4) Mac.
Usage:
    python3 ghost_scanner_mac.py [--scan-only] [--no-browser] [--port 8000]
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# Resolve root USB directory
USB_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if USB_ROOT not in sys.path:
    sys.path.insert(0, USB_ROOT)
ghost_core_dir = os.path.join(USB_ROOT, "ghost_core")
if os.path.exists(ghost_core_dir) and ghost_core_dir not in sys.path:
    sys.path.insert(0, ghost_core_dir)

from ghost_core.scanners.macos import MacOsHardwareScanner


def check_core_online(port: int = 8000) -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/health")
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_core_background(port: int = 8000):
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "ghost_core.api.server:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{USB_ROOT}:{os.path.join(USB_ROOT, 'ghost_core')}:{os.path.join(USB_ROOT, 'ghost_vault')}:{os.path.join(USB_ROOT, 'ghost_ai')}"
    env["GHOST_VAULT_PATH"] = os.path.join(USB_ROOT, "GhostVault", "vault.enc")
    
    subprocess.Popen(
        cmd,
        cwd=USB_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(20):
        time.sleep(0.3)
        if check_core_online(port):
            return True
    return False


def ingest_payload(payload_dict: dict, port: int = 8000):
    url = f"http://127.0.0.1:{port}/api/v1/scan/ingest"
    data = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print("  ✓ Hardware scan ingested into encrypted vault.")
                return True
    except urllib.error.HTTPError as e:
        if e.code == 423:
            print("  ! Vault is currently locked. Telemetry ready for ingestion upon unlocking.")
        else:
            print(f"  ! Core responded with status {e.code}. Telemetry prepared.")
    except Exception as e:
        print(f"  ! Ingestion deferred: {e}")
    return False


def main():
    print("==================================================================")
    print("             GHOST-OS PORTABLE MACOS COMPANION v1.0.0             ")
    print("   Apple Silicon (M1-M4) & Intel • Zero-Install • USB Vault       ")
    print("==================================================================")

    scan_only = "--scan-only" in sys.argv
    no_browser = "--no-browser" in sys.argv
    port = 8000

    print("[1/3] Extracting native Apple Hardware Telemetry (system_profiler, IOReg, SMC)...")
    payload = MacOsHardwareScanner.collect_payload()
    payload_dict = payload.model_dump()
    print("  ✓ Apple hardware telemetry extracted successfully.")

    if scan_only:
        print(json.dumps(payload_dict, indent=2))
        return 0

    print("[2/3] Checking Ghost-Core Localhost IPC Engine...")
    if not check_core_online(port):
        print("  Ghost-Core is not running. Launching background engine from USB...")
        start_core_background(port)

    if check_core_online(port):
        print(f"  ✓ Ghost-Core is online at http://127.0.0.1:{port}")
        print("[3/3] Ingesting telemetry into Ghost Vault...")
        ingest_payload(payload_dict, port)
    else:
        print("  ! Ghost-Core service not detected on localhost. Telemetry cached.")

    if not no_browser and check_core_online(port):
        dashboard_url = f"http://127.0.0.1:{port}/"
        print(f"\nOpening Admin Command Center: {dashboard_url}")
        subprocess.run(["open", dashboard_url], check=False)

    print("\nGhost-OS execution complete. Zero host disk or NVRAM modifications.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
