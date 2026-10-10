"""Build a display configuration that shows a source resolution inside a smaller,
centered region of the panel (black borders around it)."""
import math

import displaycfg as dc


def region_for_size(panel_w, panel_h, panel_diag_in, target_diag_in, aspect=(16, 9)):
    """Centered rect on the panel that is a 16:9 screen with diagonal target_diag_in,
    so a 24" area looks like a real 24" monitor on any panel (including ultrawides)."""
    ppi = math.hypot(panel_w, panel_h) / panel_diag_in
    ax, ay = aspect
    diag_px = target_diag_in * ppi
    w = min(int(diag_px * ax / math.hypot(ax, ay)), panel_w) // 2 * 2
    h = min(int(diag_px * ay / math.hypot(ax, ay)), panel_h) // 2 * 2
    left = (panel_w - w) // 2
    top = (panel_h - h) // 2
    return left, top, left + w, top + h


def find_path(paths, monitor=None):
    for i, p in enumerate(paths):
        if monitor is None or monitor.lower() in dc.monitor_name(p.targetInfo).lower():
            if not p.flags & dc.PATH_SUPPORT_VIRTUAL_MODE:
                raise RuntimeError("This display path does not support desktop image regions")
            return i
    raise RuntimeError(f"No active display matching {monitor!r}")


def build(paths, modes, path_idx, src_w, src_h, region):
    """Return modified copies of (paths, modes) with the given source size and image region."""
    paths = [dc.PATH_INFO.from_buffer_copy(p) for p in paths]
    modes = [dc.MODE_INFO.from_buffer_copy(m) for m in modes]
    p = paths[path_idx]

    src = modes[p.sourceInfo.source_mode_idx]
    src.sourceMode.width, src.sourceMode.height = src_w, src_h

    # PathSourceSize is the surface scanned out to the panel and must be panel size;
    # the desktop (source mode) is scaled into DesktopImageRegion inside it.
    # Exclusive-fullscreen games shrink it to their own resolution, so always reset it.
    img = modes[p.targetInfo.desktop_mode_idx]
    img.desktopImageInfo.PathSourceSize = dc.POINTL(*panel_size(paths, modes, path_idx))
    img.desktopImageInfo.DesktopImageRegion = dc.RECTL(*region)
    img.desktopImageInfo.DesktopImageClip = dc.RECTL(0, 0, src_w, src_h)
    return paths, modes


def panel_size(paths, modes, path_idx):
    t = modes[paths[path_idx].targetInfo.target_mode_idx].targetMode.targetVideoSignalInfo.activeSize
    return t.cx, t.cy
