#!/usr/bin/env bash
# Ghost-OS Portable Linux Launcher
# Run directly from USB on any x86_64 or aarch64 Linux distribution

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================================="
echo "             GHOST-OS PORTABLE LINUX LAUNCHER                     "
echo "    Zero-Install • Offline Hardware Intelligence • USB Vault      "
echo "=================================================================="

# Locate Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif [ -f "$DIR/python/bin/python3" ]; then
    PYTHON_CMD="$DIR/python/bin/python3"
else
    echo "Error: Python 3 runtime not found on Linux host."
    exit 1
fi

export PYTHONPATH="$DIR:$DIR/ghost_core:$DIR/ghost_vault:$DIR/ghost_ai:$DIR/linux-os"
export GHOST_VAULT_PATH="$DIR/GhostVault/vault.enc"

# Check if Ghost-Core is running
if ! curl -s -f http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    echo "[1/3] Starting Ghost-Core IPC Engine in background..."
    nohup $PYTHON_CMD -m uvicorn ghost_core.api.server:app --host 0.0.0.0 --port 8000 >/dev/null 2>&1 &
    sleep 1
fi

echo "[2/3] Extracting native Linux Hardware Telemetry..."
SCAN_JSON=$($PYTHON_CMD -c "
import json
from linux_os.scanner.scan import LinuxHardwareScanner
scanner = LinuxHardwareScanner()
payload = scanner.collect()
print(payload.model_dump_json())
")

echo "[3/3] Ingesting telemetry into Ghost Vault..."
curl -s -X POST http://127.0.0.1:8000/api/v1/scan/ingest \
    -H "Content-Type: application/json" \
    -d "$SCAN_JSON" >/dev/null 2>&1
echo "  ✓ Hardware scan ingested into encrypted vault."

# Open browser if desktop environment available
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    if command -v xdg-open &>/dev/null; then
        echo "Opening Admin Command Center: http://127.0.0.1:8000/"
        xdg-open "http://127.0.0.1:8000/" >/dev/null 2>&1 &
    fi
fi

echo "Ghost-OS execution complete."
