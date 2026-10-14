import ctypes
from ctypes import wintypes
import threading
import time
from typing import Callable, Dict

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

# Virtual key codes
VK_UP = 0x26
VK_DOWN = 0x28
VK_D = 0x44
VK_P = 0x50

class GlobalHotkeysManager:
    """
    Registers and listens for global Windows hotkeys in a lightweight background thread.
    - Ctrl + Alt + D: Toggle Dimmer on/off
    - Ctrl + Alt + Up: Increase dimming opacity (+5%)
    - Ctrl + Alt + Down: Decrease dimming opacity (-5%)
    - Ctrl + Alt + P: Toggle Control Panel visibility
    """
    def __init__(self,
                 on_toggle: Callable[[], None],
                 on_increase_opacity: Callable[[], None],
                 on_decrease_opacity: Callable[[], None],
                 on_toggle_panel: Callable[[], None]):
        self.callbacks = {
            1: on_toggle,
            2: on_increase_opacity,
            3: on_decrease_opacity,
            4: on_toggle_panel
        }
        self._thread: threading.Thread = None
        self._thread_id: int = 0
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()

        # Register hotkeys on thread queue
        user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_D)
        user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_UP)
        user32.RegisterHotKey(None, 3, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_DOWN)
        user32.RegisterHotKey(None, 4, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_P)

        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret <= 0:
                break
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                cb = self.callbacks.get(hotkey_id)
                if cb:
                    try:
                        cb()
                    except Exception as e:
                        print(f"[Hotkeys] Callback error: {e}")
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Unregister hotkeys
        for i in range(1, 5):
            user32.UnregisterHotKey(None, i)

    def stop(self):
        self._running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
