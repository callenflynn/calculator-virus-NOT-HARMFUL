# Calcu 2.2+ (Babbage, Night Shift Edition)

> **A boring calculator REPL that secretly unleashes a scripted scare show when you press Enter on an empty line.**
>
> Pure Python 3 + stdlib. Windows only. Entirely reversible. No permanent damage.

---

## ⚠️ SAFETY CONTRACT

**This is a prank. Nothing destructive happens.** Every scary line is fake text or fake log output. Real system changes (wallpaper, taskbar, mouse, screen colors, resolution, desktop icons) are **all restored** in both a `finally` block AND a detached watchdog process that runs even if the main process is killed.

- ❌ No files are deleted
- ❌ No formatting or shutdown commands actually execute
- ❌ No registry keys touched (except the desktop icon layout Bag key, which is backed up & restored)
- ❌ No persistence (no startup entries, no scheduled tasks, no services)
- ✅ Everything is cleaned up on exit
- ✅ A watchdog restores everything after ~10 minutes even if the process dies

**Still: test this on a VM first. Do not run on machines you don't own. Contains strobe-like white flashes — skip for photosensitive people.**

---

## 🚀 How to Run

```bash
python v3.py
```

On launch, it **requests admin via UAC** (for maximum scare potential). If declined, it continues without admin.

You'll see a plain calculator prompt:

```
Simple Calculator
=================
Enter an expression such as 4+5*2 and press Enter.

calc>
```

It works as a real calculator — type `4+5*2`, get `= 14`. Only arithmetic characters are allowed (regex whitelist, no `eval` of arbitrary input).

**Press Enter on an empty line** to trigger the show.

---

## 🎬 The Show — 18 Visual Screens (in order)

All screens are fullscreen, topmost, and closable with `Escape`. The entire sequence takes ~3-4 minutes.

| # | Screen | Description |
|---|--------|-------------|
| 1 | **Fake BIOS Boot** | Phoenix CalBIOS text, ends with "Loading cal32.sys ... FAILED" |
| 2 | **BOOTMGR Missing** | Black screen: "BOOTMGR is missing. Press Ctrl+Alt+Del to restart" |
| 3 | **BSOD** | `:(` emoji, progress percentage, random stop code with `(CAL_2_2)` suffix, fake QR code |
| 4 | **Automatic Repair** | "Preparing Automatic Repair..." → spinner "Diagnosing your PC" → "Automatic Repair couldn't repair your PC" with Advanced/Restart buttons |
| 5 | **Fake chkdsk** | 5 stages with percentages, ends in error `0xC0000225` — runs twice for extra panic |
| 6 | **Glitch Distortion** | Random colored bars, white flashes, glitch phrases — runs in parallel with **mouse button swap + cursor ghost trails** |
| 7 | **Matrix Rain** | Green katakana characters falling, occasional white highlights |
| 8 | **Webcam Overlay** | Static noise, red REC dot, "CAM_0 ACTIVE \| viewer: \<username\>" |
| 9 | **Hacked CMD Console** | Types `del kernel32.dll` (ACCESS DENIED), `format C:` (volume in use), `shutdown /s /t 10` (already scheduled), `net user Administrator /active:no` (denied) |
| 10 | **Fake UAC Dialog** | "CAL-OS System Integrity Checker" — "Verified publisher: Cal Industries Ltd." with Yes/No buttons |
| 11 | **Security Scanner** | Scrolling fake file paths, green/red, "THREATS DETECTED — QUARANTINE FAILED", staggered real `MessageBox` popups in parallel |
| 12 | **Deleting System Files** | Progress bar, "Deleting C:\\Windows\\System32\\kernel32.dll ... OK", ends with "SYSTEM32 ACCESS DENIED" |
| 13 | **Fake Ransomware** | Countdown timer, 120 fake `.dat` → `.crypt` renamed in a staging folder, log of real user filenames, `READ_ME_TO_DECRYPT.txt` on Desktop, TTS voice: *"Just kidding. This is a calculator. Cal says hi."* |
| 14 | **Windows Update** | Spinner, "Working on updates", ends with "We couldn't complete the updates" |
| 15 | **Fake sfc /scannow** | Lists corrupt files including `cal32.sys`, `win32k.sys`, "Reboot required" |
| 16 | **Sign-Out Countdown** | "You are about to be signed out" — counts from 10 to 0 with a Cancel button that actually closes it |
| 17 | **PSYCH! Reveal** | Green text: "PSYCH! Just kidding. Nothing happened." |
| 18 | **Afterparty** | "REBOOTING IN 3... 2... 1..." → "Just kidding. Have a nice day. :)" |

---

## 🖥️ Real System Effects (all restored)

| Effect | How | Restoration |
|--------|-----|-------------|
| **Wallpaper swap** | Downloads scary image, converts to BMP via GDI+, falls back to red BMP | `SystemParametersInfoW` restores original |
| **Taskbar hidden** | `FindWindowW("Shell_TrayWnd")` + `ShowWindow(0)` | Watchdog & finally block restore it |
| **Start button hidden** | `FindWindowExW` for "Start" button | Restored on cleanup |
| **Desktop icons toggled** | `SendMessageW(WM_COMMAND, 0x7402)` toggles visibility | Toggled back in finally block |
| **Icon layout scrambled** | Backs up `HKCU\...\Bags\1\Desktop` to `.reg`, sets `FFlags` to force auto-arrange | `reg import` + Explorer restart |
| **60 fake desktop shortcuts** | `CAL_2_2_*.lnk` pointing at notepad.exe, calc.exe, etc. | Deleted by prefix sweep in finally + watchdog |
| **Mouse button swap** | `SwapMouseButton(True)` then restored | Restored in finally + watchdog |
| **Cursor hidden & teleported** | `ShowCursor(False)`, `SetCursorPos` random + lissajous frenzy | Restored in finally + watchdog |
| **Ghost cursor trails** | Topmost transparent tkinter arrow windows following the pointer | Destroyed when the thread ends |
| **Screen color inversion** | Magnification API with negative transform matrix | Identity matrix restored in finally + watchdog |
| **640×480 resolution** | `ChangeDisplaySettingsW` with CDS flags = 0 (registry untouched), original `DEVMODE` saved to `devmode.bin` | Restored from `devmode.bin` in finally + watchdog |
| **Start menu spam** | `keybd_event` VK_LWIN open/close 4× | Stops on its own |
| **CPU burn loop** | Busy PRNG loop, fans spin up | Ends on its own after 8 seconds |

---

## 🎪 Extras

### Jumpscare
- Downloads a scary GIF and WebP from the web into `%TEMP%\calcu_scare\`
- Converts WebP → BMP via `System.Drawing` (GDI+)
- Strobes images fullscreen for ~9 seconds alternating with white/black flashes
- Simultaneous descending scream beeps: 1600 Hz → 300 Hz, 3 passes
- All images deleted on exit via temp folder cleanup

### TTS Voice Lines
Windows Speech API reads aloud at show start:
- *"I can see you, \<username\>. Do not be alarmed."*
- *"The diagnostics have already begun."*
- *"I am inside your computer now."*
- *"Your Downloads folder has been reorganized."*
- Plus a Caesar-shifted legacy key string

### Browser Tab Flood
40 tabs opened in the default browser from a pool of 41 URLs — funny videos, "how to remove virus" searches, Rick Rolls, and (behind `NSFW_JOKES = True`) 10 adult sites. Tabs are not closed (closing someone's real tabs would be destructive).

### Terminal Flood
Three waves of cmd windows:
1. **60** that open and close instantly
2. **300** with `timeout /t 2 >nul` (close after 2 seconds)
3. **40** with `timeout /t 1 >nul` (close after 1 second)

### Downloads Flood
60 junk files (2-64 KB of random bytes) with extensions like `.dat`, `.exe`, `.jpg`, `.crypt` named `CAL_2_2_download_<hex>.<ext>` created in the **real Downloads folder** (resolved via `shell:Downloads` to honor OneDrive redirection). Deleted on cleanup by finally block, watchdog, and prefix sweep.

### Random Apps
12 harmless Windows apps opened at random: Notepad, Paint, Calculator, CMD, Control Panel, WinVer, On-Screen Keyboard, WordPad, Task Manager, Remote Desktop, Explorer.

### Fake Registry Editor
tkinter regedit window showing `HKEY_LOCAL_MACHINE\SYSTEM\...` tree, typing fake deletion lines like "Deleting HKLM\SYSTEM\... OK", ending with "ERROR: Access is denied. Key is in use."

### Fake Task Manager
Window showing `cal32.exe` processes multiplying every 150ms up to 45 entries with random CPU/memory/disk/network/PID values, ending with "Unable to terminate cal32.exe processes".

### Content Pools
- **16** message box alerts (critical errors, security breaches, webcam alerts, etc.)
- **13** notepad texts (creepy messages opened in Notepad windows)
- **9** BSOD stop codes (all suffixed with `(CAL_2_2)`)
- **8** glitch phrases (MEMORY CORRUPTION, CRC CHECK FAILED, etc.)
- **30** shortcut name suffixes (DO_NOT_OPEN, virus_scan, SYS_CRITICAL, etc.)

---

## 🛡️ Watchdog Process

A **detached Python process** (`DETACHED_PROCESS + CREATE_NO_WINDOW`) waits ~600 seconds, then restores:

- Wallpaper (original)
- Taskbar & Start button visibility
- Desktop icon visibility
- Mouse buttons (un-swapped) & cursor (shown)
- Screen color inversion (identity matrix)
- Resolution (from `devmode.bin`)
- Deletes all `CAL_2_2_*` shortcuts from Desktop
- Deletes all `CAL_2_2_*` files from Downloads
- Imports the icon layout `.reg` backup
- Restarts Explorer
- Deletes its own script
- Removes the temp folder

This runs even if the main process crashes or is killed.

---

## ⚙️ Tunables

All constants at the top of `v3.py` — tweak to customize:

| Constant | Default | Description |
|----------|---------|-------------|
| `BSOD_S` | 14 | BSOD screen duration (seconds) |
| `TAB_SPAM` | 40 | Browser tabs opened |
| `ICON_SPAM` | 60 | Fake desktop shortcuts |
| `DOWNLOAD_SPAM` | 60 | Junk files in Downloads |
| `TERMINAL_SPAM` | 60 | Quick cmd windows |
| `TERMINAL_SPAM2` | 300 | cmd windows with 2s timeout |
| `TERMINAL_SPAM3` | 40 | cmd windows with 1s timeout |
| `APP_SPAM` | 12 | Random apps opened |
| `JUMPSCARE_S` | 9 | Jumpscare strobe duration |
| `WATCHDOG_S` | 600 | Watchdog restore delay (seconds) |
| `NSFW_JOKES` | True | Toggle NSFW browser tabs |

---

## 📋 Requirements

- **Windows 10/11** (uses `ctypes`, `tkinter`, `winsound`, `System.Drawing`, Magnification API, Speech API)
- **Python 3.8+** (stdlib only, no pip packages needed)
- Admin rights **requested** via UAC but **not required** — works either way

---

## ⚠️ Warning

This is a **prank program** intended for use among consenting friends. It simulates system failure in a convincing way. Do not:
- Run it on machines you don't own
- Run it on people with heart conditions or photosensitive epilepsy (contains strobe flashes)
- Use it for anything other than harmless pranks

*— Cal Industries Ltd.*
