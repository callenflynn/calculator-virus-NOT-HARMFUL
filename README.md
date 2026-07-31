# Calcu (Babbage, Night Shift Edition)

> A calculator REPL. Press Enter on an empty line to start a scripted
> scare show. Windows only. Pure Python 3 stdlib.

**Three editions are available:**

| File | Behavior |
|------|----------|
| `v3.py` | Safe edition. Restores everything after the show. Uses a watchdog. |
| `v3-aftermath.py` | Aftermath edition. Does NOT clean up. Leaves the mess. |
| `v4.py` | TOTAL RECALL edition. Aftermath with 10+ new scare effects. 30-min watchdog. |

## Files
### V2
v2.py - does not have watchdog, no permenant changes
### v3
v3.py - has watchdog, undoes all changes after time is up
v3-aftermath.py - does not have watchdog, changes are annoying to undo

All changes are reversible. A `finally` block and a detached watchdog
process restore everything.

### v3-aftermath.py — Aftermath Edition

**Does NOT clean up.** No watchdog. No finally block. No restore.

### v4.py — TOTAL RECALL Edition

Based on the aftermath edition. Adds 12 new scare effects:

- **Screen rotation.** Flips the display 180° for 5 seconds.
- **Window shuffle.** Scatters all open windows to random positions.
- **Volume haunt.** Random mute/volume-up/volume-down keypresses.
- **Sticky Keys trap.** Triggers the real Windows Sticky Keys prompt.
- **Password expired.** Fake "change your password" fullscreen dialog.
- **Discord ban.** Fake "banned from every server" screen.
- **Selfie scare.** Screenshots the desktop and shows it as a live webcam feed.
- **Reversed whisper.** Plays a backwards TTS voice message before the reveal.
- **Activation watermark.** Persistent "Windows is not activated" overlay.
- **Toast spam.** Fake Windows 11 notification toasts in the corner.
- **BIOS update.** Fake firmware update stuck at 99%, then fails.
- **Spy stats.** Reveal screen shows process count, tabs, and notes.

Also:
- Windows Update screen gets stuck at 99% before failing.
- NSFW URLs replaced with SFW scary alternatives.
- Watchdog fires after 30 minutes (1800 s) for automatic recovery.
- Requests UAC admin on launch.

## SAFETY CONTRACT

This is a prank. No destructive actions occur. All scary text is fake
output.

Real system changes are **all restored** by a `finally` block and a
detached watchdog process:

- Wallpaper (restored)
- Taskbar and Start button (restored)
- Desktop icons (restored)
- Mouse buttons and cursor (restored)
- Screen colors (restored)
- Screen resolution (restored)

No files are deleted. No registry keys are touched (except the desktop
icon layout key, which is backed up and restored). No persistence
exists.

**Test on a VM first. Do not run on machines you do not own.**
**Contains white flashes. Do not use with photosensitive persons.**

**For maximal safe scare, run `v3.py`. For total aftermath, run `v4.py`.**

## How to Run

```bash
python v3.py
```

The program requests admin rights via UAC on launch. If you decline,
it continues without admin.

You will see a calculator prompt:

```
Simple Calculator
=================
Enter an expression such as 4+5*2 and press Enter.

calc>
```

Type `4+5*2` and you get `= 14`. Only arithmetic characters are
permitted (regex whitelist).

**Press Enter on an empty line** to start the show.

## The Show (18 Screens)

All screens are fullscreen, topmost. Press Escape to close each one.
The show takes 3 to 4 minutes.

| # | Screen | What you see |
|---|--------|--------------|
| 1 | BIOS boot | Fake boot text. Ends with "Loading cal32.sys ... FAILED" |
| 2 | BOOTMGR | Black screen: "BOOTMGR is missing" |
| 3 | BSOD | `:(` face, percent counter, stop code + "(CAL_2_2)", fake QR code |
| 4 | Auto Repair | "Preparing Automatic Repair..." then spinner, then "could not repair" |
| 5 | chkdsk | 5 stages with percent. Ends with error 0xC0000225. Runs twice |
| 6 | Glitch | Random colored bars, white flashes, glitch words. Mouse buttons swap |
| 7 | Matrix rain | Green katakana characters fall |
| 8 | Webcam | Static noise, red REC dot, "CAM_0 ACTIVE \| viewer: \<name\>" |
| 9 | Hacked CMD | Fake console typing destructive commands. Each gets "ACCESS DENIED" |
| 10 | Fake UAC | "CAL-OS System Integrity Checker" dialog. Yes/No buttons |
| 11 | Security scan | Fake file paths scroll. "THREATS DETECTED". Real MessageBox popups |
| 12 | Delete files | Progress bar. "Deleting System32...". Ends with "ACCESS DENIED" |
| 13 | Ransomware | Countdown timer. 120 fake files renamed. TTS voice says it is a joke |
| 14 | Windows Update | Spinner. "Working on updates". Ends with "could not complete" |
| 15 | sfc /scannow | Lists corrupt files (cal32.sys). "Reboot required" |
| 16 | Sign-out | Counts from 10 to 0. Cancel button closes it |
| 17 | PSYCH! | Green text: "Just kidding. Nothing happened." |
| 18 | Afterparty | "REBOOTING IN 3... 2... 1..." then "Have a nice day. :)" |

## Real System Effects

| Effect | Method | Restored by |
|--------|--------|-------------|
| Wallpaper | Downloads scary image, converts to BMP | `SystemParametersInfoW` |
| Taskbar hidden | `FindWindowW` + `ShowWindow(0)` | Finally + watchdog |
| Start button hidden | `FindWindowExW` for "Start" | Finally + watchdog |
| Desktop icons toggled | `SendMessageW(0x7402)` | Finally block |
| Icon layout scrambled | Backs up Bag key, sets FFlags | `reg import` + Explorer restart |
| 60 fake shortcuts | `CAL_2_2_*.lnk` on Desktop | Deleted by prefix sweep |
| Mouse buttons swapped | `SwapMouseButton(True)` | Finally + watchdog |
| Cursor hidden/teleported | `ShowCursor(False)`, lissajous frenzy | Finally + watchdog |
| Ghost cursor trails | Transparent tkinter windows | Destroyed on thread end |
| Screen colors inverted | Magnification API matrix | Identity matrix restored |
| 640×480 resolution | `ChangeDisplaySettingsW` (CDS=0) | `devmode.bin` restore |
| Start menu spam | `keybd_event` VK_LWIN ×4 | Stops on its own |
| CPU burn | PRNG busy loop | Ends after 8 seconds |

## Extras

**Jumpscare.** Downloads a GIF and WebP. Converts WebP to BMP via
`System.Drawing`. Strobes fullscreen with white/black flashes for
~9 seconds. Descending scream beeps (1600→300 Hz, 3 passes).

**TTS voice.** Speaks 5 lines at show start:
- "I can see you, \<name\>. Do not be alarmed."
- "The diagnostics have already begun."
- "I am inside your computer now."
- "Your Downloads folder has been reorganized."
- A Caesar-shifted key string.

**Tab flood.** Opens 40 browser tabs from 41 URLs. Funny videos, virus
removal searches, Rick Rolls. 10 adult sites behind `NSFW_JOKES=True`.

**Terminal flood.** 60 cmd windows open/close fast. 300 with 2-second
timeout. 40 with 1-second timeout.

**Downloads flood.** 60 junk files (2-64 KB random bytes) in the real
Downloads folder. Named `CAL_2_2_download_<hex>.<ext>`. Deleted on cleanup.

**Random apps.** Opens 12 Windows apps: Notepad, Paint, Calculator, CMD,
Control Panel, WinVer, On-Screen Keyboard, WordPad, Task Manager,
Remote Desktop, Explorer.

**Fake Registry Editor.** A tkinter window that types fake deletion lines.
Ends with "ERROR: Access is denied. Key is in use."

**Fake Task Manager.** Shows `cal32.exe` processes. Multiplies every
150 ms up to 45 entries. Ends with "Unable to terminate."

## Watchdog

A detached Python process waits ~600 seconds, then:

- Restores wallpaper, taskbar, Start button, desktop icons
- Restores mouse buttons and cursor
- Restores screen colors (identity matrix)
- Restores resolution from `devmode.bin`
- Deletes all `CAL_2_2_*` shortcuts from Desktop
- Deletes all `CAL_2_2_*` files from Downloads
- Imports the icon layout `.reg` backup
- Restarts Explorer
- Deletes its own script
- Removes the temp folder

The watchdog runs even if the main process is killed.

## Tunables

Edit the constants at the top of `v3.py`:

| Constant | Default | Function |
|----------|---------|----------|
| `BSOD_S` | 14 | BSOD screen seconds |
| `TAB_SPAM` | 40 | Browser tabs opened |
| `ICON_SPAM` | 60 | Fake desktop shortcuts |
| `DOWNLOAD_SPAM` | 60 | Junk files in Downloads |
| `TERMINAL_SPAM` | 60 | Quick cmd windows |
| `TERMINAL_SPAM2` | 300 | cmd windows (2s timeout) |
| `TERMINAL_SPAM3` | 40 | cmd windows (1s timeout) |
| `APP_SPAM` | 12 | Random apps opened |
| `JUMPSCARE_S` | 9 | Jumpscare duration |
| `WATCHDOG_S` | 600 / 1800 | Watchdog delay (v3=600s, v4=1800s) |
| `NSFW_JOKES` | True | Adult browser tabs |

## Requirements

- Windows 10 or 11
- Python 3.8 or newer (stdlib only, no pip installs)
- Admin rights requested via UAC (not required)

## Warning

This is a prank for consenting friends. It simulates system failure.
Do not:
- Run it on machines you do not own
- Use it on persons with heart conditions or epilepsy
- Use it for anything other than harmless pranks

*— Cal Industries Ltd.*
