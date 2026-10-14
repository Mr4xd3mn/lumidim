' LumiDim Silent Windows Launcher
' Launches main.py with pythonw.exe completely silently (no terminal window)
Set objFSO = CreateObject("Scripting.FileSystemObject")
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
Set objShell = CreateObject("WScript.Shell")

' Build command to launch main.py with pythonw
strCmd = "cmd /c cd /d """ & strScriptDir & """ && pythonw main.py"
objShell.Run strCmd, 0, False
