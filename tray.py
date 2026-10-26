import pystray
from PIL import Image, ImageDraw
from typing import Callable, Optional

def create_tray_icon_image(enabled: bool = True, opacity: float = 0.45) -> Image.Image:
    """
    Dynamically renders a crisp, high-DPI system tray icon depicting a monitor
    with its bottom half dimmed with a smooth vertical fade.
    """
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Monitor outline
    bezel_color = (220, 225, 230, 255) if enabled else (120, 120, 120, 255)
    draw.rounded_rectangle((6, 8, 58, 48), radius=6, fill=(30, 35, 45, 255), outline=bezel_color, width=3)

    # Monitor stand
    draw.rectangle((28, 48, 36, 56), fill=bezel_color)
    draw.rounded_rectangle((20, 56, 44, 60), radius=2, fill=bezel_color)

    # Screen display area: (9, 11) to (55, 45)
    # Top half (bright)
    top_color = (96, 165, 250, 255) if enabled else (70, 75, 85, 255)
    draw.rectangle((9, 11, 55, 28), fill=top_color)

    # Bottom half (gradient dimmed)
    if enabled:
        # Draw gradient lines in miniature icon
        for y in range(28, 46):
            t = (y - 28) / 17.0
            r = int(96 * (1.0 - t) + 15 * t)
            g = int(165 * (1.0 - t) + 23 * t)
            b = int(250 * (1.0 - t) + 42 * t)
            draw.line([(9, y), (55, y)], fill=(r, g, b, 255))
        # Indicator badge dot in corner
        draw.ellipse((42, 33, 50, 41), fill=(52, 211, 153, 255))
    else:
        draw.rectangle((9, 28, 55, 45), fill=(70, 75, 85, 255))

    return img

class SystemTrayManager:
    """
    Manages the system tray icon, context menu, notifications, and interaction events.
    """
    def __init__(self,
                 get_enabled: Callable[[], bool],
                 on_toggle_enabled: Callable[[], None],
                 get_opacity: Callable[[], float],
                 on_set_opacity: Callable[[float], None],
                 get_blend: Callable[[], float],
                 on_set_blend: Callable[[float], None],
                 get_preset: Callable[[], str],
                 on_set_preset: Callable[[str], None],
                 on_open_region_picker: Callable[[], None],
                 on_show_control_panel: Callable[[], None],
                 get_autostart: Callable[[], bool],
                 on_toggle_autostart: Callable[[], None],
                 on_exit: Callable[[], None]):

        self.get_enabled = get_enabled
        self.on_toggle_enabled = on_toggle_enabled
        self.get_opacity = get_opacity
        self.on_set_opacity = on_set_opacity
        self.get_blend = get_blend
        self.on_set_blend = on_set_blend
        self.get_preset = get_preset
        self.on_set_preset = on_set_preset
        self.on_open_region_picker = on_open_region_picker
        self.on_show_control_panel = on_show_control_panel
        self.get_autostart = get_autostart
        self.on_toggle_autostart = on_toggle_autostart
        self.on_exit = on_exit

        self.icon: Optional[pystray.Icon] = None

    def _build_menu(self) -> pystray.Menu:
        enabled = self.get_enabled()
        current_op = self.get_opacity()
        current_blend = self.get_blend()
        current_preset = self.get_preset()

        status_text = f"LumiDim: {'Active' if enabled else 'Paused'} ({int(current_op * 100)}% Dim, {int(current_blend * 100)}% Blend)"

        # Opacity submenu
        opacity_items = []
        for pct in (10, 20, 30, 40, 50, 60, 70, 80, 90):
            val = pct / 100.0
            is_active = abs(current_op - val) < 0.05
            opacity_items.append(
                pystray.MenuItem(
                    f"{pct}%",
                    lambda item, v=val: self.on_set_opacity(v),
                    checked=lambda item, active=is_active: active
                )
            )

        # Blend Falloff submenu
        blend_items = []
        for label, val in [("25% (Soft Edge)", 0.25), ("50% (Natural Falloff)", 0.50), ("75% (Deep Blend)", 0.75), ("100% (Full Gradient)", 1.00)]:
            is_active = abs(current_blend - val) < 0.08
            blend_items.append(
                pystray.MenuItem(
                    label,
                    lambda item, v=val: self.on_set_blend(v),
                    checked=lambda item, active=is_active: active
                )
            )

        # Preset submenu
        presets = [
            ("Bottom Half (Default)", "bottom_half"),
            ("Top Half", "top_half"),
            ("Bottom Third", "bottom_third"),
            ("Full Screen (Gradient)", "full"),
            ("Full Screen (Uniform)", "full_uniform"),
            ("Custom Selected", "custom"),
        ]
        preset_items = []
        for label, key in presets:
            preset_items.append(
                pystray.MenuItem(
                    label,
                    lambda icon, item, *, preset=key: self.on_set_preset(preset),
                    checked=lambda item, k=key: current_preset == k
                )
            )

        menu = pystray.Menu(
            pystray.MenuItem(status_text, lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Dimmer Enabled",
                lambda: self.on_toggle_enabled(),
                checked=lambda item: self.get_enabled()
            ),
            pystray.MenuItem("Dimming Opacity", pystray.Menu(*opacity_items)),
            pystray.MenuItem("Gradient Blend Height", pystray.Menu(*blend_items)),
            pystray.MenuItem("Dimming Region", pystray.Menu(*preset_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Select Region on Screen...", lambda: self.on_open_region_picker()),
            pystray.MenuItem("Control Panel...", lambda: self.on_show_control_panel(), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows",
                lambda: self.on_toggle_autostart(),
                checked=lambda item: self.get_autostart()
            ),
            pystray.MenuItem("Exit LumiDim", lambda: self.on_exit())
        )
        return menu

    def start(self):
        img = create_tray_icon_image(self.get_enabled(), self.get_opacity())
        self.icon = pystray.Icon(
            "LumiDim",
            img,
            "LumiDim - Regional Screen Dimmer",
            menu=self._build_menu()
        )
        self.icon.run_detached()

    def update(self):
        """Refreshes the tray icon appearance and menu checkmarks."""
        if self.icon:
            self.icon.icon = create_tray_icon_image(self.get_enabled(), self.get_opacity())
            self.icon.menu = self._build_menu()

    def show_notification(self, title: str, message: str):
        """Displays a Windows tray balloon notification."""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None
