# LumiDim

Lightweight regional screen dimmer for Windows. Overlays a semi-transparent, click-through dimming filter on a configurable area of your screen using Win32 layered windows.

---

## Features

- **Gradient dimming** — per-pixel vertical linear gradient via `UpdateLayeredWindow`. No hard edges.
- **Regional control** — dim the bottom half, top half, bottom third, full screen, or a custom drag-selected rectangle.
- **Uniform fullscreen dimming** — choose **Full Screen (Uniform)** in the control panel or tray's **Dimming Region** menu to dim every row equally, including the top edge. **Full Screen (Gradient)** keeps the existing fade. Opacity and tone apply to both modes; blend height only affects gradients. Your selected mode is saved between launches.
- **Click-through** — built with `WS_EX_TRANSPARENT | WS_EX_LAYERED`. Input passes to whatever is underneath.
- **Always-on-top** — background watchdog re-asserts z-order so fullscreen apps and games don't bury the overlay.
- **Color tones** — Classic Black, Warm Amber (night light), or Cool Slate.
- **System tray** — right-click for quick controls without opening the panel.
- **Global hotkeys** — Ctrl+Alt+D (toggle), Ctrl+Alt+Up/Down (opacity), Ctrl+Alt+P (panel).
- **Startup integration** — registers in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- **Multi-monitor** — per-monitor DPI V2 aware (`SetProcessDpiAwarenessContext`).
- **No hardware changes** — pure software alpha blending, does not touch backlight, DDC/CI, or gamma.

---

## Quick Start

**Executable (no Python needed):**
Download the [latest LumiDim.exe](https://github.com/Mr4xd3mn/lumidim/raw/refs/heads/main/dist/LumiDim.exe) and run it. Older versioned builds are available on the [Releases](https://github.com/Mr4xd3mn/lumidim/releases) page.

**From source:**
```powershell
pip install -r requirements.txt
python main.py
```

Start minimized to tray:
```powershell
pythonw main.py --minimized
```

---

## Project Structure

```
lumidim/
├── main.py           # Entry point, coordinator, single-instance mutex
├── overlay.py        # Win32 layered window engine
├── ui.py             # Control panel UI
├── tray.py           # System tray icon and context menu
├── regions.py        # Monitor geometry, DPI awareness, region presets
├── region_picker.py  # Interactive screen region selector
├── hotkeys.py        # Win32 RegisterHotKey listener
├── autostart.py      # Registry startup integration
├── config.py         # JSON settings persistence
└── requirements.txt
```

---

## Configuration

Settings are stored in `%APPDATA%\LumiDim\settings.json`:

```json
{
    "enabled": true,
    "opacity": 0.45,
    "preset": "bottom_half",
    "split_ratio": 0.50,
    "custom_rect": null,
    "monitor_index": 0,
    "tint_color": [0, 0, 0],
    "start_with_windows": false,
    "hotkeys_enabled": true,
    "close_to_tray": true
}
```

---

## Requirements

Python 3.10+, Windows 10/11.

```
pystray
pillow
numpy
pyinstaller
```
