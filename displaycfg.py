# ctypes bindings for QueryDisplayConfig / SetDisplayConfig
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32")

QDC_ONLY_ACTIVE_PATHS = 0x2
QDC_VIRTUAL_MODE_AWARE = 0x10

SDC_APPLY = 0x80
SDC_USE_SUPPLIED_DISPLAY_CONFIG = 0x20
SDC_VALIDATE = 0x40
SDC_USE_DATABASE_CURRENT = 0x0F
SDC_ALLOW_CHANGES = 0x400
SDC_VIRTUAL_MODE_AWARE = 0x8000

PATH_SUPPORT_VIRTUAL_MODE = 0x8
DEVICE_INFO_GET_TARGET_NAME = 2

ERRORS = {
    5: "ERROR_ACCESS_DENIED",
    31: "ERROR_GEN_FAILURE",
    50: "ERROR_NOT_SUPPORTED",
    87: "ERROR_INVALID_PARAMETER",
    1610: "ERROR_BAD_CONFIGURATION",
}


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class RATIONAL(ctypes.Structure):
    _fields_ = [("Numerator", ctypes.c_uint32), ("Denominator", ctypes.c_uint32)]


class POINTL(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECTL(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    def __repr__(self):
        return f"{self.right - self.left}x{self.bottom - self.top} at ({self.left},{self.top})"


class REGION2D(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_uint32), ("cy", ctypes.c_uint32)]


class PATH_SOURCE_INFO(ctypes.Structure):
    _fields_ = [("adapterId", LUID), ("id", ctypes.c_uint32),
                ("modeInfoIdx", ctypes.c_uint32), ("statusFlags", ctypes.c_uint32)]

    @property
    def source_mode_idx(self):  # upper 16 bits in virtual mode aware layout
        return self.modeInfoIdx >> 16


class PATH_TARGET_INFO(ctypes.Structure):
    _fields_ = [("adapterId", LUID), ("id", ctypes.c_uint32), ("modeInfoIdx", ctypes.c_uint32),
                ("outputTechnology", ctypes.c_uint32), ("rotation", ctypes.c_uint32),
                ("scaling", ctypes.c_uint32), ("refreshRate", RATIONAL),
                ("scanLineOrdering", ctypes.c_uint32), ("targetAvailable", wintypes.BOOL),
                ("statusFlags", ctypes.c_uint32)]

    @property
    def desktop_mode_idx(self):
        return self.modeInfoIdx & 0xFFFF

    @property
    def target_mode_idx(self):
        return self.modeInfoIdx >> 16


class PATH_INFO(ctypes.Structure):
    _fields_ = [("sourceInfo", PATH_SOURCE_INFO), ("targetInfo", PATH_TARGET_INFO),
                ("flags", ctypes.c_uint32)]


class VIDEO_SIGNAL_INFO(ctypes.Structure):
    _fields_ = [("pixelRate", ctypes.c_uint64), ("hSyncFreq", RATIONAL), ("vSyncFreq", RATIONAL),
                ("activeSize", REGION2D), ("totalSize", REGION2D),
                ("videoStandard", ctypes.c_uint32), ("scanLineOrdering", ctypes.c_uint32)]


class TARGET_MODE(ctypes.Structure):
    _fields_ = [("targetVideoSignalInfo", VIDEO_SIGNAL_INFO)]


class SOURCE_MODE(ctypes.Structure):
    _fields_ = [("width", ctypes.c_uint32), ("height", ctypes.c_uint32),
                ("pixelFormat", ctypes.c_uint32), ("position", POINTL)]


class DESKTOP_IMAGE_INFO(ctypes.Structure):
    _fields_ = [("PathSourceSize", POINTL), ("DesktopImageRegion", RECTL),
                ("DesktopImageClip", RECTL)]


class _MODE_UNION(ctypes.Union):
    _fields_ = [("targetMode", TARGET_MODE), ("sourceMode", SOURCE_MODE),
                ("desktopImageInfo", DESKTOP_IMAGE_INFO)]


class MODE_INFO(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("infoType", ctypes.c_uint32), ("id", ctypes.c_uint32),
                ("adapterId", LUID), ("u", _MODE_UNION)]


class DEVICE_INFO_HEADER(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint32), ("size", ctypes.c_uint32),
                ("adapterId", LUID), ("id", ctypes.c_uint32)]


class TARGET_DEVICE_NAME(ctypes.Structure):
    _fields_ = [("header", DEVICE_INFO_HEADER), ("flags", ctypes.c_uint32),
                ("outputTechnology", ctypes.c_uint32), ("edidManufactureId", ctypes.c_uint16),
                ("edidProductCodeId", ctypes.c_uint16), ("connectorInstance", ctypes.c_uint32),
                ("monitorFriendlyDeviceName", ctypes.c_wchar * 64),
                ("monitorDevicePath", ctypes.c_wchar * 128)]


assert ctypes.sizeof(PATH_INFO) == 72
assert ctypes.sizeof(MODE_INFO) == 64


class DisplayConfigError(OSError):
    pass


def _check(rc, what):
    if rc != 0:
        raise DisplayConfigError(rc, f"{what} failed: {ERRORS.get(rc, rc)}")


def query():
    flags = QDC_ONLY_ACTIVE_PATHS | QDC_VIRTUAL_MODE_AWARE
    while True:
        n_paths, n_modes = ctypes.c_uint32(), ctypes.c_uint32()
        _check(user32.GetDisplayConfigBufferSizes(flags, ctypes.byref(n_paths), ctypes.byref(n_modes)),
               "GetDisplayConfigBufferSizes")
        paths = (PATH_INFO * n_paths.value)()
        modes = (MODE_INFO * n_modes.value)()
        rc = user32.QueryDisplayConfig(flags, ctypes.byref(n_paths), paths,
                                       ctypes.byref(n_modes), modes, None)
        if rc == 122:  # config changed in between, try again
            continue
        _check(rc, "QueryDisplayConfig")
        return paths[:n_paths.value], modes[:n_modes.value]


def apply(paths, modes, flags):
    p = (PATH_INFO * len(paths))(*paths)
    m = (MODE_INFO * len(modes))(*modes)
    _check(user32.SetDisplayConfig(len(paths), p, len(modes), m, flags), "SetDisplayConfig")


def target_name(target):
    req = TARGET_DEVICE_NAME()
    req.header.type = DEVICE_INFO_GET_TARGET_NAME
    req.header.size = ctypes.sizeof(req)
    req.header.adapterId = target.adapterId
    req.header.id = target.id
    if user32.DisplayConfigGetDeviceInfo(ctypes.byref(req)) != 0:
        return None
    return req


def monitor_name(target):
    req = target_name(target)
    return req.monitorFriendlyDeviceName if req else "?"
