import ctypes
from ctypes import wintypes
import os

user32 = ctypes.WinDLL("user32", use_last_error=True)
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_CHILD = 0x40000000
FRAME_STYLES = WS_CAPTION | 0x00040000 | 0x00020000 | 0x00010000 | 0x00080000
EXTENDED_FRAME_STYLES = 0x00000001 | 0x00000100 | 0x00000200 | 0x00020000
POSITION_FLAGS = 0x0004 | 0x0010 | 0x0020


class WindowPlacement(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT), ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT), ("ptMinPosition", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT), ("rcNormalPosition", wintypes.RECT),
    ]


class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
    ]


get_style = user32.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetWindowLongW
set_style = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
get_style.argtypes = [wintypes.HWND, ctypes.c_int]
get_style.restype = ctypes.c_ssize_t
set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
set_style.restype = ctypes.c_ssize_t
user32.GetForegroundWindow.restype = wintypes.HWND
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WindowPlacement)]
user32.SetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WindowPlacement)]
user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.MonitorFromWindow.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]


class GameWindowManager:
    def __init__(self):
        self._saved = {}

    @staticmethod
    def _process_id(hwnd):
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        return process_id.value

    @staticmethod
    def _set_style(hwnd, index, value):
        ctypes.set_last_error(0)
        previous = set_style(hwnd, index, value)
        if not previous and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())

    @staticmethod
    def _fit(hwnd):
        monitor = user32.MonitorFromWindow(hwnd, 2)
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        bounds = info.rcMonitor
        if not user32.SetWindowPos(hwnd, None, bounds.left, bounds.top,
                                   bounds.right - bounds.left, bounds.bottom - bounds.top,
                                   POSITION_FLAGS):
            raise ctypes.WinError(ctypes.get_last_error())

    def toggle_foreground(self):
        hwnd = user32.GetForegroundWindow()
        if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            raise RuntimeError("Focus the game in Windowed mode, then press Ctrl+Alt+G.")
        process_id = self._process_id(hwnd)
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        style = get_style(hwnd, GWL_STYLE)
        if process_id == os.getpid() or not process_id or style & WS_CHILD or class_name.value in (
            "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "#32768",
        ):
            raise RuntimeError("Focus the game window before pressing Ctrl+Alt+G.")
        if hwnd in self._saved:
            if self._saved[hwnd]["process_id"] == process_id:
                self.restore(hwnd)
                return "Game window restored."
            del self._saved[hwnd]
        if style & WS_CAPTION != WS_CAPTION:
            raise RuntimeError("Choose Windowed in the game first. In Minecraft, press F11, then Ctrl+Alt+G.")
        placement = WindowPlacement()
        placement.length = ctypes.sizeof(placement)
        if not user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            raise ctypes.WinError(ctypes.get_last_error())
        extended_style = get_style(hwnd, GWL_EXSTYLE)
        self._saved[hwnd] = {
            "process_id": process_id, "style": style,
            "extended_style": extended_style, "placement": placement,
        }
        try:
            if placement.showCmd == 3:
                user32.ShowWindow(hwnd, 9)
            self._set_style(hwnd, GWL_STYLE, style & ~(FRAME_STYLES | 0x01000000 | 0x20000000))
            self._set_style(hwnd, GWL_EXSTYLE, extended_style & ~EXTENDED_FRAME_STYLES)
            self._fit(hwnd)
        except Exception:
            self.restore(hwnd)
            raise
        return "Borderless fullscreen enabled. Ctrl+Alt+G restores the game window."

    def restore(self, hwnd):
        saved = self._saved.get(hwnd)
        if saved is None:
            return
        if user32.IsWindow(hwnd) and self._process_id(hwnd) == saved["process_id"]:
            self._set_style(hwnd, GWL_STYLE, saved["style"])
            self._set_style(hwnd, GWL_EXSTYLE, saved["extended_style"])
            if not user32.SetWindowPlacement(hwnd, ctypes.byref(saved["placement"])):
                raise ctypes.WinError(ctypes.get_last_error())
            if not user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, POSITION_FLAGS | 0x0001 | 0x0002):
                raise ctypes.WinError(ctypes.get_last_error())
        del self._saved[hwnd]

    def refit(self):
        for hwnd in list(self._saved):
            if not user32.IsWindow(hwnd) or self._process_id(hwnd) != self._saved[hwnd]["process_id"]:
                del self._saved[hwnd]
            elif not user32.IsIconic(hwnd):
                self._fit(hwnd)

    def restore_all(self):
        for hwnd in list(self._saved):
            try:
                self.restore(hwnd)
            except OSError as error:
                print(f"[Gaming] Could not restore window: {error}")
