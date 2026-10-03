from pathlib import Path

import pefile


root = Path("dist/Lautsprecher-Konstruktion_V-00.03.00/_internal/PySide6")
for source_name, target_name in (
    ("QtGui.pyd", "Qt6Gui.dll"),
    ("QtGui.pyd", "pyside6.abi3.dll"),
    ("Qt6Gui.dll", "Qt6Core.dll"),
):
    source = pefile.PE(str(root / source_name))
    target = pefile.PE(str(root / target_name))
    imports = [
        item.name
        for entry in source.DIRECTORY_ENTRY_IMPORT
        if entry.dll.decode().lower() == target_name.lower()
        for item in entry.imports
    ]
    exports = {item.name for item in target.DIRECTORY_ENTRY_EXPORT.symbols}
    missing = [item for item in imports if item not in exports]
    print(source_name, "->", target_name, "imports", len(imports), "missing", missing[:20])
