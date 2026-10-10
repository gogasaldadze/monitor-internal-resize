import math

import displaycfg as dc


def region_for_size(panel_w, panel_h, panel_in, size_in):
    # always 16:9 so it matches a real monitor of that size, even on ultrawides
    ppi = math.hypot(panel_w, panel_h) / panel_in
    diag = size_in * ppi
    w = min(int(diag * 16 / math.hypot(16, 9)), panel_w) // 2 * 2
    h = min(int(diag * 9 / math.hypot(16, 9)), panel_h) // 2 * 2
    left = (panel_w - w) // 2
    top = (panel_h - h) // 2
    return left, top, left + w, top + h


def find_path(paths, monitor=None):
    for i, p in enumerate(paths):
        if monitor is None or monitor.lower() in dc.monitor_name(p.targetInfo).lower():
            if not p.flags & dc.PATH_SUPPORT_VIRTUAL_MODE:
                raise RuntimeError("This monitor/driver doesn't support desktop image regions")
            return i
    raise RuntimeError(f"No monitor found matching {monitor!r}")


def panel_size(paths, modes, i):
    t = modes[paths[i].targetInfo.target_mode_idx].targetMode.targetVideoSignalInfo.activeSize
    return t.cx, t.cy


def build(paths, modes, i, res_w, res_h, region):
    paths = [dc.PATH_INFO.from_buffer_copy(p) for p in paths]
    modes = [dc.MODE_INFO.from_buffer_copy(m) for m in modes]
    p = paths[i]

    src = modes[p.sourceInfo.source_mode_idx].sourceMode
    src.width, src.height = res_w, res_h

    # PathSourceSize has to stay at panel size. Fullscreen games change it to their
    # own resolution, so set it back every time.
    img = modes[p.targetInfo.desktop_mode_idx].desktopImageInfo
    img.PathSourceSize = dc.POINTL(*panel_size(paths, modes, i))
    img.DesktopImageRegion = dc.RECTL(*region)
    img.DesktopImageClip = dc.RECTL(0, 0, res_w, res_h)
    return paths, modes
