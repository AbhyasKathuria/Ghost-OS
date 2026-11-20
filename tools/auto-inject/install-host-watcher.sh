#!/usr/bin/env bash
# Ghost-OS Linux Zero-Click Udev Rule Installer
# Automatically executes Launch-GhostOS.sh the millisecond the USB is plugged in

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install-host-watcher.sh)"
    exit 1
fi

cat << 'EOF' > /etc/udev/rules.d/99-ghost-vault.rules
ACTION=="add", SUBSYSTEMS=="usb", ENV{ID_FS_LABEL}=="GhostVault", RUN+="/bin/sh -c 'sleep 2; /bin/sh /media/*/GhostVault/Launch-GhostOS.sh || /bin/sh /run/media/*/*/Launch-GhostOS.sh'"
EOF

udevadm control --reload-rules
udevadm trigger

echo "  ✓ Linux udev zero-click injection rule installed into /etc/udev/rules.d/99-ghost-vault.rules"
