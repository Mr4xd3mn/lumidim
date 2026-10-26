import os
import json
import sys

DEFAULT_CONFIG = {
    "enabled": True,
    "opacity": 0.45,
    "preset": "bottom_half",  # "bottom_half", "top_half", "bottom_third", "full", "full_uniform", "custom"
    "split_ratio": 0.50,      # For bottom_half / top_half / custom split (fraction of screen height)
    "custom_rect": None,      # {"x": int, "y": int, "width": int, "height": int}
    "monitor_index": 0,       # 0 = primary, -1 = all monitors / virtual screen, >0 = monitor index
    "tint_color": [0, 0, 0],  # [R, G, B] - Default pure black
    "blend_ratio": 0.50,      # Transition blend height (fraction of overlay height for smooth fade)
    "gradient_curve": "smooth", # "smooth" (cosine/natural) or "linear"
    "start_with_windows": False,
    "hotkeys_enabled": True,
    "close_to_tray": True
}

def get_config_dir():
    appdata = os.environ.get("APPDATA")
    if appdata:
        cfg_dir = os.path.join(appdata, "LumiDim")
    else:
        cfg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    os.makedirs(cfg_dir, exist_ok=True)
    return cfg_dir

def get_config_path():
    return os.path.join(get_config_dir(), "settings.json")

import threading

class Config:
    def __init__(self):
        self._data = dict(DEFAULT_CONFIG)
        self._save_timer = None
        self._lock = threading.Lock()
        self.load()

    def load(self):
        cfg_path = get_config_path()
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception as e:
                print(f"[Config] Error loading config: {e}")
        return self._data

    def save(self, immediate=False):
        if immediate:
            self._do_save()
            return

        with self._lock:
            if self._save_timer:
                try:
                    self._save_timer.cancel()
                except Exception:
                    pass
            self._save_timer = threading.Timer(0.35, self._do_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _do_save(self):
        cfg_path = get_config_path()
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value, autosave=True):
        self._data[key] = value
        if autosave:
            self.save()

    def update(self, mapping, autosave=True):
        self._data.update(mapping)
        if autosave:
            self.save()

    @property
    def enabled(self):
        return self._data.get("enabled", True)

    @enabled.setter
    def enabled(self, val):
        self.set("enabled", bool(val))

    @property
    def opacity(self):
        return self._data.get("opacity", 0.45)

    @opacity.setter
    def opacity(self, val):
        self.set("opacity", max(0.0, min(0.95, float(val))))

    @property
    def preset(self):
        return self._data.get("preset", "bottom_half")

    @preset.setter
    def preset(self, val):
        self.set("preset", str(val))

    @property
    def split_ratio(self):
        return self._data.get("split_ratio", 0.50)

    @split_ratio.setter
    def split_ratio(self, val):
        self.set("split_ratio", max(0.1, min(0.95, float(val))))

    @property
    def custom_rect(self):
        return self._data.get("custom_rect")

    @custom_rect.setter
    def custom_rect(self, val):
        self.set("custom_rect", val)

    @property
    def monitor_index(self):
        return self._data.get("monitor_index", 0)

    @monitor_index.setter
    def monitor_index(self, val):
        self.set("monitor_index", int(val))

    @property
    def tint_color(self):
        return self._data.get("tint_color", [0, 0, 0])

    @tint_color.setter
    def tint_color(self, val):
        self.set("tint_color", list(val))

    @property
    def start_with_windows(self):
        return self._data.get("start_with_windows", False)

    @start_with_windows.setter
    def start_with_windows(self, val):
        self.set("start_with_windows", bool(val))

    @property
    def hotkeys_enabled(self):
        return self._data.get("hotkeys_enabled", True)

    @hotkeys_enabled.setter
    def hotkeys_enabled(self, val):
        self.set("hotkeys_enabled", bool(val))

    @property
    def blend_ratio(self):
        return self._data.get("blend_ratio", 0.50)

    @blend_ratio.setter
    def blend_ratio(self, val):
        self.set("blend_ratio", max(0.05, min(1.0, float(val))))

    @property
    def gradient_curve(self):
        return self._data.get("gradient_curve", "smooth")

    @gradient_curve.setter
    def gradient_curve(self, val):
        self.set("gradient_curve", str(val))

    @property
    def close_to_tray(self):
        return self._data.get("close_to_tray", True)

    @close_to_tray.setter
    def close_to_tray(self, val):
        self.set("close_to_tray", bool(val))

