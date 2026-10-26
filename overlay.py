import ctypes
from ctypes import wintypes
import threading
import time
import math
from typing import Tuple, Optional, List

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Window styles
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000

# Extended Window styles
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# UpdateLayeredWindow flags
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01

# SetWindowPos flags
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080
HWND_TOPMOST = wintypes.HWND(-1)

# ShowWindow flags
SW_HIDE = 0
SW_SHOWNA = 8

# WinEvent flags
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
    wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD
)

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ('BlendOp', wintypes.BYTE),
        ('BlendFlags', wintypes.BYTE),
        ('SourceConstantAlpha', wintypes.BYTE),
        ('AlphaFormat', wintypes.BYTE),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3),
    ]

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', ctypes.c_void_p),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HICON),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HICON),
    ]

def _generate_gradient_bytes_numpy(
    w: int, h: int,
    max_opacity: float,
    blend_ratio: float = 0.50,
    tint: Tuple[int, int, int] = (0, 0, 0),
    direction: str = "top_to_bottom",
    curve: str = "smooth"
) -> bytes:
    """Fast gradient generator using numpy array vectorization."""
    max_alpha = max(0.0, min(0.95, float(max_opacity))) * 255.0
    blend_h = max(1.0, float(h) * max(0.05, min(1.0, float(blend_ratio))))

    y_coords = np.arange(h, dtype=np.float32)

    if direction == "uniform":
        t = np.ones(h, dtype=np.float32)
    elif direction == "top_to_bottom":
        # 0 at top edge (y=0), gradually darkening down to blend_h
        t = np.clip(y_coords / blend_h, 0.0, 1.0)
    else:
        # 0 at bottom edge (y=h-1), gradually darkening up
        t = np.clip((h - 1.0 - y_coords) / blend_h, 0.0, 1.0)

    if curve == "smooth":
        # Cosine ease: completely removes harsh boundary lines at t=0 and t=1
        t = 0.5 * (1.0 - np.cos(np.pi * t))

    alphas = np.clip(t * max_alpha, 0.0, 255.0).astype(np.uint8)

    # Premultiplied 32-bit ARGB (stored in Windows memory as BGRA bytes)
    r_val, g_val, b_val = tint
    r_pre = ((r_val * alphas.astype(np.uint16)) // 255).astype(np.uint8)
    g_pre = ((g_val * alphas.astype(np.uint16)) // 255).astype(np.uint8)
    b_pre = ((b_val * alphas.astype(np.uint16)) // 255).astype(np.uint8)

    col = np.zeros((h, 1, 4), dtype=np.uint8)
    col[:, 0, 0] = b_pre
    col[:, 0, 1] = g_pre
    col[:, 0, 2] = r_pre
    col[:, 0, 3] = alphas

    # Broadcast identical row pixels across screen width W
    arr = np.repeat(col, w, axis=1)
    return np.ascontiguousarray(arr).tobytes()

def _generate_gradient_bytes_fallback(
    w: int, h: int,
    max_opacity: float,
    blend_ratio: float = 0.50,
    tint: Tuple[int, int, int] = (0, 0, 0),
    direction: str = "top_to_bottom",
    curve: str = "smooth"
) -> bytes:
    """Pure Python fallback for gradient generation if numpy is unavailable."""
    max_alpha = max(0.0, min(0.95, float(max_opacity))) * 255.0
    blend_h = max(1.0, float(h) * max(0.05, min(1.0, float(blend_ratio))))
    r_val, g_val, b_val = tint

    row_bytes = bytearray()
    for y in range(h):
        if direction == "uniform":
            t = 1.0
        elif direction == "top_to_bottom":
            t = min(1.0, max(0.0, y / blend_h))
        else:
            t = min(1.0, max(0.0, (h - 1 - y) / blend_h))

        if curve == "smooth":
            t = 0.5 * (1.0 - math.cos(math.pi * t))

        a = int(t * max_alpha)
        b_pre = (b_val * a) // 255
        g_pre = (g_val * a) // 255
        r_pre = (r_val * a) // 255

        # 4-byte BGRA pixel repeated W times
        pixel = bytes((b_pre, g_pre, r_pre, a))
        row_bytes.extend(pixel * w)

    return bytes(row_bytes)

def generate_gradient_bytes(
    w: int, h: int,
    max_opacity: float,
    blend_ratio: float = 0.50,
    tint: Tuple[int, int, int] = (0, 0, 0),
    direction: str = "top_to_bottom",
    curve: str = "smooth"
) -> bytes:
    if HAVE_NUMPY:
        return _generate_gradient_bytes_numpy(w, h, max_opacity, blend_ratio, tint, direction, curve)
    return _generate_gradient_bytes_fallback(w, h, max_opacity, blend_ratio, tint, direction, curve)


class ScreenDimmerOverlay:
    """
    Native Win32 click-through, always-on-top, regional software dimming overlay
    with smooth linear gradient blending to eliminate any harsh borders or lines.
    Floats persistently above all windows, games, and system elements without
    intercepting mouse clicks or stealing focus.
    """
    _class_registered = False
    _class_name = "LumiDimRegionalGradientOverlayWindow"

    def __init__(self,
                 x: int = 0, y: int = 540,
                 width: int = 1920, height: int = 540,
                 opacity: float = 0.45,
                 blend_ratio: float = 0.50,
                 direction: str = "top_to_bottom",
                 curve: str = "smooth",
                 tint_color: Tuple[int, int, int] = (0, 0, 0),
                 enabled: bool = True):

        self.x = int(x)
        self.y = int(y)
        self.width = max(10, int(width))
        self.height = max(10, int(height))
        self.opacity = max(0.0, min(0.95, float(opacity)))
        self.blend_ratio = max(0.05, min(1.0, float(blend_ratio)))
        self.direction = direction
        self.curve = curve
        self.tint_color = tuple(tint_color)
        self.enabled = bool(enabled)

        self.hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._ready_event = threading.Event()
        self._lock = threading.RLock()

        # Cached GDI resources
        self._hdc_screen: Optional[int] = None
        self._hdc_mem: Optional[int] = None
        self._hbitmap: Optional[int] = None
        self._h_old_bm: Optional[int] = None
        self._p_bits = ctypes.c_void_p()
        self._cur_w = 0
        self._cur_h = 0

        self._start_thread()

    def _register_class(self, hinstance):
        if ScreenDimmerOverlay._class_registered:
            return

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 0
        wc.lpfnWndProc = ctypes.cast(user32.DefWindowProcW, ctypes.c_void_p)
        wc.hInstance = hinstance
        wc.hbrBackground = None  # Transparent background, updated via UpdateLayeredWindow
        wc.lpszClassName = ScreenDimmerOverlay._class_name

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            last_err = kernel32.GetLastError()
            if last_err != 1410:  # ERROR_CLASS_ALREADY_EXISTS
                print(f"[Overlay] RegisterClassExW warning: {last_err}")
        ScreenDimmerOverlay._class_registered = True

    def _start_thread(self):
        self._running = True
        self._thread = threading.Thread(target=self._window_thread, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=3.0)

    def _window_thread(self):
        hinstance = kernel32.GetModuleHandleW(None)
        self._register_class(hinstance)

        ex_style = (
            WS_EX_TOPMOST |
            WS_EX_TRANSPARENT |
            WS_EX_LAYERED |
            WS_EX_TOOLWINDOW |
            WS_EX_NOACTIVATE
        )

        style = WS_POPUP
        if self.enabled:
            style |= WS_VISIBLE

        self.hwnd = user32.CreateWindowExW(
            ex_style,
            ScreenDimmerOverlay._class_name,
            "LumiDim Gradient Overlay",
            style,
            self.x, self.y, self.width, self.height,
            None, None, hinstance, None
        )

        if not self.hwnd:
            err = kernel32.GetLastError()
            print(f"[Overlay] Failed to create overlay window! Error code: {err}")
            self._ready_event.set()
            return

        self._init_gdi_buffers(self.width, self.height)

        # Render initial gradient
        if self.enabled:
            self._render_and_update()
            user32.ShowWindow(self.hwnd, SW_SHOWNA)
            user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST,
                self.x, self.y, self.width, self.height,
                SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        else:
            user32.ShowWindow(self.hwnd, SW_HIDE)

        self._ready_event.set()

        # Install global Windows event hook to immediately catch foreground window activations (0ms delay)
        def _on_win_event(hHook, event, hwnd, idObject, idChild, idEventThread, dwmsEventTime):
            if self.hwnd and self.enabled and hwnd != self.hwnd:
                user32.SetWindowPos(
                    self.hwnd, HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
                )

        self._hook_cb = WINEVENTPROC(_on_win_event)
        self._h_event_hook = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
            None, self._hook_cb, 0, 0, WINEVENT_OUTOFCONTEXT
        )

        # Start fast persistent topmost watchdog thread (40ms interval)
        topmost_watchdog = threading.Thread(target=self._topmost_watchdog_loop, daemon=True)
        topmost_watchdog.start()

        # Standard Win32 message loop
        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup hook and GDI
        if hasattr(self, '_h_event_hook') and self._h_event_hook:
            user32.UnhookWinEvent(self._h_event_hook)
            self._h_event_hook = None

        self._cleanup_gdi_buffers()
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None

    def _init_gdi_buffers(self, w: int, h: int):
        with self._lock:
            self._cleanup_gdi_buffers()
            w = max(10, int(w))
            h = max(10, int(h))
            self._cur_w = w
            self._cur_h = h

            self._hdc_screen = user32.GetDC(None)
            self._hdc_mem = gdi32.CreateCompatibleDC(self._hdc_screen)

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = w
            bmi.bmiHeader.biHeight = -h  # top-down DIB
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0  # BI_RGB

            self._p_bits = ctypes.c_void_p()
            self._hbitmap = gdi32.CreateDIBSection(
                self._hdc_screen,
                ctypes.byref(bmi),
                0,
                ctypes.byref(self._p_bits),
                None,
                0
            )
            if self._hbitmap and self._hdc_mem:
                self._h_old_bm = gdi32.SelectObject(self._hdc_mem, self._hbitmap)

    def _cleanup_gdi_buffers(self):
        if self._hdc_mem and self._h_old_bm:
            gdi32.SelectObject(self._hdc_mem, self._h_old_bm)
            self._h_old_bm = None
        if self._hbitmap:
            gdi32.DeleteObject(self._hbitmap)
            self._hbitmap = None
        if self._hdc_mem:
            gdi32.DeleteDC(self._hdc_mem)
            self._hdc_mem = None
        if self._hdc_screen:
            user32.ReleaseDC(None, self._hdc_screen)
            self._hdc_screen = None
        self._p_bits = ctypes.c_void_p()

    def _render_and_update(self):
        """Generates the linear gradient and updates the layered window."""
        with self._lock:
            if not self.hwnd or not self._running:
                return

            try:
                w = max(10, int(self.width))
                h = max(10, int(self.height))

                # Reallocate GDI DIB section if dimensions changed
                if w != self._cur_w or h != self._cur_h or not self._hbitmap:
                    self._init_gdi_buffers(w, h)

                if not self._p_bits or not self._p_bits.value:
                    return

                # Generate smooth gradient raw bytes
                raw_data = generate_gradient_bytes(
                    w=w, h=h,
                    max_opacity=self.opacity,
                    blend_ratio=self.blend_ratio,
                    tint=self.tint_color,
                    direction=self.direction,
                    curve=self.curve
                )

                # Copy directly into DIB memory
                ctypes.memmove(self._p_bits, raw_data, len(raw_data))

                pt_dst = wintypes.POINT(self.x, self.y)
                size = wintypes.SIZE(w, h)
                pt_src = wintypes.POINT(0, 0)
                blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

                user32.UpdateLayeredWindow(
                    self.hwnd,
                    self._hdc_screen,
                    ctypes.byref(pt_dst),
                    ctypes.byref(size),
                    self._hdc_mem,
                    ctypes.byref(pt_src),
                    0,
                    ctypes.byref(blend),
                    ULW_ALPHA
                )
            except Exception as e:
                print(f"[Overlay] Render error: {e}")

    def _topmost_watchdog_loop(self):
        """
        Fast watchdog (40ms interval) that continuously asserts HWND_TOPMOST
        so that flyouts, popups, and taskbars are dimmed with zero delay.
        """
        while self._running:
            time.sleep(0.04)
            if self.hwnd and self.enabled:
                try:
                    user32.SetWindowPos(
                        self.hwnd, HWND_TOPMOST,
                        0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                    )
                except Exception:
                    pass

    def set_geometry(self, x: int, y: int, width: int, height: int):
        """Dynamically moves and resizes the overlay window."""
        self.x = int(x)
        self.y = int(y)
        self.width = max(10, int(width))
        self.height = max(10, int(height))

        if self.hwnd and self._running and self.enabled:
            self._render_and_update()
            user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST,
                self.x, self.y, self.width, self.height,
                SWP_NOACTIVATE | SWP_SHOWWINDOW
            )

    def set_opacity(self, opacity: float):
        """Dynamically updates the peak dimming opacity (0.0 to 0.95)."""
        self.opacity = max(0.0, min(0.95, float(opacity)))
        if self.hwnd and self._running and self.enabled:
            self._render_and_update()

    def set_blend_ratio(self, blend_ratio: float):
        """Dynamically updates the gradient blend / transition height (0.05 to 1.0)."""
        self.blend_ratio = max(0.05, min(1.0, float(blend_ratio)))
        if self.hwnd and self._running and self.enabled:
            self._render_and_update()

    def set_direction(self, direction: str):
        """Sets dimming direction: 'top_to_bottom', 'bottom_to_top', or 'uniform'."""
        self.direction = direction
        if self.hwnd and self._running and self.enabled:
            self._render_and_update()

    def set_curve(self, curve: str):
        """Sets gradient curve: 'smooth' or 'linear'."""
        self.curve = curve
        if self.hwnd and self._running and self.enabled:
            self._render_and_update()

    def set_tint(self, r: int, g: int, b: int):
        """Updates the overlay tint color."""
        self.tint_color = (int(r), int(g), int(b))
        if self.hwnd and self._running and self.enabled:
            self._render_and_update()

    def set_enabled(self, enabled: bool):
        """Toggles the visibility of the dimming overlay."""
        self.enabled = bool(enabled)
        if self.hwnd and self._running:
            if self.enabled:
                self._render_and_update()
                user32.ShowWindow(self.hwnd, SW_SHOWNA)
                user32.SetWindowPos(
                    self.hwnd, HWND_TOPMOST,
                    self.x, self.y, self.width, self.height,
                    SWP_NOACTIVATE | SWP_SHOWWINDOW
                )
            else:
                user32.ShowWindow(self.hwnd, SW_HIDE)

    def force_topmost(self):
        """Immediately re-asserts topmost z-order."""
        if self.hwnd and self._running and self.enabled:
            user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )

    def destroy(self):
        """Gracefully destroys the overlay window and terminates threads."""
        self._running = False
        if self.hwnd:
            WM_CLOSE = 0x0010
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
