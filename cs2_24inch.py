"""Play CS2 stretched on a smaller part of your monitor, with black borders around it.

usage:
    python cs2_24inch.py run    turn on, start CS2, turn off when CS2 closes (default)
    python cs2_24inch.py on     turn on
    python cs2_24inch.py off    back to normal
    python cs2_24inch.py test   turn on for 15 seconds
    python cs2_24inch.py info   show monitor info
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
CS2_URI = "steam://rungameid/730"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cs2_24inch.log")

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE


def log(msg):
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def edid_inches(path):
    req = dc.target_name(path.targetInfo)
    if not req:
        return None
    # \\?\DISPLAY#AUS27B1#5&1234&0&UID4353#{...}
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
    paths, modes = dc.query()
    i = layout.find_path(paths, args.monitor)
    panel = layout.panel_size(paths, modes, i)
    panel_in = args.panel or edid_inches(paths[i])
    if not panel_in:
        raise ValueError("Couldn't read the monitor size, set it with --panel")
    if args.size > panel_in:
        raise ValueError(f"{args.size}\" is bigger than your monitor ({panel_in:.1f}\")")
    region = layout.region_for_size(*panel, panel_in, args.size)
    return paths, modes, i, panel, panel_in, region


def turn_on(args):
    paths, modes, i, panel, panel_in, region = resolve(args)
    w, h = parse_res(args.res)
    new_paths, new_modes = layout.build(paths, modes, i, w, h, region)
    flags = dc.SDC_USE_SUPPLIED_DISPLAY_CONFIG | dc.SDC_VIRTUAL_MODE_AWARE | dc.SDC_ALLOW_CHANGES
    dc.apply(new_paths, new_modes, flags | dc.SDC_VALIDATE)
    # not saved to the display database on purpose, a reboot always resets it
    dc.apply(new_paths, new_modes, flags | dc.SDC_APPLY)
    l, t, r, b = region
    log(f"on: {w}x{h} in {r - l}x{b - t} ({args.size}\" on {panel_in:.1f}\" {panel[0]}x{panel[1]})")
    return paths, modes


def is_on(args):
    paths, modes = dc.query()
    p = paths[layout.find_path(paths, args.monitor)]
    src = modes[p.sourceInfo.source_mode_idx].sourceMode
    img = modes[p.targetInfo.desktop_mode_idx].desktopImageInfo
    sig = modes[p.targetInfo.target_mode_idx].targetMode.targetVideoSignalInfo
    r = img.DesktopImageRegion
    full = (r.left, r.top, r.right, r.bottom) == (0, 0, img.PathSourceSize.x, img.PathSourceSize.y)
    hz = sig.vSyncFreq.Numerator / max(sig.vSyncFreq.Denominator, 1)
    state = (f"desktop {src.width}x{src.height}, image {r!r}, "
             f"signal {sig.activeSize.cx}x{sig.activeSize.cy}@{hz:.2f}")
    return (src.width, src.height) == parse_res(args.res) and not full, state


def turn_off(saved=None):
    if saved:
        try:
            dc.apply(*saved, dc.SDC_USE_SUPPLIED_DISPLAY_CONFIG | dc.SDC_VIRTUAL_MODE_AWARE
                     | dc.SDC_ALLOW_CHANGES | dc.SDC_APPLY)
            log("off")
            return
        except dc.DisplayConfigError as e:
            log(f"couldn't restore saved config ({e}), using windows default")
    rc = dc.user32.SetDisplayConfig(0, None, 0, None, dc.SDC_APPLY | dc.SDC_USE_DATABASE_CURRENT)
    log("off" if rc == 0 else f"off failed: error {rc}")


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]


def cs2_running():
    snap = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    if snap == wintypes.HANDLE(-1).value:
        return True  # better than turning off mid game
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(e)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            if e.szExeFile.lower() == CS2_EXE:
                return True
            ok = kernel32.Process32NextW(snap, ctypes.byref(e))
        return False
    finally:
        kernel32.CloseHandle(snap)


class Session:
    """Turns it on, watches CS2 and puts the layout back if the game resets it.
    Call tick() every second. It returns "closed" when CS2 is gone and
    "timeout" if CS2 never started."""

    def __init__(self, args, launch=True):
        self.args = args
        self.launch = launch
        self.saved = None
        self.cs2_seen = False
        self.gone_since = None
        self.deadline = None
        self.resets = []
        self.gave_up = False

    def start(self):
        self.saved = turn_on(self.args)
        if self.launch and not cs2_running():
            os.startfile(CS2_URI)
            log("starting cs2")
            self.deadline = time.time() + self.args.launch_timeout

    def stop(self):
        if self.saved:
            turn_off(self.saved)
            self.saved = None

    def tick(self):
        now = time.time()
        if cs2_running():
            if not self.cs2_seen:
                log("cs2 is running")
            self.cs2_seen = True
            self.gone_since = None
            if not self.gave_up:
                self.keep_on(now)
            return None
        if not self.cs2_seen:
            if self.deadline and now > self.deadline:
                log("cs2 didn't start")
                return "timeout"
            return None
        # cs2 sometimes closes and reopens itself on launch, so wait a bit
        self.gone_since = self.gone_since or now
        if now - self.gone_since >= self.args.exit_grace:
            log("cs2 closed")
            return "closed"
        return None

    def keep_on(self, now):
        ok, state = is_on(self.args)
        if ok:
            return
        self.resets = [t for t in self.resets if now - t < 60]
        if len(self.resets) >= 3:
            log(f"keeps getting reset ({state}), giving up. try fullscreen windowed")
            self.gave_up = True
            return
        log(f"reset by something ({state}), turning back on")
        self.resets.append(now)
        try:
            turn_on(self.args)
        except (dc.DisplayConfigError, ValueError) as e:
            log(f"couldn't turn back on: {e}")


_HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)


def off_on_console_close(saved):
    # atexit doesn't run when the console window is closed
    def handler(event):
        if event in (2, 5, 6):  # close, logoff, shutdown
            turn_off(saved)
            return True
        return False
    off_on_console_close.handler = _HandlerRoutine(handler)
    kernel32.SetConsoleCtrlHandler(off_on_console_close.handler, True)


def cmd_run(args):
    s = Session(args)
    s.start()
    atexit.register(s.stop)
    off_on_console_close(s.saved)
    log("goes back to normal when cs2 closes, ctrl+c to stop now")
    try:
        while s.tick() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def cmd_test(args):
    saved = turn_on(args)
    try:
        time.sleep(args.seconds)
    finally:
        turn_off(saved)


def cmd_info(args):
    paths, modes, i, panel, panel_in, region = resolve(args)
    p = paths[i]
    src = modes[p.sourceInfo.source_mode_idx].sourceMode
    img = modes[p.targetInfo.desktop_mode_idx].desktopImageInfo
    l, t, r, b = region
    print(f"monitor:  {dc.monitor_name(p.targetInfo)} {panel[0]}x{panel[1]} {panel_in:.1f}\"")
    print(f"desktop:  {src.width}x{src.height}, image {img.DesktopImageRegion!r}")
    print(f"{args.size:g}\" area: {r - l}x{b - t} at ({l},{t})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="run", choices=["run", "on", "off", "test", "info"])
    ap.add_argument("--size", type=float, default=24.0, help="size to play on in inches (default 24)")
    ap.add_argument("--res", default="1280x960", help="stretched resolution (default 1280x960)")
    ap.add_argument("--panel", type=float, help="your monitor size in inches (default: read from monitor)")
    ap.add_argument("--monitor", help="monitor name, if you have more than one")
    ap.add_argument("--seconds", type=int, default=15, help="how long test runs")
    ap.add_argument("--launch-timeout", type=int, default=180)
    ap.add_argument("--exit-grace", type=int, default=15)
    args = ap.parse_args()

    try:
        if args.command == "off":
            turn_off()
        elif args.command == "on":
            turn_on(args)
        else:
            {"run": cmd_run, "test": cmd_test, "info": cmd_info}[args.command](args)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
