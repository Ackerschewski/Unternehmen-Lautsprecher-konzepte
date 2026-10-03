import ctypes
import os
from pathlib import Path
import sys
import time

print("MEIPASS", sys._MEIPASS, flush=True)
root = Path(sys._MEIPASS) / "PySide6"
with os.add_dll_directory(str(root)):
    for name in ("Qt6Core.dll", "QtCore.pyd", "Qt6Gui.dll", "QtGui.pyd"):
        try:
            print(name, ctypes.WinDLL(str(root / name)), flush=True)
        except OSError as exc:
            print(name, repr(exc), flush=True)
import PySide6.QtCore

print("QtCore imported", flush=True)
import PySide6.QtGui

print("QtGui imported", flush=True)
time.sleep(60)
