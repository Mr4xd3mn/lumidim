import ctypes
from ctypes import wintypes
from typing import List, Dict, Any, Tuple, Optional

user32 = ctypes.windll.user32

# Ensure DPI awareness for accurate physical screen metrics
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]

class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', wintypes.DWORD),
        ('szDevice', wintypes.WCHAR * 32)
    ]

MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)

def get_monitors() -> List[Dict[str, Any]]:
    """Returns a list of all detected physical/virtual displays with their pixel coordinates."""
    monitors = []

    def _enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
            r = info.rcMonitor
            is_primary = bool(info.dwFlags & 1)
            monitors.append({
                'name': info.szDevice,
                'is_primary': is_primary,
                'x': r.left,
                'y': r.top,
                'width': r.right - r.left,
                'height': r.bottom - r.top
            })
        return True

    proc = MONITORENUMPROC(_enum_proc)
    user32.EnumDisplayMonitors(None, None, proc, 0)

    # Sort so primary is always index 0
    monitors.sort(key=lambda m: (not m['is_primary'], m['x'], m['y']))

    if not monitors:
        # Fallback to system metrics
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        monitors.append({
            'name': 'Primary Display',
            'is_primary': True,
            'x': 0,
            'y': 0,
            'width': w,
            'height': h
        })

    return monitors

def get_virtual_screen() -> Dict[str, Any]:
    """Returns the bounding rectangle that spans all connected monitors."""
    vx = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return {
        'name': 'All Monitors (Virtual Screen)',
        'is_primary': False,
        'x': vx,
        'y': vy,
        'width': vw,
        'height': vh
    }

def calculate_overlay_geometry(
    preset: str = "bottom_half",
    split_ratio: float = 0.50,
    monitor_index: int = 0,
    custom_rect: Optional[Dict[str, int]] = None
) -> Tuple[int, int, int, int]:
    """
    Calculates the exact (x, y, width, height) rectangle in screen coordinates
    for the dimming overlay based on the requested preset and monitor settings.
    """
    monitors = get_monitors()

    # Determine base screen bounds
    if monitor_index == -1:
        base = get_virtual_screen()
    elif 0 <= monitor_index < len(monitors):
        base = monitors[monitor_index]
    else:
        base = monitors[0]

    bx, by, bw, bh = base['x'], base['y'], base['width'], base['height']

    if preset == "bottom_half":
        # Specifically requirement #1: bottom half (or user-adjusted split ratio)
        h = int(bh * split_ratio)
        y = by + (bh - h)
        return (bx, y, bw, h)

    elif preset == "top_half":
        h = int(bh * split_ratio)
        return (bx, by, bw, h)

    elif preset == "bottom_third":
        h = int(bh * (1.0 / 3.0))
        y = by + (bh - h)
        return (bx, y, bw, h)

    elif preset in ("full", "full_uniform"):
        return (bx, by, bw, bh)

    elif preset == "custom":
        if custom_rect and all(k in custom_rect for k in ("x", "y", "width", "height")):
            return (
                int(custom_rect["x"]),
                int(custom_rect["y"]),
                max(10, int(custom_rect["width"])),
                max(10, int(custom_rect["height"]))
            )
        # Fallback to bottom half if no custom rect saved
        h = int(bh * split_ratio)
        return (bx, by + (bh - h), bw, h)

    else:
        # Default fallback
        h = int(bh * 0.5)
        return (bx, by + (bh - h), bw, h)
