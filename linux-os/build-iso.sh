#!/usr/bin/env bash
# ==============================================================================
# GHOST-OS Minimal Bootable UEFI Live Image Builder
# Targets: Ubuntu 24.04 LTS (Noble) minimal + XFCE + Native Hardware Toolchains
# ==============================================================================

set -euo pipefail

DISTRO_CODENAME="noble"
ARCH="amd64"
OUTPUT_ISO="ghost-os-live-uefi.iso"
WORK_DIR="/tmp/ghost-os-build"
CHROOT_DIR="${WORK_DIR}/chroot"
IMAGE_DIR="${WORK_DIR}/image"

# ------------------------------------------------------------------------------
# Dependency Manifest Verification
# ------------------------------------------------------------------------------
REQUIRED_HOST_TOOLS=(
    "debootstrap"
    "xorriso"
    "mtools"
    "mksquashfs"
    "grub-mkstandalone"
)

echo ">>> [1/7] Verifying builder host toolchain..."
for tool in "${REQUIRED_HOST_TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: Required host utility '$tool' is not installed."
        echo "Install using: sudo apt-get update && sudo apt-get install -y debootstrap xorriso mtools squashfs-tools grub-efi-amd64-bin"
        exit 1
    fi
done

# Hardware diagnostic toolchain packages for Ghost-OS Live image
GHOST_DIAGNOSTIC_PACKAGES=(
    "linux-generic"
    "systemd-sysv"
    "network-manager"
    "net-tools"
    "ethtool"
    "pciutils"
    "usbutils"
    "dmidecode"
    "lshw"
    "smartmontools"
    "lm-sensors"
    "nvme-cli"
    "memtester"
    "stress-ng"
    "python3"
    "python3-venv"
    "python3-pip"
    "xfce4"
    "xfce4-terminal"
    "firefox"
    "sudo"
    "exfatprogs"
    "curl"
)

echo ">>> [2/7] Cleaning previous build trees..."
rm -rf "$WORK_DIR"
mkdir -p "$CHROOT_DIR" "$IMAGE_DIR"

# ------------------------------------------------------------------------------
# Stage 1: Debootstrap Minimal Base
# ------------------------------------------------------------------------------
echo ">>> [3/7] Debootstrapping minimal Ubuntu ${DISTRO_CODENAME} base..."
debootstrap --arch="$ARCH" --variant=minbase "$DISTRO_CODENAME" "$CHROOT_DIR" http://archive.ubuntu.com/ubuntu/

# Mount host binds
mount --bind /dev "$CHROOT_DIR/dev"
mount --bind /run "$CHROOT_DIR/run"
mount --bind /proc "$CHROOT_DIR/proc"
mount --bind /sys "$CHROOT_DIR/sys"

cleanup_mounts() {
    echo ">>> Unmounting virtual filesystems..."
    umount -lf "$CHROOT_DIR/dev" || true
    umount -lf "$CHROOT_DIR/run" || true
    umount -lf "$CHROOT_DIR/proc" || true
    umount -lf "$CHROOT_DIR/sys" || true
}
trap cleanup_mounts EXIT

# ------------------------------------------------------------------------------
# Stage 2: Install Kernel, Drivers, Diagnostics & Desktop in Chroot
# ------------------------------------------------------------------------------
echo ">>> [4/7] Installing diagnostics toolchain & minimal XFCE in chroot..."
cat << 'EOF' > "$CHROOT_DIR/tmp/chroot-setup.sh"
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Update apt repositories
cat << 'REPO_LIST' > /etc/apt/sources.list
deb http://archive.ubuntu.com/ubuntu/ noble main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu/ noble-security main restricted universe multiverse
REPO_LIST

apt-get update
apt-get install -y --no-install-recommends \
    linux-generic systemd-sysv network-manager net-tools ethtool \
    pciutils usbutils dmidecode lshw smartmontools lm-sensors \
    nvme-cli memtester stress-ng python3 python3-venv python3-pip \
    xfce4 xfce4-terminal firefox sudo exfatprogs curl dbus-x11

# Set Hostname
echo "ghost-os" > /etc/hostname

# Configure autologin user 'ghost'
useradd -m -s /bin/bash -G sudo,adm,dialout ghost
echo "ghost:ghost" | chpasswd
echo "ghost ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/ghost-nopasswd
chmod 0440 /etc/sudoers.d/ghost-nopasswd

# Clean apt cache
apt-get clean
rm -rf /var/lib/apt/lists/*
EOF

chmod +x "$CHROOT_DIR/tmp/chroot-setup.sh"
chroot "$CHROOT_DIR" /tmp/chroot-setup.sh
rm -f "$CHROOT_DIR/tmp/chroot-setup.sh"

# ------------------------------------------------------------------------------
# Stage 3: Ghost Vault Auto-Mount & Auto-Launch Service
# ------------------------------------------------------------------------------
echo ">>> [5/7] Configuring systemd Ghost Vault auto-mount and companion launcher..."
cat << 'EOF' > "$CHROOT_DIR/etc/systemd/system/ghost-vault.service"
[Unit]
Description=Mount Ghost Vault exFAT USB and Launch Core Engine
After=local-fs.target systemd-udevd.service
Wants=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/ghost-mount-vault.sh

[Install]
WantedBy=multi-user.target
EOF

cat << 'EOF' > "$CHROOT_DIR/usr/local/bin/ghost-mount-vault.sh"
#!/usr/bin/env bash
mkdir -p /mnt/ghostvault
VAULT_DEV=$(blkid -L "GhostVault" || true)

if [ -n "$VAULT_DEV" ]; then
    mount -t exfat -o umask=0000 "$VAULT_DEV" /mnt/ghostvault || true
    echo "Ghost Vault partition mounted at /mnt/ghostvault"
fi
EOF
chmod +x "$CHROOT_DIR/usr/local/bin/ghost-mount-vault.sh"
chroot "$CHROOT_DIR" systemctl enable ghost-vault.service

# ------------------------------------------------------------------------------
# Stage 4: Package SquashFS Filesystem
# ------------------------------------------------------------------------------
echo ">>> [6/7] Compressing rootfs into SquashFS container..."
mkdir -p "$IMAGE_DIR/live"
mksquashfs "$CHROOT_DIR" "$IMAGE_DIR/live/filesystem.squashfs" \
    -comp xz -e boot

# Copy Kernel and Initramfs
VMLINUZ=$(ls -1t "$CHROOT_DIR/boot/vmlinuz-"* | head -n 1)
INITRD=$(ls -1t "$CHROOT_DIR/boot/initrd.img-"* | head -n 1)
cp "$VMLINUZ" "$IMAGE_DIR/live/vmlinuz"
cp "$INITRD" "$IMAGE_DIR/live/initrd"

# ------------------------------------------------------------------------------
# Stage 5: Configure Pure UEFI GRUB Bootloader & Assemble ISO
# ------------------------------------------------------------------------------
echo ">>> [7/7] Assembling bootable UEFI Live ISO image..."
mkdir -p "$IMAGE_DIR/boot/grub/x86_64-efi" "$IMAGE_DIR/EFI/BOOT"

cat << 'EOF' > "$IMAGE_DIR/boot/grub/grub.cfg"
set default=0
set timeout=5

menuentry "Ghost-OS Diagnostic Live Environment (UEFI)" {
    linux /live/vmlinuz boot=live quiet splash
    initrd /live/initrd
}

menuentry "Ghost-OS Live (Safe Mode / VESA Graphics)" {
    linux /live/vmlinuz boot=live nomodeset
    initrd /live/initrd
}
EOF

# Build standalone EFI executable
grub-mkstandalone \
    --format=x86_64-efi \
    --output="$IMAGE_DIR/EFI/BOOT/BOOTX64.EFI" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$IMAGE_DIR/boot/grub/grub.cfg"

# Create minimal FAT EFI boot image
dd if=/dev/zero of="$IMAGE_DIR/boot/grub/efiboot.img" bs=1M count=20
mkfs.vfat "$IMAGE_DIR/boot/grub/efiboot.img"
mmd -i "$IMAGE_DIR/boot/grub/efiboot.img" ::/EFI ::/EFI/BOOT
mcopy -i "$IMAGE_DIR/boot/grub/efiboot.img" "$IMAGE_DIR/EFI/BOOT/BOOTX64.EFI" ::/EFI/BOOT/

# Build final ISO via xorriso
xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "GHOST_OS" \
    -eltorito-alt-boot \
    -e boot/grub/efiboot.img \
    -no-emul-boot \
    -isohybrid-gpt-basdat \
    -output "$OUTPUT_ISO" \
    "$IMAGE_DIR"

echo "=================================================================="
echo " Ghost-OS Live UEFI ISO successfully generated: $OUTPUT_ISO"
echo " Flash to USB Partition 2 (GHOST_SYS) using dd or Rufus"
echo "=================================================================="
