# Ghost-OS Method A: Hardware Auto-Run & Keystroke Injection Guide

This guide walks you through setting up a **$3-$4 hardware auto-injector** that triggers Ghost-OS **automatically in under 300 milliseconds** the exact second it is plugged into any Windows, macOS, or Linux computer.

---

## 1. Why Method A is the Industry Standard

Modern operating systems intentionally block USB flash drives from automatically executing software via `autorun.inf` to prevent virus infections. However, **every operating system unconditionally trusts USB keyboards (HID) without security prompts**.

By pairing your 128GB Ghost-OS flash drive with a tiny microcontroller (like the **Raspberry Pi Pico** or **RP2040-Zero**):
* The device presents as a trusted USB keyboard.
* In ~300ms after plugging in, it sends the OS run shortcut (`Win+R` on Windows, `Cmd+Space` on Mac, `Ctrl+Alt+T` on Linux).
* It locates the drive labeled `GhostVault` and launches `Launch-GhostOS.cmd` with zero clicks.
* The web command center opens on `http://127.0.0.1:8000/` ready for your password `Abhyas2108`.

---

## 2. Recommended Hardware (Choose One)

| Hardware Device | Form Factor | Approx. Cost | Why It's Great |
| :--- | :--- | :--- | :--- |
| **Waveshare RP2040-One** | Integrated USB-A Male Plug | ~$3 - $4 | **Top Recommendation.** Plugs directly into any USB port like a normal flash drive without extra cables. |
| **Waveshare RP2040-Zero** | Postage-stamp size USB-C | ~$3 | Extremely tiny. Fits inside custom enclosures or soldered to hubs. |
| **Raspberry Pi Pico / Pico W** | Standard Board | ~$4 | Globally available at every electronics store / Amazon. |
| **Hak5 Rubber Ducky / BadUSB** | Commercial USB Dongle | ~$20 - $50 | Uses the raw `.duck` scripts in `D:\tools\auto-inject\`. |

---

## 3. The "1-Plug" Holy Grail Setup

To have **one single physical plug** that you insert into any PC:
* Use a **$2 Ultra-Compact 2-Port USB Hub / Dual Splitter**:
  * Port 1: Your 128GB SanDisk GhostVault pendrive.
  * Port 2: Your RP2040-One / Pico HID injector.
* When you plug the single USB male connector into any target machine:
  1. The target machine enumerates both the keyboard and the 128GB flash drive simultaneously.
  2. The keyboard fires the injection script in 300ms.
  3. Ghost-OS executes, scans hardware, and opens the dashboard!

---

## 4. 3-Minute Flashing Tutorial (Raspberry Pi Pico / RP2040)

### Step 1: Install CircuitPython
1. Download the CircuitPython `.uf2` firmware file for your board from:
   * **Raspberry Pi Pico:** [circuitpython.org/board/raspberry_pi_pico](https://circuitpython.org/board/raspberry_pi_pico/)
   * **Waveshare RP2040-Zero:** [circuitpython.org/board/waveshare_rp2040_zero](https://circuitpython.org/board/waveshare_rp2040_zero/)
2. Hold down the white **BOOTSEL** button on your Pico / RP2040 board.
3. Plug the Pico into your computer's USB port while holding BOOTSEL, then release it.
4. A drive named `RPI-RP2` will appear in Windows Explorer.
5. Drag and drop the downloaded `.uf2` file onto the `RPI-RP2` drive.
6. The board will automatically reboot and reappear as a drive named **`CIRCUITPY`**.

### Step 2: Copy the HID Keyboard Library
1. Download the CircuitPython Community Bundle from [circuitpython.org/libraries](https://circuitpython.org/libraries).
2. Inside the bundle's `lib/` folder, find the folder named `adafruit_hid`.
3. Copy the entire `adafruit_hid` folder into the `lib/` folder on your `CIRCUITPY` drive:
   ```text
   CIRCUITPY/
   ├── lib/
   │   └── adafruit_hid/
   ```

### Step 3: Copy Ghost-OS Firmware Files
1. Copy the following files from your 128GB pendrive (`D:\tools\auto-inject\`):
   * `D:\tools\auto-inject\code.py` &rarr; `CIRCUITPY\code.py`
   * *(Optional)* `D:\tools\auto-inject\boot.py` &rarr; `CIRCUITPY\boot.py` (Hides the `CIRCUITPY` drive for pure stealth).
2. Safely eject the Pico.

**You are done!**

---

## 5. How It Operates

* **Windows Target:** Plug in the injector and 128GB pendrive. Within 0.4 seconds, `Win+R` opens, types the silent launcher command, and executes Ghost-OS.
* **macOS Target:** Connect a jumper wire between Pin `GP0` and `GND` on the Pico. It will automatically trigger macOS Spotlight (`Cmd+Space`) and execute `Launch-GhostOS.command`.
* **Linux Target:** Connect a jumper wire between Pin `GP1` and `GND`. It triggers terminal (`Ctrl+Alt+T`) and runs `Launch-GhostOS.sh`.

Once launched, open your browser to `http://127.0.0.1:8000/`, enter password **`Abhyas2108`**, and view the hardware diagnostics!
