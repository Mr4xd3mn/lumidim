import ctypes
import math
import os
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageDraw, ImageTk

from autostart import is_autostart_enabled, set_autostart
from regions import calculate_overlay_geometry, get_monitors, get_virtual_screen


COLORS = {
    "background": "#171e21", "surface": "#20292d", "border": "#354145",
    "text": "#edf3f2", "muted": "#9ba9ae", "accent": "#37c8b7",
    "accent_dark": "#163b38", "track": "#435054", "hover": "#2b393d",
}


def rounded_points(left, top, right, bottom, radius):
    return (left + radius, top, right - radius, top, right, top,
            right, top + radius, right, bottom - radius, right, bottom,
            right - radius, bottom, left + radius, bottom, left, bottom,
            left, bottom - radius, left, top + radius, left, top)


class Card(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["background"], highlightthickness=0, height=60)
        self.shape = self.create_polygon(rounded_points(1, 1, 440, 59, 12), smooth=True,
                                         fill=COLORS["surface"], outline=COLORS["border"])
        self.body = tk.Frame(self, bg=COLORS["surface"])
        self.body_window = self.create_window(16, 10, window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._resize_body)
        self.bind("<Configure>", self._resize_card)

    def _resize_body(self, event):
        self.configure(height=event.height + 20)

    def _resize_card(self, event):
        self.itemconfigure(self.body_window, width=max(1, event.width - 32))
        self.coords(self.shape, *rounded_points(1, 1, event.width - 1, event.height - 1, 12))


class Switch(tk.Canvas):
    def __init__(self, parent, variable, command):
        super().__init__(parent, width=48, height=30, bg=COLORS["surface"],
                         highlightthickness=0, takefocus=True, cursor="hand2")
        self.variable = variable
        self.command = command
        self.variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Button-1>", lambda event: self.invoke())
        self.bind("<space>", lambda event: self.invoke())
        self.bind("<Return>", lambda event: self.invoke())
        self.bind("<FocusIn>", lambda event: self._draw())
        self.bind("<FocusOut>", lambda event: self._draw())
        self._draw()

    def _draw(self):
        self.delete("all")
        enabled = self.variable.get()
        track = COLORS["accent"] if enabled else COLORS["track"]
        self.create_polygon(rounded_points(1, 4, 47, 27, 12), smooth=True,
                            fill=track, outline=COLORS["text"] if self.focus_get() == self else track)
        position = 27 if enabled else 5
        self.create_oval(position, 7, position + 17, 24, fill=COLORS["text"], outline="")

    def invoke(self):
        self.variable.set(not self.variable.get())
        self.command()


class DimmerSlider(tk.Canvas):
    def __init__(self, parent, variable, command, minimum, maximum):
        super().__init__(parent, height=27, bg=COLORS["surface"],
                         highlightthickness=0, takefocus=True, cursor="hand2")
        self.variable = variable
        self.command = command
        self.minimum = minimum
        self.maximum = maximum
        self.enabled = True
        self.variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", lambda event: self._draw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Left>", lambda event: self._adjust(-0.01))
        self.bind("<Right>", lambda event: self._adjust(0.01))
        self.bind("<Home>", lambda event: self._set_value(self.minimum))
        self.bind("<End>", lambda event: self._set_value(self.maximum))
        self.bind("<FocusIn>", lambda event: self._draw())
        self.bind("<FocusOut>", lambda event: self._draw())

    def _draw(self):
        self.delete("all")
        width = max(32, self.winfo_width())
        fraction = (self.variable.get() - self.minimum) / (self.maximum - self.minimum)
        position = 10 + max(0.0, min(1.0, fraction)) * (width - 20)
        self.create_line(10, 14, width - 10, 14, fill=COLORS["track"], width=5, capstyle="round")
        if self.enabled:
            self.create_line(10, 14, position, 14, fill=COLORS["accent"], width=5, capstyle="round")
        self.create_oval(position - 7, 7, position + 7, 21,
                         fill=COLORS["text"] if self.enabled else COLORS["muted"],
                         outline=COLORS["accent"] if self.focus_get() == self else COLORS["surface"], width=2)

    def _set_value(self, value):
        if not self.enabled:
            return "break"
        value = max(self.minimum, min(self.maximum, value))
        self.variable.set(value)
        self.command(value)
        return "break"

    def _drag(self, event):
        if self.enabled:
            self.focus_set()
            fraction = (event.x - 10) / max(1, self.winfo_width() - 20)
            self._set_value(self.minimum + fraction * (self.maximum - self.minimum))

    def _adjust(self, amount):
        return self._set_value(self.variable.get() + amount)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow", takefocus=enabled)
        self._draw()


def make_landscape(width, height):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for row in range(height):
        fraction = row / max(1, height - 1)
        color = tuple(int(top + (bottom - top) * fraction) for top, bottom in
                      zip((85, 118, 143), (221, 175, 142)))
        draw.line((0, row, width, row), fill=color)
    draw.polygon([(0, height * 0.62), (width * 0.15, height * 0.31),
                  (width * 0.29, height * 0.52), (width * 0.50, height * 0.11),
                  (width * 0.72, height * 0.47), (width * 0.86, height * 0.28),
                  (width, height * 0.59), (width, height), (0, height)], fill="#687c88")
    draw.polygon([(width * 0.34, height * 0.40), (width * 0.50, height * 0.11),
                  (width * 0.64, height * 0.34), (width * 0.53, height * 0.28),
                  (width * 0.49, height * 0.34), (width * 0.45, height * 0.29)], fill="#d9dedb")
    draw.polygon([(0, height * 0.77), (width * 0.18, height * 0.56),
                  (width * 0.37, height * 0.74), (width * 0.63, height * 0.48),
                  (width * 0.83, height * 0.69), (width, height * 0.48),
                  (width, height), (0, height)], fill="#344d59")
    draw.rectangle((0, height * 0.80, width, height), fill="#203640")
    for index in range(18):
        position = int(width * index / 17)
        tree_height = int(height * (0.12 + (index % 4) * 0.025))
        draw.polygon([(position - 9, height * 0.82), (position, height * 0.82 - tree_height),
                      (position + 9, height * 0.82)], fill="#1d3439")
    return image


def dim_preview(image, opacity, blend_ratio, tint, direction, region, curve="smooth"):
    layer = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(layer)
    left, top, width, height = region
    for row in range(max(0, int(top)), min(image.height, math.ceil(top + height))):
        distance = top + height - 1 - row if direction == "bottom_to_top" else row - top
        fraction = 1.0 if direction == "uniform" else max(0.0, min(1.0, distance / max(1, height * blend_ratio)))
        if curve == "smooth":
            fraction = 0.5 * (1 - math.cos(math.pi * fraction))
        alpha = int(max(0.0, min(0.95, opacity)) * 255 * fraction)
        draw.line((int(left), row, math.ceil(left + width) - 1, row), fill=(*tint, alpha))
    return Image.alpha_composite(image.convert("RGBA"), layer)


class ModernControlPanel:
    def __init__(self, config, on_opacity_change, on_blend_change, on_preset_change,
                 on_toggle_enabled, on_tint_change, on_monitor_change,
                 on_launch_picker, on_exit_app):
        self.config = config
        self.on_opacity_change = on_opacity_change
        self.on_blend_change = on_blend_change
        self.on_preset_change = on_preset_change
        self.on_toggle_enabled = on_toggle_enabled
        self.on_tint_change = on_tint_change
        self.on_monitor_change = on_monitor_change
        self.on_launch_picker = on_launch_picker
        self.on_exit_app = on_exit_app
        self._preview_job = None
        self._preview_image = None
        self._settings_window = None
        self._syncing = False
        self._scrollbar_visible = True
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("LumiDim")
        self.root.configure(bg=COLORS["background"])
        self.root.minsize(450, 560)
        self.root.resizable(True, True)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass
        self.enabled_var = tk.BooleanVar(value=config.enabled)
        self.opacity_var = tk.DoubleVar(value=config.opacity)
        self.blend_var = tk.DoubleVar(value=config.blend_ratio)
        self.split_var = tk.DoubleVar(value=config.split_ratio)
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        self._setup_styles()
        self._build_ui()
        self.refresh_from_external()
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Escape>", lambda event: self.hide())
        self._center_window()
        self._style_titlebar()

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Lumi.TCombobox", fieldbackground=COLORS["background"],
                        background=COLORS["surface"], foreground=COLORS["text"],
                        arrowcolor=COLORS["muted"], bordercolor=COLORS["border"],
                        lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=6)
        style.map("Lumi.TCombobox", fieldbackground=[("readonly", COLORS["background"])],
                  foreground=[("readonly", COLORS["text"])], selectbackground=[("readonly", COLORS["background"])],
                  selectforeground=[("readonly", COLORS["text"])])
        style.configure("Lumi.Vertical.TScrollbar", background=COLORS["border"],
                        troughcolor=COLORS["background"], bordercolor=COLORS["background"],
                        lightcolor=COLORS["background"], darkcolor=COLORS["background"],
                        arrowcolor=COLORS["muted"], borderwidth=0, arrowsize=10)
        self.root.option_add("*TCombobox*Listbox.background", COLORS["surface"])
        self.root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent_dark"])

    def _center_window(self):
        width = 480
        height = min(950, max(560, self.root.winfo_screenheight() - 100))
        position_x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        position_y = max(0, (self.root.winfo_screenheight() - height) // 2 - 15)
        self.root.geometry(f"{width}x{height}+{position_x}+{position_y}")

    def _style_titlebar(self):
        try:
            self.root.update_idletasks()
            native = ctypes.windll.user32
            native.GetParent.argtypes = [ctypes.c_void_p]
            native.GetParent.restype = ctypes.c_void_p
            handle = native.GetParent(self.root.winfo_id())
            enabled = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(handle), 20,
                                                     ctypes.byref(enabled), ctypes.sizeof(enabled))
        except (AttributeError, OSError, tk.TclError):
            pass

    def _label(self, parent, text, muted=False, size=10, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"),
                        fg=COLORS["muted"] if muted else COLORS["text"],
                        font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w")

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=COLORS["surface"],
                         fg=COLORS["muted"], activebackground=COLORS["hover"],
                         activeforeground=COLORS["text"], font=("Segoe UI", 9),
                         relief="flat", borderwidth=0, highlightthickness=1,
                         highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
                         cursor="hand2", padx=8, pady=6)

    def _card(self):
        card = Card(self.content)
        card.pack(fill="x", pady=(0, 6))
        return card.body

    def _slider_card(self, title, variable, callback, minimum, maximum):
        body = self._card()
        header = tk.Frame(body, bg=COLORS["surface"])
        header.pack(fill="x")
        self._label(header, title, size=11).pack(side="left")
        value_label = self._label(header, "", size=11)
        value_label.pack(side="right")
        slider = DimmerSlider(body, variable, callback, minimum, maximum)
        slider.pack(fill="x", pady=(3, 0))
        return value_label, slider

    def _build_ui(self):
        header = tk.Frame(self.root, bg=COLORS["background"], padx=22, pady=14)
        header.pack(fill="x")
        sun = self._label(header, "☼", size=25)
        sun.configure(fg=COLORS["accent"])
        sun.pack(side="left", padx=(0, 9))
        self._label(header, "LumiDim", size=20, bold=True).pack(side="left")
        self.status_label = self._label(header, "", size=9)
        self.status_label.pack(side="right")
        footer = tk.Frame(self.root, bg=COLORS["background"], padx=20, pady=12)
        footer.pack(side="bottom", fill="x")
        self._button(footer, "Settings", self._show_settings).pack(side="left")
        self._button(footer, "Minimize to tray", self.hide).pack(side="right")
        scroll_host = tk.Frame(self.root, bg=COLORS["background"])
        scroll_host.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(scroll_host, bg=COLORS["background"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(scroll_host, orient="vertical",
                                      command=self.scroll_canvas.yview, style="Lumi.Vertical.TScrollbar")
        self.scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scroll_canvas.configure(yscrollcommand=self._update_scrollbar)
        self.content = tk.Frame(self.scroll_canvas, bg=COLORS["background"], padx=20)
        self.content_window = self.scroll_canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind("<Configure>", lambda event: self.scroll_canvas.itemconfigure(self.content_window, width=event.width))
        self.root.bind("<MouseWheel>", self._scroll)
        self.root.bind("<Next>", lambda event: self.scroll_canvas.yview_scroll(1, "pages"))
        self.root.bind("<Prior>", lambda event: self.scroll_canvas.yview_scroll(-1, "pages"))
        self.root.bind("<FocusIn>", self._ensure_focus_visible, add="+")
        master = self._card()
        self.power_btn = Switch(master, self.enabled_var, self._on_toggle_power)
        self.power_btn.pack(side="right", padx=(12, 0))
        self._label(master, "Enable dimming", size=11, bold=True).pack(anchor="w")
        self.region_summary = self._label(master, "", muted=True, size=9)
        self.region_summary.pack(anchor="w", pady=(3, 0))
        self.preview_canvas = tk.Canvas(self.content, height=140, bg=COLORS["background"], highlightthickness=0)
        self.preview_canvas.pack(fill="x", pady=(0, 6))
        self.preview_canvas.bind("<Configure>", lambda event: self._schedule_preview())
        self.opacity_val_label, self.opacity_slider = self._slider_card(
            "Dimming", self.opacity_var, self._on_slider_opacity, 0.0, 0.95)
        self.blend_val_label, self.blend_slider = self._slider_card(
            "Fade", self.blend_var, self._on_slider_blend, 0.05, 1.0)
        region = self._card()
        self._label(region, "Region", size=11).pack(anchor="w", pady=(0, 8))
        preset_grid = tk.Frame(region, bg=COLORS["surface"])
        preset_grid.pack(fill="x")
        self.preset_buttons = {}
        presets = (("Bottom", "bottom_half"), ("Top", "top_half"), ("Bottom third", "bottom_third"),
                   ("Full fade", "full"), ("Full even", "full_uniform"), ("Custom…", "custom"))
        for index, (label, key) in enumerate(presets):
            command = self.on_launch_picker if key == "custom" else lambda preset=key: self._set_preset(preset)
            button = self._button(preset_grid, label, command)
            button.grid(row=index // 3, column=index % 3, padx=3, pady=3, sticky="ew")
            preset_grid.grid_columnconfigure(index % 3, weight=1, uniform="preset")
            self.preset_buttons[key] = button
        self.split_frame = tk.Frame(region, bg=COLORS["surface"])
        self._label(self.split_frame, "Coverage", muted=True, size=9).pack(side="left")
        self.split_val_label = self._label(self.split_frame, "", muted=True, size=9)
        self.split_val_label.pack(side="right")
        self.split_slider = DimmerSlider(self.split_frame, self.split_var, self._on_slider_split, 0.1, 0.95)
        self.split_slider.pack(side="left", fill="x", expand=True, padx=10)
        display = self._card()
        monitor_row = tk.Frame(display, bg=COLORS["surface"])
        monitor_row.pack(fill="x")
        self._label(monitor_row, "Monitor", size=10).pack(side="left", padx=(0, 12))
        self.monitor_combo = ttk.Combobox(monitor_row, state="readonly", style="Lumi.TCombobox",
                                          font=("Segoe UI", 9), width=24)
        self.monitor_combo.pack(side="right", fill="x", expand=True)
        self.monitor_combo.bind("<<ComboboxSelected>>", self._on_monitor_select)
        tint_row = tk.Frame(display, bg=COLORS["surface"])
        tint_row.pack(fill="x", pady=(8, 0))
        self._label(tint_row, "Tint", size=10).pack(side="left")
        self.tint_buttons = []
        for name, rgb, swatch_color in (("Black", [0, 0, 0], "#080c0d"),
                                        ("Amber", [35, 20, 5], "#bd872f"),
                                        ("Slate", [10, 20, 35], "#607f98")):
            button = self._button(tint_row, name, lambda color=rgb: self._set_tint(color))
            swatch = Image.new("RGBA", (18, 18))
            ImageDraw.Draw(swatch).ellipse((1, 1, 16, 16), fill=swatch_color, outline=COLORS["muted"])
            button.swatch_image = ImageTk.PhotoImage(swatch, master=self.root)
            button.configure(image=button.swatch_image, compound="left", padx=7)
            button.pack(side="left", padx=(12, 0))
            self.tint_buttons.append((button, rgb))
        startup = self._card()
        self.autostart_cb = Switch(startup, self.autostart_var, self._on_toggle_autostart)
        self.autostart_cb.pack(side="right")
        self._label(startup, "Start with Windows", size=10).pack(side="left", pady=4)

    def _scroll(self, event):
        target = event.widget
        if target.winfo_toplevel() == self.root and not isinstance(target, ttk.Combobox):
            self.scroll_canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"

    def _update_scrollbar(self, first, last):
        self.scrollbar.set(first, last)
        needed = float(last) - float(first) < 0.999
        if needed != self._scrollbar_visible:
            self._scrollbar_visible = needed
            if needed:
                self.scrollbar.pack(side="right", fill="y", before=self.scroll_canvas)
            else:
                self.scrollbar.pack_forget()

    def _ensure_focus_visible(self, event):
        target = event.widget
        ancestor = target
        while ancestor is not None and ancestor != self.content:
            ancestor = getattr(ancestor, "master", None)
        if ancestor != self.content or target == self.content:
            return
        top = target.winfo_rooty() - self.content.winfo_rooty()
        bottom = top + target.winfo_height()
        visible_top = self.scroll_canvas.canvasy(0)
        height = self.scroll_canvas.winfo_height()
        total = max(1, self.content.winfo_reqheight())
        if top < visible_top:
            self.scroll_canvas.yview_moveto(max(0, top - 8) / total)
        elif bottom > visible_top + height:
            self.scroll_canvas.yview_moveto(max(0, bottom - height + 8) / total)

    def _refresh_monitors(self):
        monitors = get_monitors()
        self._monitor_ids = list(range(len(monitors)))
        self.monitor_names = ["Primary display" if monitor["is_primary"] else f"Display {index + 1}"
                              for index, monitor in enumerate(monitors)]
        if len(monitors) > 1 or self.config.monitor_index == -1:
            self._monitor_ids.append(-1)
            self.monitor_names.append("All displays")
        self.monitor_combo.configure(values=self.monitor_names)
        selected = self.config.monitor_index
        self.monitor_combo.current(self._monitor_ids.index(selected) if selected in self._monitor_ids else 0)

    def _schedule_preview(self):
        if self._preview_job is None:
            self._preview_job = self.root.after_idle(self._draw_preview)

    def _draw_preview(self):
        self._preview_job = None
        canvas = self.preview_canvas
        canvas.delete("all")
        width = min(350, max(180, canvas.winfo_width() - 64))
        height = 100
        image = make_landscape(width, height)
        if self.config.enabled:
            monitors = get_monitors()
            selected = self.config.monitor_index
            base = get_virtual_screen() if selected == -1 else monitors[selected if 0 <= selected < len(monitors) else 0]
            region_x, region_y, region_width, region_height = calculate_overlay_geometry(
                self.config.preset, self.config.split_ratio, selected, self.config.custom_rect)
            region = ((region_x - base["x"]) * width / max(1, base["width"]),
                      (region_y - base["y"]) * height / max(1, base["height"]),
                      region_width * width / max(1, base["width"]), region_height * height / max(1, base["height"]))
            direction = "uniform" if self.config.preset == "full_uniform" else "bottom_to_top" if self.config.preset == "top_half" else "top_to_bottom"
            image = dim_preview(image, self.config.opacity, self.config.blend_ratio,
                                tuple(self.config.tint_color), direction, region, self.config.gradient_curve)
        self._preview_image = ImageTk.PhotoImage(image, master=self.root)
        center = canvas.winfo_width() / 2
        left = center - width / 2
        canvas.create_polygon(rounded_points(left - 5, 3, left + width + 5, height + 13, 5),
                              smooth=True, fill="#111719", outline="#6d7c80")
        canvas.create_image(center, 8, image=self._preview_image, anchor="n")
        canvas.create_rectangle(center - 13, height + 14, center + 13, height + 28, fill="#4a575c", outline="")
        canvas.create_line(center - 49, height + 29, center + 49, height + 29, fill="#77858a", width=3, capstyle="round")
        canvas.create_text(center, 136, text="PREVIEW", fill=COLORS["muted"], font=("Segoe UI", 7))

    def _on_toggle_power(self):
        self.config.enabled = self.enabled_var.get()
        self.on_toggle_enabled(self.config.enabled)
        self._sync_controls()

    def _on_slider_opacity(self, value):
        if self._syncing:
            return
        self.config.opacity = float(value)
        self.on_opacity_change(self.config.opacity)
        self._sync_controls()

    def _set_opacity_direct(self, value):
        self._on_slider_opacity(value)

    def _on_slider_blend(self, value):
        if self._syncing:
            return
        self.config.blend_ratio = float(value)
        self.on_blend_change(self.config.blend_ratio)
        self._sync_controls()

    def _set_blend_direct(self, value):
        self._on_slider_blend(value)

    def _set_preset(self, preset_key):
        self.config.preset = preset_key
        self.on_preset_change(preset_key, self.config.split_ratio)
        self._sync_controls()

    def _on_slider_split(self, value):
        if self._syncing:
            return
        self.config.split_ratio = float(value)
        self.on_preset_change(self.config.preset, self.config.split_ratio)
        self._sync_controls()

    def _set_tint(self, rgb):
        self.config.tint_color = rgb
        self.on_tint_change(rgb)
        self._sync_controls()

    def _on_monitor_select(self, event=None):
        index = self.monitor_combo.current()
        if 0 <= index < len(self._monitor_ids):
            self.config.monitor_index = self._monitor_ids[index]
            self.on_monitor_change(self.config.monitor_index)
            self._sync_controls()

    def _on_toggle_autostart(self):
        enabled = self.autostart_var.get()
        if set_autostart(enabled):
            self.config.start_with_windows = enabled
        else:
            self.autostart_var.set(is_autostart_enabled())
            messagebox.showerror("LumiDim", "Couldn't change the Windows startup setting.", parent=self.root)

    def _sync_controls(self):
        self._syncing = True
        try:
            self.enabled_var.set(self.config.enabled)
            self.status_label.configure(text="●  ACTIVE" if self.config.enabled else "●  PAUSED",
                                        fg=COLORS["accent"] if self.config.enabled else COLORS["muted"])
            self.opacity_var.set(self.config.opacity)
            self.blend_var.set(self.config.blend_ratio)
            self.split_var.set(self.config.split_ratio)
            self.opacity_val_label.configure(text=f"{round(self.config.opacity * 100)}%")
            uniform = self.config.preset == "full_uniform"
            self.blend_val_label.configure(text="Not used" if uniform else f"{round(self.config.blend_ratio * 100)}%",
                                           fg=COLORS["muted"] if uniform else COLORS["text"])
            self.blend_slider.set_enabled(not uniform)
            self.split_val_label.configure(text=f"{round(self.config.split_ratio * 100)}%")
            if self.config.preset in ("bottom_half", "top_half"):
                self.split_frame.pack(fill="x", pady=(9, 0))
            else:
                self.split_frame.pack_forget()
            for key, button in self.preset_buttons.items():
                active = key == self.config.preset
                button.configure(bg=COLORS["accent_dark"] if active else COLORS["surface"],
                                 fg=COLORS["accent"] if active else COLORS["muted"],
                                 highlightbackground=COLORS["accent"] if active else COLORS["border"])
            for button, color in self.tint_buttons:
                active = list(color) == list(self.config.tint_color)
                button.configure(bg=COLORS["accent_dark"] if active else COLORS["surface"],
                                 fg=COLORS["accent"] if active else COLORS["muted"],
                                 highlightbackground=COLORS["accent"] if active else COLORS["border"])
            names = {"bottom_half": "Bottom", "top_half": "Top", "bottom_third": "Bottom third",
                     "full": "Full screen · fade", "full_uniform": "Full screen · even", "custom": "Custom region"}
            monitor = self.monitor_combo.get() or "Primary display"
            self.region_summary.configure(text=f"{names.get(self.config.preset, 'Custom region')} · {monitor}")
            self._schedule_preview()
        finally:
            self._syncing = False

    def _show_settings(self):
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            return
        window = tk.Toplevel(self.root)
        self._settings_window = window
        window.title("LumiDim settings")
        window.configure(bg=COLORS["background"])
        window.transient(self.root)
        window.resizable(False, False)
        body = tk.Frame(window, bg=COLORS["background"], padx=24, pady=22)
        body.pack(fill="both", expand=True)
        self._label(body, "Keyboard shortcuts", size=15, bold=True).pack(anchor="w", pady=(0, 14))
        for title, shortcut in (("Toggle dimming", "Ctrl + Alt + D"), ("Adjust dimming", "Ctrl + Alt + ↑ / ↓"),
                                ("Show / hide panel", "Ctrl + Alt + P"), ("Borderless game / restore", "Ctrl + Alt + G")):
            row = tk.Frame(body, bg=COLORS["background"])
            row.pack(fill="x", pady=6)
            self._label(row, title).pack(side="left", padx=(0, 22))
            self._label(row, shortcut, muted=True).pack(side="right")
        hint = self._label(body, "For games, choose Windowed first, then Ctrl + Alt + G.\nExclusive fullscreen isn't supported.", muted=True, size=9)
        hint.pack(anchor="w", pady=(16, 20))
        self._button(body, "Exit LumiDim", self.on_exit_app).pack(side="left")
        self._button(body, "Done", window.destroy).pack(side="right")

    def show(self):
        self.refresh_from_external()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    def toggle_visibility(self):
        if self.root.winfo_viewable():
            self.hide()
        else:
            self.show()

    def refresh_from_external(self):
        self._refresh_monitors()
        self._sync_controls()
