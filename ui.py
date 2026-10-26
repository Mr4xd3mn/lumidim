import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import Callable, Dict, Any, List
from regions import get_monitors
from autostart import is_autostart_enabled, set_autostart

class ModernControlPanel:
    """
    Sleek, minimalist dark-themed floating control panel for LumiDim.
    Provides real-time sliders for dimming opacity and gradient blend height,
    preset region selection, split height adjustment, monitor targeting,
    tone modes, and Windows autostart toggle.
    """
    def __init__(self,
                 config,
                 on_opacity_change: Callable[[float], None],
                 on_blend_change: Callable[[float], None],
                 on_preset_change: Callable[[str, float], None],
                 on_toggle_enabled: Callable[[bool], None],
                 on_tint_change: Callable[[List[int]], None],
                 on_monitor_change: Callable[[int], None],
                 on_launch_picker: Callable[[], None],
                 on_exit_app: Callable[[], None]):

        self.config = config
        self.on_opacity_change = on_opacity_change
        self.on_blend_change = on_blend_change
        self.on_preset_change = on_preset_change
        self.on_toggle_enabled = on_toggle_enabled
        self.on_tint_change = on_tint_change
        self.on_monitor_change = on_monitor_change
        self.on_launch_picker = on_launch_picker
        self.on_exit_app = on_exit_app

        self.root = tk.Tk()
        self.root.title("LumiDim — Regional Screen Dimmer")
        self.root.geometry("480x740")
        self.root.minsize(450, 700)
        self.root.configure(bg="#0f172a")

        # Load window icon if present
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Configure window icon and styles
        self._setup_styles()
        self._build_ui()

        # Handle close button (minimize to tray)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        # Center on screen
        self._center_window()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        bg_dark = "#0f172a"
        card_bg = "#1e293b"

        style.configure("TFrame", background=bg_dark)
        style.configure("Card.TFrame", background=card_bg, relief="flat")
        style.configure("TLabel", background=bg_dark, foreground="#f8fafc", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=card_bg, foreground="#f8fafc", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg_dark, foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("CardMuted.TLabel", background=card_bg, foreground="#94a3b8", font=("Segoe UI", 9))

        # Slider style
        style.configure("Horizontal.TScale",
                        background=card_bg,
                        troughcolor="#334155",
                        sliderthickness=18)

        # Combobox style
        style.configure("TCombobox",
                        fieldbackground="#334155",
                        background="#475569",
                        foreground="#ffffff",
                        darkcolor="#1e293b",
                        lightcolor="#1e293b")

    def _center_window(self):
        self.root.update_idletasks()
        w = 480
        h = 740
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(50, (sw - w) // 2)
        y = max(50, (sh - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        main_container = tk.Frame(self.root, bg="#0f172a", padx=20, pady=16)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Header with App Title & Master Power Toggle
        header_frame = tk.Frame(main_container, bg="#0f172a")
        header_frame.pack(fill=tk.X, pady=(0, 14))

        title_box = tk.Frame(header_frame, bg="#0f172a")
        title_box.pack(side=tk.LEFT)

        app_title = tk.Label(title_box, text="LumiDim", font=("Segoe UI", 18, "bold"), fg="#38bdf8", bg="#0f172a")
        app_title.pack(anchor="w")

        app_subtitle = tk.Label(title_box, text="Seamless Gradient Screen Dimmer", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        app_subtitle.pack(anchor="w")

        # Master Power Toggle Button
        self.power_btn = tk.Button(
            header_frame,
            text="ON" if self.config.enabled else "OFF",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#10b981" if self.config.enabled else "#64748b",
            activeforeground="#ffffff",
            activebackground="#059669" if self.config.enabled else "#475569",
            relief="flat",
            padx=16,
            pady=4,
            cursor="hand2",
            command=self._on_toggle_power
        )
        self.power_btn.pack(side=tk.RIGHT)

        # 2. Peak Dimming Opacity Card
        opacity_card = tk.Frame(main_container, bg="#1e293b", padx=16, pady=12, relief="flat", highlightbackground="#334155", highlightthickness=1)
        opacity_card.pack(fill=tk.X, pady=(0, 12))

        op_header = tk.Frame(opacity_card, bg="#1e293b")
        op_header.pack(fill=tk.X, pady=(0, 4))

        tk.Label(op_header, text="PEAK DIMMING OPACITY", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#1e293b").pack(side=tk.LEFT)
        self.opacity_val_label = tk.Label(op_header, text=f"{int(self.config.opacity * 100)}%", font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#1e293b")
        self.opacity_val_label.pack(side=tk.RIGHT)

        # Smooth Opacity Slider
        self.opacity_var = tk.DoubleVar(value=self.config.opacity)
        self.opacity_slider = ttk.Scale(
            opacity_card,
            from_=0.0,
            to=0.95,
            orient="horizontal",
            variable=self.opacity_var,
            command=self._on_slider_opacity
        )
        self.opacity_slider.pack(fill=tk.X, pady=(2, 8))

        # Quick preset pills for opacity
        pills_frame = tk.Frame(opacity_card, bg="#1e293b")
        pills_frame.pack(fill=tk.X)
        for pct in (20, 35, 50, 65, 80):
            val = pct / 100.0
            btn = tk.Button(
                pills_frame,
                text=f"{pct}%",
                font=("Segoe UI", 8, "bold"),
                fg="#cbd5e1",
                bg="#334155",
                activeforeground="#ffffff",
                activebackground="#475569",
                relief="flat",
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda v=val: self._set_opacity_direct(v)
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # 3. Smooth Gradient Blend / Falloff Card (Requirement #1, #2, #3)
        blend_card = tk.Frame(main_container, bg="#1e293b", padx=16, pady=12, relief="flat", highlightbackground="#334155", highlightthickness=1)
        blend_card.pack(fill=tk.X, pady=(0, 12))

        blend_header = tk.Frame(blend_card, bg="#1e293b")
        blend_header.pack(fill=tk.X, pady=(0, 2))

        tk.Label(blend_header, text="GRADIENT BLEND & FALLOFF", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#1e293b").pack(side=tk.LEFT)
        self.blend_val_label = tk.Label(blend_header, text=f"{int(self.config.blend_ratio * 100)}% Blend Height", font=("Segoe UI", 11, "bold"), fg="#a78bfa", bg="#1e293b")
        self.blend_val_label.pack(side=tk.RIGHT)

        # Explanatory subtitle
        tk.Label(
            blend_card,
            text="Fades smoothly from 0% alpha at the boundary to eliminate harsh lines and match natural backlight falloff.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#1e293b",
            wraplength=410,
            justify="left"
        ).pack(anchor="w", pady=(0, 6))

        # Smooth Blend Slider
        self.blend_var = tk.DoubleVar(value=self.config.blend_ratio)
        self.blend_slider = ttk.Scale(
            blend_card,
            from_=0.05,
            to=1.00,
            orient="horizontal",
            variable=self.blend_var,
            command=self._on_slider_blend
        )
        self.blend_slider.pack(fill=tk.X, pady=(2, 8))

        # Blend preset pills
        blend_pills_frame = tk.Frame(blend_card, bg="#1e293b")
        blend_pills_frame.pack(fill=tk.X)
        blend_presets = [
            ("25% Soft", 0.25),
            ("50% Natural", 0.50),
            ("75% Deep", 0.75),
            ("100% Full Fade", 1.00)
        ]
        for label, val in blend_presets:
            btn = tk.Button(
                blend_pills_frame,
                text=label,
                font=("Segoe UI", 8),
                fg="#e2e8f0",
                bg="#334155",
                activeforeground="#ffffff",
                activebackground="#475569",
                relief="flat",
                padx=6,
                pady=2,
                cursor="hand2",
                command=lambda v=val: self._set_blend_direct(v)
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # 4. Regional Coverage Card
        region_card = tk.Frame(main_container, bg="#1e293b", padx=16, pady=12, relief="flat", highlightbackground="#334155", highlightthickness=1)
        region_card.pack(fill=tk.X, pady=(0, 12))

        tk.Label(region_card, text="DIMMED REGION", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#1e293b").pack(anchor="w", pady=(0, 6))

        # Preset Buttons Grid
        presets_grid = tk.Frame(region_card, bg="#1e293b")
        presets_grid.pack(fill=tk.X, pady=(0, 8))

        self.preset_buttons: Dict[str, tk.Button] = {}
        preset_defs = [
            ("Bottom Half (Default)", "bottom_half"),
            ("Top Half", "top_half"),
            ("Bottom 1/3", "bottom_third"),
            ("Full Screen (Gradient)", "full"),
            ("Full Screen (Uniform)", "full_uniform"),
        ]

        for idx, (label, key) in enumerate(preset_defs):
            is_active = (self.config.preset == key)
            btn = tk.Button(
                presets_grid,
                text=label,
                font=("Segoe UI", 9, "bold" if is_active else "normal"),
                fg="#ffffff" if is_active else "#94a3b8",
                bg="#2563eb" if is_active else "#334155",
                activeforeground="#ffffff",
                activebackground="#1d4ed8",
                relief="flat",
                pady=5,
                cursor="hand2",
                command=lambda k=key: self._set_preset(k)
            )
            btn.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=3, pady=2)
            presets_grid.grid_columnconfigure(idx % 2, weight=1)
            self.preset_buttons[key] = btn

        # Split Ratio Slider (for bottom/top half)
        self.split_frame = tk.Frame(region_card, bg="#1e293b")
        self.split_frame.pack(fill=tk.X, pady=(2, 6))

        split_label_row = tk.Frame(self.split_frame, bg="#1e293b")
        split_label_row.pack(fill=tk.X)
        tk.Label(split_label_row, text="Split Height Coverage", font=("Segoe UI", 8), fg="#cbd5e1", bg="#1e293b").pack(side=tk.LEFT)
        self.split_val_label = tk.Label(split_label_row, text=f"{int(self.config.split_ratio * 100)}%", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b")
        self.split_val_label.pack(side=tk.RIGHT)

        self.split_var = tk.DoubleVar(value=self.config.split_ratio)
        self.split_slider = ttk.Scale(
            self.split_frame,
            from_=0.10,
            to=0.90,
            orient="horizontal",
            variable=self.split_var,
            command=self._on_slider_split
        )
        self.split_slider.pack(fill=tk.X, pady=(2, 0))

        # Interactive Screen Selector Button
        picker_btn = tk.Button(
            region_card,
            text="🎯 Drag & Select Custom Region on Screen...",
            font=("Segoe UI", 9, "bold"),
            fg="#f8fafc",
            bg="#0f766e",
            activeforeground="#ffffff",
            activebackground="#115e59",
            relief="flat",
            pady=5,
            cursor="hand2",
            command=self.on_launch_picker
        )
        picker_btn.pack(fill=tk.X, pady=(4, 0))

        # 5. Monitor & Dimmer Tone Section
        display_card = tk.Frame(main_container, bg="#1e293b", padx=16, pady=10, relief="flat", highlightbackground="#334155", highlightthickness=1)
        display_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(display_card, text="TARGET DISPLAY & TONE", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#1e293b").pack(anchor="w", pady=(0, 4))

        self.monitor_names = ["Primary Display"]
        monitors = get_monitors()
        if len(monitors) > 1:
            self.monitor_names = [f"Display {i+1} ({m['width']}x{m['height']}){' [Primary]' if m['is_primary'] else ''}" for i, m in enumerate(monitors)]
            self.monitor_names.append("Span All Displays (Virtual Screen)")

        self.monitor_combo = ttk.Combobox(
            display_card,
            values=self.monitor_names,
            state="readonly",
            font=("Segoe UI", 9)
        )
        cur_idx = self.config.monitor_index
        if cur_idx == -1 and len(self.monitor_names) > len(monitors):
            self.monitor_combo.current(len(self.monitor_names) - 1)
        elif 0 <= cur_idx < len(self.monitor_names):
            self.monitor_combo.current(cur_idx)
        else:
            self.monitor_combo.current(0)

        self.monitor_combo.pack(fill=tk.X, pady=(0, 6))
        self.monitor_combo.bind("<<ComboboxSelected>>", self._on_monitor_select)

        # Tone selector buttons
        tint_row = tk.Frame(display_card, bg="#1e293b")
        tint_row.pack(fill=tk.X)

        tk.Label(tint_row, text="Tone:", font=("Segoe UI", 8), fg="#cbd5e1", bg="#1e293b").pack(side=tk.LEFT)

        tint_options = [
            ("Black (Pure Dimmer)", [0, 0, 0]),
            ("Warm Amber (Night Light)", [35, 20, 5]),
            ("Cool Slate", [10, 20, 35])
        ]
        self.tint_buttons = []
        for name, rgb in tint_options:
            is_active = (self.config.tint_color == rgb)
            btn = tk.Button(
                tint_row,
                text=name,
                font=("Segoe UI", 8),
                fg="#ffffff" if is_active else "#94a3b8",
                bg="#1e40af" if is_active else "#334155",
                relief="flat",
                padx=6,
                pady=2,
                cursor="hand2",
                command=lambda c=rgb: self._set_tint(c)
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.tint_buttons.append((btn, rgb))

        # 6. Options & Hotkeys Note
        options_frame = tk.Frame(main_container, bg="#0f172a")
        options_frame.pack(fill=tk.X, pady=(0, 6))

        # Windows Startup Checkbox
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        self.autostart_cb = tk.Checkbutton(
            options_frame,
            text="Run automatically on Windows startup (minimized to tray)",
            variable=self.autostart_var,
            font=("Segoe UI", 9),
            fg="#e2e8f0",
            bg="#0f172a",
            activeforeground="#ffffff",
            activebackground="#0f172a",
            selectcolor="#1e293b",
            cursor="hand2",
            command=self._on_toggle_autostart
        )
        self.autostart_cb.pack(anchor="w")

        # Hotkeys Hint Card
        hotkey_hint = tk.Label(
            options_frame,
            text="⚡ Shortcuts: Ctrl+Alt+D (Toggle)  •  Ctrl+Alt+↑/↓ (Opacity ±5%)  •  Ctrl+Alt+P (Panel)",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#0f172a"
        )
        hotkey_hint.pack(anchor="w", pady=(4, 0))

        # 7. Bottom Action Buttons
        footer = tk.Frame(main_container, bg="#0f172a")
        footer.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        min_btn = tk.Button(
            footer,
            text="Minimize to System Tray",
            font=("Segoe UI", 9, "bold"),
            fg="#f8fafc",
            bg="#334155",
            activeforeground="#ffffff",
            activebackground="#475569",
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self.hide
        )
        min_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        exit_btn = tk.Button(
            footer,
            text="Exit App",
            font=("Segoe UI", 9),
            fg="#fca5a5",
            bg="#451a1a",
            activeforeground="#ffffff",
            activebackground="#7f1d1d",
            relief="flat",
            pady=6,
            cursor="hand2",
            command=self.on_exit_app
        )
        exit_btn.pack(side=tk.RIGHT, padx=(5, 0))

    def _on_toggle_power(self):
        new_state = not self.config.enabled
        self.config.enabled = new_state
        self.power_btn.config(
            text="ON" if new_state else "OFF",
            bg="#10b981" if new_state else "#64748b",
            activebackground="#059669" if new_state else "#475569"
        )
        self.on_toggle_enabled(new_state)

    def _on_slider_opacity(self, val):
        fval = float(val)
        self.opacity_val_label.config(text=f"{int(fval * 100)}%")
        self.config.opacity = fval
        self.on_opacity_change(fval)

    def _set_opacity_direct(self, val: float):
        self.opacity_var.set(val)
        self._on_slider_opacity(val)

    def _on_slider_blend(self, val):
        fval = float(val)
        self.blend_val_label.config(text=f"{int(fval * 100)}% Blend Height")
        self.config.blend_ratio = fval
        self.on_blend_change(fval)

    def _set_blend_direct(self, val: float):
        self.blend_var.set(val)
        self._on_slider_blend(val)

    def _set_preset(self, preset_key: str):
        self.config.preset = preset_key
        for key, btn in self.preset_buttons.items():
            if key == preset_key:
                btn.config(bg="#2563eb", fg="#ffffff", font=("Segoe UI", 9, "bold"))
            else:
                btn.config(bg="#334155", fg="#94a3b8", font=("Segoe UI", 9, "normal"))

        # Show split slider if bottom_half or top_half
        if preset_key in ("bottom_half", "top_half"):
            self.split_frame.pack(fill=tk.X, pady=(2, 6))
        else:
            self.split_frame.pack_forget()

        self.on_preset_change(preset_key, self.config.split_ratio)

    def _on_slider_split(self, val):
        fval = float(val)
        self.split_val_label.config(text=f"{int(fval * 100)}%")
        self.config.split_ratio = fval
        self.on_preset_change(self.config.preset, fval)

    def _set_tint(self, rgb: List[int]):
        self.config.tint_color = rgb
        for btn, b_rgb in self.tint_buttons:
            if b_rgb == rgb:
                btn.config(bg="#1e40af", fg="#ffffff")
            else:
                btn.config(bg="#334155", fg="#94a3b8")
        self.on_tint_change(rgb)

    def _on_monitor_select(self, event):
        idx = self.monitor_combo.current()
        monitors = get_monitors()
        if len(self.monitor_names) > len(monitors) and idx == len(self.monitor_names) - 1:
            mon_id = -1  # Span all
        else:
            mon_id = idx
        self.config.monitor_index = mon_id
        self.on_monitor_change(mon_id)

    def _on_toggle_autostart(self):
        val = self.autostart_var.get()
        set_autostart(val)
        self.config.start_with_windows = val

    def show(self):
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
        """Called when settings are changed via Tray or Hotkeys."""
        self.power_btn.config(
            text="ON" if self.config.enabled else "OFF",
            bg="#10b981" if self.config.enabled else "#64748b"
        )
        self.opacity_var.set(self.config.opacity)
        self.opacity_val_label.config(text=f"{int(self.config.opacity * 100)}%")

        self.blend_var.set(self.config.blend_ratio)
        self.blend_val_label.config(text=f"{int(self.config.blend_ratio * 100)}% Blend Height")

        self.split_var.set(self.config.split_ratio)
        self.split_val_label.config(text=f"{int(self.config.split_ratio * 100)}%")

        for key, btn in self.preset_buttons.items():
            if key == self.config.preset:
                btn.config(bg="#2563eb", fg="#ffffff", font=("Segoe UI", 9, "bold"))
            else:
                btn.config(bg="#334155", fg="#94a3b8", font=("Segoe UI", 9, "normal"))

        for btn, b_rgb in self.tint_buttons:
            if b_rgb == self.config.tint_color:
                btn.config(bg="#1e40af", fg="#ffffff")
            else:
                btn.config(bg="#334155", fg="#94a3b8")
