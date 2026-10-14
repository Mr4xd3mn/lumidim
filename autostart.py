import os
import sys
import winreg

APP_NAME = "LumiDimRegionalDimmer"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_launch_command() -> str:
    """Returns the silent startup command line for the application."""
    if getattr(sys, 'frozen', False):
        # Running as compiled PyInstaller executable
        exe_path = sys.executable
        return f'"{exe_path}" --minimized'
    else:
        # Running as Python script
        python_dir = os.path.dirname(sys.executable)
        pythonw = os.path.join(python_dir, "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable

        main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        return f'"{pythonw}" "{main_py}" --minimized'

def is_autostart_enabled() -> bool:
    """Checks whether the application is configured to run at Windows startup."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        print(f"[Autostart] Query error: {e}")
        return False

def set_autostart(enable: bool) -> bool:
    """Enables or disables automatic startup with Windows."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        if enable:
            cmd = get_launch_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            print(f"[Autostart] Enabled startup: {cmd}")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
                print("[Autostart] Disabled startup")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Autostart] Set error: {e}")
        return False
