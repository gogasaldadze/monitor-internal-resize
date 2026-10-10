"""Play CS2 stretched (e.g. 1280x960) on a smaller virtual monitor with black borders.

Uses the Windows display API to scale the desktop into a centered region of the
panel that has the physical size you want (e.g. a 24" area on a 26.5" monitor).
The normal desktop is restored when CS2 exits.

Usage:
    python cs2_24inch.py run   [options]   apply, launch CS2, restore when it closes (default)
    python cs2_24inch.py on    [options]   apply and leave it on
    python cs2_24inch.py off               restore the normal desktop
    python cs2_24inch.py test  [options]   apply for 15 seconds, then restore
    python cs2_24inch.py info              show monitor and current layout
"""
import argparse
import atexit
import ctypes
import math
import os
import sys
import time
import winreg
from ctypes import wintypes

import displaycfg as dc
import layout

CS2_EXE = "cs2.exe"
CS2_STEAM_URI = "steam://rungameid/730"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cs2_24inch.log")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def edid_diagonal_inches(path):
    """Panel diagonal from the EDID physical size (cm), or None if unavailable."""
    req = dc.TARGET_DEVICE_NAME()
    req.header.type = dc.DEVICE_INFO_GET_TARGET_NAME
    req.header.size = dc.ctypes.sizeof(req)
    req.header.adapterId = path.targetInfo.adapterId
    req.header.id = path.targetInfo.id
    if dc.user32.DisplayConfigGetDeviceInfo(dc.ctypes.byref(req)) != 0:
        return None
    # \\?\DISPLAY#AUS27B1#5&1234&0&UID4353#{guid} -> DISPLAY\AUS27B1\5&1234&0&UID4353
    parts = req.monitorDevicePath.split("#")
    if len(parts) < 3:
        return None
    key = rf"SYSTEM\CurrentControlSet\Enum\DISPLAY\{parts[1]}\{parts[2]}\Device Parameters"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            edid, _ = winreg.QueryValueEx(k, "EDID")
    except OSError:
        return None
    w_cm, h_cm = edid[21], edid[22]
    if not w_cm or not h_cm:
        return None
    return math.hypot(w_cm, h_cm) / 2.54


def parse_res(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def resolve(args):
    """Query the current config and work out the target layout."""
    paths, modes = dc.query()
    i = layout.find_path(paths, args.monitor)
    panel_w, panel_h = layout.panel_size(paths, modes, i)
    panel_in = args.panel or edid_diagonal_inches(paths[i])
    if not panel_in:
        raise ValueError("Could not read the panel size from EDID; set the monitor size.")
    if args.size > panel_in:
        raise ValueError(f"Size {args.size}\" is larger than the monitor ({panel_in:.1f}\").")
    region = layout.region_for_size(panel_w, panel_h, panel_in, args.size)
    return paths, modes, i, (panel_w, panel_h), panel_in, region


def apply_layout(args):
    paths, modes, i, panel, panel_in, region = resolve(args)
    src_w, src_h = parse_res(args.res)
    new_paths, new_modes = layout.build(paths, modes, i, src_w, src_h, region)
    flags = dc.SDC_USE_SUPPLIED_DISPLAY_CONFIG | dc.SDC_VIRTUAL_MODE_AWARE | dc.SDC_ALLOW_CHANGES
    dc.apply(new_paths, new_modes, flags | dc.SDC_VALIDATE)
    # Not saved to the Windows display database, so a reboot or `off` always restores normal.
    dc.apply(new_paths, new_modes, flags | dc.SDC_APPLY)
    l, t, r, b = region
    log(f"ON: {src_w}x{src_h} stretched into {r - l}x{b - t} "
        f"({args.size}\" area on a {panel_in:.1f}\" {panel[0]}x{panel[1]} panel)")
    return paths, modes


def layout_active(args):
    """True if the desktop is currently at --res inside a shrunken region."""
    paths, modes = dc.query()
    p = paths[layout.find_path(paths, args.monitor)]
    src = modes[p.sourceInfo.source_mode_idx].sourceMode
    img = modes[p.targetInfo.desktop_mode_idx].desktopImageInfo
    r = img.DesktopImageRegion
    full = r.left == 0 and r.top == 0 and (r.right, r.bottom) == (img.PathSourceSize.x, img.PathSourceSize.y)
    tgt = modes[p.targetInfo.target_mode_idx].targetMode.targetVideoSignalInfo
    state = (f"desktop {src.width}x{src.height} in {img.PathSourceSize.x}x{img.PathSourceSize.y} "
             f"region={r!r} signal {tgt.activeSize.cx}x{tgt.activeSize.cy}"
             f"@{tgt.vSyncFreq.Numerator / max(tgt.vSyncFreq.Denominator, 1):.2f} scaling={p.targetInfo.scaling}")
    return (src.width, src.height) == parse_res(args.res) and not full, state


def restore(saved=None):
    if saved is not None:
        try:
            dc.apply(*saved, dc.SDC_USE_SUPPLIED_DISPLAY_CONFIG | dc.SDC_VIRTUAL_MODE_AWARE
                     | dc.SDC_ALLOW_CHANGES | dc.SDC_APPLY)
            log("OFF: normal desktop restored")
            return
        except dc.DisplayConfigError as e:
            log(f"Exact restore failed ({e}); falling back to the saved Windows layout")
    # SDC_USE_DATABASE_CURRENT: re-apply what Windows has stored for this monitor setup.
    rc = dc.user32.SetDisplayConfig(0, None, 0, None, dc.SDC_APPLY | 0x0F)
    log("OFF: normal desktop restored" if rc == 0 else f"OFF failed: error {rc}")


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE


def cs2_running():
    snap = _k32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if snap == wintypes.HANDLE(-1).value:
        return True  # can't tell; assume still running rather than restoring mid-game
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(e)
        ok = _k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.szExeFile.lower() == CS2_EXE:
                return True
            ok = _k32.Process32NextW(snap, ctypes.byref(e))
        return False
    finally:
        _k32.CloseHandle(snap)


_HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)


def restore_on_console_close(saved):
    """Restore the desktop when the console window is closed (atexit does not run then)."""
    def handler(event):
        if event in (2, 5, 6):  # CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT
            restore(saved)
            return True
        return False  # Ctrl+C etc.: default handling -> KeyboardInterrupt -> atexit restore
    restore_on_console_close.handler = _HANDLER_ROUTINE(handler)  # keep a reference alive
    _k32.SetConsoleCtrlHandler(restore_on_console_close.handler, True)


class Session:
    """One ON period: applies the layout, optionally launches CS2, keeps the layout in place
    while CS2 runs, and reports when CS2 has closed. Call tick() about once a second."""

    def __init__(self, args, launch=True):
        self.args = args
        self.launch = launch
        self.saved = None
        self.cs2_seen = False
        self.gone_since = None
        self.launch_deadline = None
        self.reapplied = []
        self.gave_up = False

    @property
    def active(self):
        return self.saved is not None

    def start(self):
        self.saved = apply_layout(self.args)
        if self.launch and not cs2_running():
            os.startfile(CS2_STEAM_URI)
            log("Launching CS2...")
            self.launch_deadline = time.time() + self.args.launch_timeout

    def stop(self):
        if self.saved is not None:
            restore(self.saved)
            self.saved = None

    def tick(self):
        """Return None while things are fine, "closed" once CS2 has exited,
        or "timeout" if a launch was requested and CS2 never started."""
        now = time.time()
        if cs2_running():
            if not self.cs2_seen:
                log("CS2 running.")
            self.cs2_seen = True
            self.gone_since = None
            if not self.gave_up:
                self._keep_layout(now)
            return None
        if not self.cs2_seen:
            if self.launch_deadline and now > self.launch_deadline:
                log("CS2 did not start in time.")
                return "timeout"
            return None
        # CS2 sometimes exits and relaunches itself while starting; wait before restoring.
        self.gone_since = self.gone_since or now
        if now - self.gone_since >= self.args.exit_grace:
            log("CS2 closed.")
            return "closed"
        return None

    def _keep_layout(self, now):
        active, state = layout_active(self.args)
        if active:
            return
        self.reapplied = [t for t in self.reapplied if now - t < 60]
        if len(self.reapplied) >= 3:
            log(f"Layout keeps getting reset ({state}). Switch CS2 to Fullscreen Windowed. "
                "Not re-applying again.")
            self.gave_up = True
            return
        log(f"Layout was reset ({state}); re-applying")
        self.reapplied.append(now)
        try:
            apply_layout(self.args)
        except (dc.DisplayConfigError, ValueError) as e:
            log(f"Re-apply failed: {e}")


def cmd_run(args):
    session = Session(args)
    session.start()
    atexit.register(session.stop)
    restore_on_console_close(session.saved)
    log("Normal desktop comes back when CS2 closes (Ctrl+C to restore now).")
    try:
        while session.tick() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def cmd_test(args):
    saved = apply_layout(args)
    try:
        time.sleep(args.seconds)
    finally:
        restore(saved)


def cmd_info(args):
    paths, modes, i, panel, panel_in, region = resolve(args)
    p = paths[i]
    src = modes[p.sourceInfo.source_mode_idx].sourceMode
    img = modes[p.targetInfo.desktop_mode_idx].desktopImageInfo
    print(f"Monitor:  {dc.monitor_name(p.targetInfo)}  {panel[0]}x{panel[1]}  {panel_in:.1f}\"")
    print(f"Desktop:  {src.width}x{src.height}")
    print(f"Image at: {img.DesktopImageRegion!r}")
    l, t, r, b = region
    print(f"A {args.size}\" area would be {r - l}x{b - t} at ({l},{t})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="run", choices=["run", "on", "off", "test", "info"])
    ap.add_argument("--size", type=float, default=24.0, help="virtual monitor diagonal in inches (default 24)")
    ap.add_argument("--res", default="1280x960", help="stretched resolution (default 1280x960)")
    ap.add_argument("--panel", type=float, help="real panel diagonal in inches (default: read from EDID)")
    ap.add_argument("--monitor", help="part of the monitor name, if you have several")
    ap.add_argument("--seconds", type=int, default=15, help="duration for `test`")
    ap.add_argument("--launch-timeout", type=int, default=180, help="seconds to wait for CS2 to start")
    ap.add_argument("--exit-grace", type=int, default=15,
                    help="seconds CS2 must be gone before the desktop is restored")
    args = ap.parse_args()

    try:
        if args.command == "off":
            restore()
        elif args.command == "on":
            apply_layout(args)
        else:
            {"run": cmd_run, "test": cmd_test, "info": cmd_info}[args.command](args)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
