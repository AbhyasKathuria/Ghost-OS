#!/usr/bin/env bash
# Ghost-OS Portable macOS Launcher
# Double-click in Finder to launch on any Intel or Apple Silicon (M1-M4) Mac

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================================="
echo "             GHOST-OS PORTABLE MACOS LAUNCHER                     "
echo "    Zero-Install • Offline Hardware Intelligence • USB Vault      "
echo "=================================================================="

# Locate Python 3
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif [ -f "$DIR/python/bin/python3" ]; then
    PYTHON_CMD="$DIR/python/bin/python3"
else
    echo "Error: Python 3 runtime not found on host Mac."
    echo "Please ensure Python 3 is installed."
    read -p "Press [Enter] to exit..."
    exit 1
fi

export PYTHONPATH="$DIR:$DIR/ghost_core:$DIR/ghost_vault:$DIR/ghost_ai:$DIR/macos-companion"
export GHOST_VAULT_PATH="$DIR/GhostVault/vault.enc"

$PYTHON_CMD "$DIR/macos-companion/ghost_scanner_mac.py" "$@"
