import tkinter as tk
from typing import Callable, Optional, Dict, Any
from regions import get_virtual_screen, get_monitors

class RegionPickerWindow:
    """
    Interactive full-screen overlay that allows the user to click and drag
    to select any arbitrary screen rectangle for custom dimming.
    """
    def __init__(self, on_selected: Callable[[Dict[str, int]], None], on_cancelled: Optional[Callable[[], None]] = None):
        self.on_selected = on_selected
        self.on_cancelled = on_cancelled

        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.35)
        self.root.configure(bg="#000000")
        self.root.config(cursor="cross")

        # Cover entire virtual screen (all monitors)
        v = get_virtual_screen()
        self.offset_x = v['x']
        self.offset_y = v['y']
        w = v['width']
        h = v['height']

        self.root.geometry(f"{w}x{h}+{self.offset_x}+{self.offset_y}")

        self.canvas = tk.Canvas(self.root, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Instructions banner in center
        cx = w // 2
        self.banner = self.canvas.create_text(
            cx, 80,
            text="Click and drag to select screen area to dim • Press ESC to cancel",
            fill="#38bdf8",
            font=("Segoe UI", 16, "bold")
        )

        self.start_x: Optional[int] = None
        self.start_y: Optional[int] = None
        self.rect_id: Optional[int] = None
        self.border_id: Optional[int] = None
        self.info_text_id: Optional[int] = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", lambda e: self._cancel())

        self.root.focus_force()

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if self.border_id:
            self.canvas.delete(self.border_id)
        if self.info_text_id:
            self.canvas.delete(self.info_text_id)

        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            fill="#3b82f6", outline=""
        )
        self.border_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#60a5fa", width=2
        )
        self.info_text_id = self.canvas.create_text(
            self.start_x + 10, self.start_y - 15,
            text="", fill="#ffffff", font=("Segoe UI", 11, "bold"),
            anchor="w"
        )

    def _on_drag(self, event):
        if self.start_x is None or self.start_y is None:
            return

        cur_x, cur_y = event.x, event.y
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)

        self.canvas.coords(self.rect_id, x1, y1, x2, y2)
        self.canvas.coords(self.border_id, x1, y1, x2, y2)

        w = x2 - x1
        h = y2 - y1
        real_x = self.offset_x + x1
        real_y = self.offset_y + y1

        self.canvas.coords(self.info_text_id, x1 + 8, max(20, y1 - 12))
        self.canvas.itemconfig(self.info_text_id, text=f"{w} × {h} px at ({real_x}, {real_y})")

    def _on_release(self, event):
        if self.start_x is None or self.start_y is None:
            self._cancel()
            return

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        w = x2 - x1
        h = y2 - y1

        # Only accept if at least 20x20 pixels
        if w >= 20 and h >= 20:
            result = {
                "x": self.offset_x + x1,
                "y": self.offset_y + y1,
                "width": w,
                "height": h
            }
            self.root.destroy()
            self.on_selected(result)
        else:
            self._cancel()

    def _cancel(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        if self.on_cancelled:
            self.on_cancelled()
