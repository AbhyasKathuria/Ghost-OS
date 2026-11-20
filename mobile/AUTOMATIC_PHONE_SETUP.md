# Ghost-OS: How Automatic USB Type-C Plug-in Works on Android & iOS

## 1. The Security Reality (Why Phones Don't Run Raw EXE Files)
Modern mobile operating systems (Android and Apple iOS) have strict operating system sandboxes. To protect users from malicious flash drives that could steal photos or passwords, mobile operating systems do not allow unknown external storage drives to execute arbitrary binary code silently in the background without user interaction.

However, Ghost-OS is engineered to give you the **fastest, seamless, 1-tap automated experience** possible on modern smartphones.

---

## 2. Default Zero-Setup Experience (Works on EVERY Phone Out-of-the-Box)

### On Android (via USB-to-Type-C Adapter):
1. Plug your pendrive into your Android phone using your Type-C adapter.
2. Android will immediately make a chime and display a notification:
   > **"SanDisk USB Drive &bull; Tap to explore / view files"**
3. Tap the notification.
4. Tap **`START_HERE.html`** (or `index.html`).
5. **What Happens Instantly:**
   * Opens immediately in your mobile browser with zero installation.
   * Auto-detects your phone brand and Android version.
   * Audits your CPU cores, RAM, and screen resolution.
   * Queries the live battery level and charging state via HTML5 hardware APIs.
   * Calculates your phone's Hardware Health Score (e.g. 98/100).
   * Generates a verified Mobile Diagnostic Certificate you can save or share!

### On Apple iPhone 15/16 or iPad (via Type-C Adapter):
1. Plug the pendrive into your iPhone/iPad.
2. Open the native **Files app**.
3. Under Locations, tap **GhostVault**.
4. Tap **`START_HERE.html`** &rarr; Mobile Safari renders the live hardware audit and certificates offline!

---

## 3. How to Make it 100% Zero-Touch "Auto-Launch" on Android (No Tapping Required)

If you want your Android phone to automatically open Ghost-OS the millisecond you plug in the USB drive:

### Option A: Using MacroDroid (Free, 30-Second Setup)
1. Install **MacroDroid** from the Google Play Store on your phone.
2. Tap **Add Macro**:
   * **Trigger:** *Connectivity &rarr; USB Device Connected* (Any device or Mass Storage).
   * **Action:** *Applications &rarr; Open Website / File* &rarr; Select `START_HERE.html` on the USB drive.
3. Save the macro.
4. **Done!** Now, whenever you plug the pendrive into your phone with your Type-C adapter, your phone will automatically turn on the screen and display the Ghost-OS hardware console with zero clicks!

### Option B: Using Termux (For IT Technicians & Complete System Dumps)
1. Install **Termux** on Android.
2. Plug in the USB drive.
3. In Termux, navigate to the drive:
   ```sh
   sh /sdcard/../Launch-GhostOS-Android.sh
   ```
4. It reads internal kernel structures (`/proc/cpuinfo`, `/sys/class/power_supply/battery/`) and saves a complete hardware audit file directly back onto the USB drive.
