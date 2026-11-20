# ==============================================================================
# Ghost-OS Pico Ducky Stealth Boot Configuration (CircuitPython)
# Prevents the Pico from mounting as a visible flash drive on the target PC
# Keeps only the trusted USB Keyboard HID active for pure stealth injection!
# ==============================================================================

import storage
import board
import digitalio

# To re-enable the CIRCUITPY drive for editing code:
# Hold Pin GP3 to GND while plugging in!
edit_pin = None
try:
    edit_pin = digitalio.DigitalInOut(board.GP3)
    edit_pin.direction = digitalio.Direction.INPUT
    edit_pin.pull = digitalio.Pull.UP
except Exception:
    pass

# If edit_pin is pulled to GND, keep drive enabled; otherwise hide drive
if edit_pin and edit_pin.value:
    storage.disable_usb_drive()
