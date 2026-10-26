import sys
import os
import argparse
import ctypes
from ctypes import wintypes

from config import Config
from regions import calculate_overlay_geometry
from overlay import ScreenDimmerOverlay
from autostart import is_autostart_enabled, set_autostart
from hotkeys import GlobalHotkeysManager
from tray import SystemTrayManager
from ui import ModernControlPanel
from region_picker import RegionPickerWindow

# Single instance enforcement via Windows Named Mutex
kernel32 = ctypes.windll.kernel32
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Global\\LumiDimRegionalDimmerMutex"

class LumiDimApp:
    def __init__(self, start_minimized: bool = False):
        self.config = Config()
        self.start_minimized = start_minimized
        self.picker_window = None

        # 1. Calculate initial geometry
        x, y, w, h = calculate_overlay_geometry(
            preset=self.config.preset,
            split_ratio=self.config.split_ratio,
            monitor_index=self.config.monitor_index,
            custom_rect=self.config.custom_rect
        )

        direction = self._direction_for_preset(self.config.preset)

        # 2. Initialize native Win32 gradient dimmer overlay
        self.overlay = ScreenDimmerOverlay(
            x=x, y=y, width=w, height=h,
            opacity=self.config.opacity,
            blend_ratio=self.config.blend_ratio,
            direction=direction,
            curve=self.config.gradient_curve,
            tint_color=self.config.tint_color,
            enabled=self.config.enabled
        )

        # 3. Create UI Control Panel
        self.panel = ModernControlPanel(
            config=self.config,
            on_opacity_change=self.handle_opacity_change,
            on_blend_change=self.handle_blend_change,
            on_preset_change=self.handle_preset_change,
            on_toggle_enabled=self.handle_toggle_enabled,
            on_tint_change=self.handle_tint_change,
            on_monitor_change=self.handle_monitor_change,
            on_launch_picker=self.handle_launch_picker,
            on_exit_app=self.handle_exit
        )

        # 4. Initialize System Tray
        self.tray = SystemTrayManager(
            get_enabled=lambda: self.config.enabled,
            on_toggle_enabled=lambda: self.panel.root.after(0, self._threadsafe_toggle_enabled),
            get_opacity=lambda: self.config.opacity,
            on_set_opacity=lambda val: self.panel.root.after(0, lambda: self._threadsafe_set_opacity(val)),
            get_blend=lambda: self.config.blend_ratio,
            on_set_blend=lambda val: self.panel.root.after(0, lambda: self._threadsafe_set_blend(val)),
            get_preset=lambda: self.config.preset,
            on_set_preset=lambda p: self.panel.root.after(0, lambda: self._threadsafe_set_preset(p)),
            on_open_region_picker=lambda: self.panel.root.after(0, self.handle_launch_picker),
            on_show_control_panel=lambda: self.panel.root.after(0, self.panel.show),
            get_autostart=is_autostart_enabled,
            on_toggle_autostart=lambda: self.panel.root.after(0, self._threadsafe_toggle_autostart),
            on_exit=lambda: self.panel.root.after(0, self.handle_exit)
        )
        self.tray.start()

        # 5. Initialize Global Hotkeys
        self.hotkeys = GlobalHotkeysManager(
            on_toggle=lambda: self.panel.root.after(0, self._threadsafe_toggle_enabled),
            on_increase_opacity=lambda: self.panel.root.after(0, self._threadsafe_adjust_opacity, 0.05),
            on_decrease_opacity=lambda: self.panel.root.after(0, self._threadsafe_adjust_opacity, -0.05),
            on_toggle_panel=lambda: self.panel.root.after(0, self.panel.toggle_visibility)
        )
        if self.config.hotkeys_enabled:
            self.hotkeys.start()

        # Check startup mode
        if self.start_minimized:
            self.panel.hide()
        else:
            self.panel.show()

    # --- Event Handlers & Safe Thread Dispatches ---

    @staticmethod
    def _direction_for_preset(preset: str):
        if preset == "full_uniform":
            return "uniform"
        return "bottom_to_top" if preset == "top_half" else "top_to_bottom"

    def _threadsafe_toggle_enabled(self):
        new_state = not self.config.enabled
        self.config.enabled = new_state
        self.handle_toggle_enabled(new_state)
        self.panel.refresh_from_external()
        self.tray.update()

    def _threadsafe_set_opacity(self, val: float):
        self.config.opacity = val
        self.handle_opacity_change(val)
        self.panel.refresh_from_external()
        self.tray.update()

    def _threadsafe_set_blend(self, val: float):
        self.config.blend_ratio = val
        self.handle_blend_change(val)
        self.panel.refresh_from_external()
        self.tray.update()

    def _threadsafe_adjust_opacity(self, delta: float):
        new_val = max(0.0, min(0.95, self.config.opacity + delta))
        self._threadsafe_set_opacity(new_val)

    def _threadsafe_set_preset(self, preset: str):
        self.config.preset = preset
        self.handle_preset_change(preset, self.config.split_ratio)
        self.panel.refresh_from_external()
        self.tray.update()

    def _threadsafe_toggle_autostart(self):
        new_state = not is_autostart_enabled()
        set_autostart(new_state)
        self.config.start_with_windows = new_state
        self.panel.autostart_var.set(new_state)
        self.tray.update()

    def _schedule_tray_update(self):
        """Debounces tray icon updates so dragging sliders does not flood the Windows Shell."""
        if hasattr(self, '_tray_job') and self._tray_job:
            try:
                self.panel.root.after_cancel(self._tray_job)
            except Exception:
                pass
        self._tray_job = self.panel.root.after(300, self._do_tray_update)

    def _do_tray_update(self):
        self._tray_job = None
        self.tray.update()

    def handle_opacity_change(self, opacity: float):
        self.overlay.set_opacity(opacity)
        self.config.opacity = opacity
        self._schedule_tray_update()

    def handle_blend_change(self, blend_ratio: float):
        self.overlay.set_blend_ratio(blend_ratio)
        self.config.blend_ratio = blend_ratio
        self._schedule_tray_update()

    def handle_preset_change(self, preset: str, split_ratio: float):
        self.config.preset = preset
        self.config.split_ratio = split_ratio
        direction = self._direction_for_preset(preset)
        self.overlay.set_direction(direction)

        x, y, w, h = calculate_overlay_geometry(
            preset=preset,
            split_ratio=split_ratio,
            monitor_index=self.config.monitor_index,
            custom_rect=self.config.custom_rect
        )
        self.overlay.set_geometry(x, y, w, h)
        self._schedule_tray_update()

    def handle_toggle_enabled(self, enabled: bool):
        self.overlay.set_enabled(enabled)
        self.config.enabled = enabled
        self.tray.update()

    def handle_tint_change(self, rgb):
        self.overlay.set_tint(*rgb)
        self.config.tint_color = rgb

    def handle_monitor_change(self, monitor_index: int):
        self.config.monitor_index = monitor_index
        x, y, w, h = calculate_overlay_geometry(
            preset=self.config.preset,
            split_ratio=self.config.split_ratio,
            monitor_index=monitor_index,
            custom_rect=self.config.custom_rect
        )
        self.overlay.set_geometry(x, y, w, h)

    def handle_launch_picker(self):
        self.panel.hide()

        def on_selected(rect_dict):
            self.config.custom_rect = rect_dict
            self.config.preset = "custom"
            self.overlay.set_direction("top_to_bottom")
            x, y, w, h = rect_dict["x"], rect_dict["y"], rect_dict["width"], rect_dict["height"]
            self.overlay.set_geometry(x, y, w, h)
            self.panel.refresh_from_external()
            self.panel.show()
            self.tray.update()

        def on_cancelled():
            self.panel.show()

        self.picker_window = RegionPickerWindow(on_selected=on_selected, on_cancelled=on_cancelled)

    def handle_exit(self):
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.overlay.destroy()
        except Exception:
            pass
        try:
            self.panel.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        self.panel.root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="LumiDim — Regional Screen Dimmer Overlay")
    parser.add_argument("--minimized", "--tray", action="store_true", help="Start minimized to the system tray")
    args = parser.parse_args()

    h_mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        print("[LumiDim] Another instance is already running.")
        sys.exit(0)

    app = LumiDimApp(start_minimized=args.minimized)
    app.run()

if __name__ == "__main__":
    main()
