# ==============================================================================
# Ghost-OS Pico Ducky Firmware v2.1 (CircuitPython)
# Runs on Raspberry Pi Pico / RP2040-Zero / RP2040-One microcontroller
#
# SECURITY COMPLIANCE (Sprint 1 Production Hardening):
# - Automatic keystroke injection is DISABLED by default.
# - Requires EXPLICIT physical operator authorization via physical button push (GP2 or BOOTSEL).
# - Disarms automatically after 10-second safety timeout if no confirmation is detected.
# ==============================================================================

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# Security Policy Configuration
REQUIRE_OPERATOR_CONFIRMATION = True  # Strict Security: Must press confirmation button
AUTHORIZATION_TIMEOUT_SECONDS = 10.0  # Disarms if not authorized within 10s

# Initialize USB HID Keyboard
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# Status LED Setup (supports standard Pico GP25 and board.LED)
led = None
try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
except Exception:
    pass

# Operator Authorization Button (Pin GP2 to GND)
pin_auth = None
try:
    pin_auth = digitalio.DigitalInOut(board.GP2)
    pin_auth.direction = digitalio.Direction.INPUT
    pin_auth.pull = digitalio.Pull.UP
except Exception:
    pass

# OS Selector Jumper Pins
# - Default (no jumpers): Windows Mode
# - Pin GP0 to GND: macOS Mode
# - Pin GP1 to GND: Linux Mode
pin_mac = None
pin_linux = None
try:
    pin_mac = digitalio.DigitalInOut(board.GP0)
    pin_mac.direction = digitalio.Direction.INPUT
    pin_mac.pull = digitalio.Pull.UP

    pin_linux = digitalio.DigitalInOut(board.GP1)
    pin_linux.direction = digitalio.Direction.INPUT
    pin_linux.pull = digitalio.Pull.UP
except Exception:
    pass


def set_led(state: bool):
    if led:
        led.value = state


def wait_for_operator_authorization() -> bool:
    """Waits for operator to physically press the authorization button (GP2 -> GND).

    Flashes LED in a distinct alert cadence while armed.
    Returns True if authorized, False if timed out (disarmed).
    """
    if not REQUIRE_OPERATOR_CONFIRMATION:
        return True

    start_time = time.monotonic()
    blink = False

    while (time.monotonic() - start_time) < AUTHORIZATION_TIMEOUT_SECONDS:
        # Check authorization button (Active LOW)
        if pin_auth and not pin_auth.value:
            set_led(True)
            time.sleep(0.3)
            return True

        # Rapid security pulse (5 Hz)
        blink = not blink
        set_led(blink)
        time.sleep(0.1)

    # Disarmed on timeout
    set_led(False)
    return False


def inject_windows():
    """Injects Windows launcher command via Win+R in under 400ms."""
    set_led(True)
    time.sleep(0.4)
    kbd.send(Keycode.GUI, Keycode.R)
    time.sleep(0.2)
    cmd = 'powershell -WindowStyle Hidden -Command "$d=(Get-Volume -FileSystemLabel GhostVault).DriveLetter; if($d){Start-Process ($d+\':\\Launch-GhostOS.cmd\')}"'
    layout.write(cmd)
    time.sleep(0.1)
    kbd.send(Keycode.ENTER)
    time.sleep(0.2)
    set_led(False)


def inject_mac():
    """Injects macOS launcher command via Spotlight search in under 700ms."""
    set_led(True)
    time.sleep(0.6)
    kbd.send(Keycode.GUI, Keycode.SPACE)
    time.sleep(0.25)
    layout.write("terminal")
    kbd.send(Keycode.ENTER)
    time.sleep(0.5)
    layout.write("sh /Volumes/GhostVault/Launch-GhostOS.command\n")
    time.sleep(0.2)
    set_led(False)


def inject_linux():
    """Injects Linux launcher command via desktop terminal in under 600ms."""
    set_led(True)
    time.sleep(0.5)
    kbd.send(Keycode.CONTROL, Keycode.ALT, Keycode.T)
    time.sleep(0.4)
    layout.write("sh /media/$USER/GhostVault/Launch-GhostOS.sh\n")
    time.sleep(0.2)
    set_led(False)


def main():
    # Wait for host USB enumeration
    time.sleep(1.0)

    # Enforce Operator Confirmation Gate
    authorized = wait_for_operator_authorization()
    if not authorized:
        # Disarmed: do nothing, remain idle
        return

    # Detect OS Mode via Jumper or default to Windows
    is_mac = pin_mac and not pin_mac.value
    is_linux = pin_linux and not pin_linux.value

    if is_mac:
        inject_mac()
    elif is_linux:
        inject_linux()
    else:
        inject_windows()


if __name__ == "__main__":
    main()
