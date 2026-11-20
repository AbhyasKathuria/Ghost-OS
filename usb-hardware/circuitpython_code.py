"""Ghost-OS Hardware HID Auto-Launcher for Raspberry Pi Pico / RP2040.

When flashed onto an RP2040 micro-controller presenting both USB Mass Storage
and USB Keyboard HID, this script executes instantly when plugged into Windows,
launching Ghost-OS without requiring manual double-clicking.
"""

import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# Short delay to allow Windows USB enumeration
time.sleep(0.5)

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# Press Win + R to open Run dialog
kbd.press(Keycode.GUI, Keycode.R)
time.sleep(0.1)
kbd.release_all()

time.sleep(0.2)

# PowerShell 1-liner to find GhostVault drive letter and execute launcher
cmd = "powershell -NoP -W Hidden -C \"$v=Get-Volume -FileSystemLabel 'GhostVault' -EA SilentlyContinue; if($v){ & \\\"$($v.DriveLetter):\\Launch-GhostOS.cmd\\\" }\"\n"
layout.write(cmd)
time.sleep(0.1)
kbd.send(Keycode.ENTER)
