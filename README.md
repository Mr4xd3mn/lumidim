# LumiDim — Lightweight Regional Screen Dimmer for Windows

**LumiDim** is a high-performance, minimalist desktop application for Windows that provides hardware-independent, regional software screen dimming. It allows you to define a specific area of your screen—specifically the **bottom half** by default—and overlay a persistent, semi-transparent dimming filter with seamless click-through pass-through.

---

## ✨ Features

1. **Seamless Linear Gradient Dimming (Zero Harsh Lines)**
   - Replaces hard solid edges with a **per-pixel vertical linear gradient** composited via Win32 `UpdateLayeredWindow`.
   - Starts completely transparent ($\alpha = 0$) at the boundary edge and blends seamlessly down to your chosen peak opacity, matching physical backlight falloff.
   - Utilizes a cosine ease curve to eliminate perceptual Mach bands or visible boundary creases.

2. **Customizable Gradient Blend Height / Falloff Control**
   - Fine-tune exactly where the transition begins and ends using the **Gradient Blend & Falloff Slider** (5% to 100%).
   - Quick presets: **25% Soft Edge**, **50% Natural Falloff**, **75% Deep Blend**, and **100% Full Gradient**.

3. **Regional Dimming Overlay (Bottom Half Default)**
   - Pre-configured to dim the bottom 50% of the display right out of the box.
   - Smooth split-height slider allows dynamic adjustment between 10% and 90% of screen height.
   - Presets included: **Bottom Half**, **Top Half**, **Bottom 1/3**, **Full Screen**, and **Custom Region**.

4. **Interactive Drag-to-Select Region**
   - Click **"🎯 Drag & Select Custom Region on Screen..."** to draw a custom box over any specific part of your screen with real-time coordinate and dimension readout.

5. **Persistent Always-on-Top (Over Everything)**
   - Leverages native Win32 extended window styles (`WS_EX_TOPMOST`, `WS_EX_TOOLWINDOW`, `WS_EX_NOACTIVATE`).
   - Includes a background watchdog that continuously re-asserts top z-order priority so that fullscreen games, borderless windows, taskbars, and video players never bury or hide the dimmer.

6. **100% Click-Through Pass-Through**
   - Built with `WS_EX_TRANSPARENT | WS_EX_LAYERED`.
   - Mouse clicks, scrolling, double clicks, and drag-and-drop actions pass directly to whatever application, game, or window is underneath the overlay.
   - Overlay never steals keyboard focus or activates over active windows.

7. **Software-Based Dimming (Zero Hardware/System Modification)**
   - Operates completely via desktop window composition alpha blending.
   - Does **not** alter hardware monitor backlight, DDC/CI settings, or Windows global gamma curves.

8. **Intuitive Real-Time Opacity & Tone Controls**
   - **Modern Control Panel**: Real-time sliders for both Opacity (0% to 95%) and Gradient Blend Height (5% to 100%) with instant live response.
   - **System Tray Icon**: Right-click to quickly toggle presets, adjust opacity or blend height in steps, or open the control panel.
   - **Color Tone Modes**:
     - *Classic Black*: Neutral software dimming (reduces perceived screen luminance).
     - *Warm Amber*: Night light tone (filters blue light for night-time comfort).
     - *Cool Slate*: Soft charcoal tone.

7. **Multi-Monitor & Virtual Desktop Support**
   - Per-monitor DPI V2 aware (`SetProcessDpiAwarenessContext`).
   - Choose between Primary Display, Secondary Monitors, or Span All Displays.

8. **Windows Startup Integration**
   - One-click toggle in both the Control Panel and Tray menu to launch automatically when Windows boots.
   - Registers in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` with `--minimized` to silently start docked in the system tray.

9. **Global Keyboard Shortcuts**
   - <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>D</kbd> : Toggle Dimmer On/Off
   - <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>↑</kbd> : Increase Dimming Opacity (+5%)
   - <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>↓</kbd> : Decrease Dimming Opacity (-5%)
   - <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>P</kbd> : Show / Hide Control Panel

---

## 🚀 Quick Start

### Option A: Standalone Executable (No Python Required)
Double-click:
```
dist\LumiDim.exe
```

### Option B: Silent Launcher (Zero Console Window)
Double-click `run_silently.vbs` to start LumiDim directly into the background without a command prompt window.

### Option C: Python Source
Run with Python:
```powershell
python main.py
```
Or start minimized directly to the tray:
```powershell
pythonw main.py --minimized
```

---

## 📁 Project Architecture

```
goofy-davinci/
├── main.py             # Application entry point, coordinator, and single-instance mutex
├── overlay.py          # Native Win32 layered, click-through, topmost window engine
├── ui.py               # Sleek modern dark-themed Control Panel UI
├── tray.py             # System tray icon and dynamic context menu (pystray)
├── regions.py          # Monitor geometry, DPI awareness, and regional presets
├── region_picker.py    # Interactive visual screen region selection tool
├── hotkeys.py          # Win32 RegisterHotKey global shortcut listener
├── autostart.py        # Windows Registry HKCU Run integration
├── config.py           # Configuration manager and JSON settings persistence
├── app_icon.ico        # High-DPI Windows application icon
├── run_silently.vbs    # Silent VBScript launcher
├── run_dimmer.bat      # Windows batch launcher
└── dist/
    └── LumiDim.exe     # Standalone compiled Windows executable
```

---

## ⚙️ Configuration File
Settings are persisted in `%APPDATA%\LumiDim\settings.json`:
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
