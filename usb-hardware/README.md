# Ghost-OS Instant Hardware Auto-Launch Guide

Modern versions of Microsoft Windows disable standard software `AutoRun.inf` on USB mass storage devices by design (since Windows 7) to prevent unauthorized code execution.

To achieve **100% true physical zero-click auto-launch the exact second you plug in the USB**, Ghost-OS supports **Dual-Device HID Emulation**:

---

## Supported Hardware Solutions

### 1. Raspberry Pi Pico / RP2040 Dual USB ($4 Solution)
1. Flash **CircuitPython 9.x+** onto a Raspberry Pi Pico or RP2040-Zero USB dongle.
2. Copy `adafruit_hid` into the `lib/` directory of the Pico.
3. Copy `usb-hardware/circuitpython_code.py` as `code.py` on the Pico.
4. Plug in the Pico along with your USB flash drive: Windows enumerates the keyboard, types the background launcher command in 400 milliseconds, and launches `Ghost-Companion.exe` instantly.

### 2. USB Rubber Ducky / Hak5 / Flipper Zero
1. Copy `usb-hardware/ducky_autorun.txt` to your Rubber Ducky or Flipper Zero BadUSB storage.
2. Plug into the target Windows workstation for instant execution.
