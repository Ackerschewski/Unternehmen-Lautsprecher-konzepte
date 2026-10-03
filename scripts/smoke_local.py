"""Local headless smoke test for the full demonstration workflow."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'.mplcache'))
from PySide6.QtWidgets import QApplication
from lautsprecher_konstruktion.ui.main_window import MainWindow
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.export.package import export_project_package


def main() -> int:
    app=QApplication([])
    window=MainWindow()
    assert window._bundle is not None and window._bundle.vented_response is not None
    assert window._bundle.port is not None
    assert window._bundle.crossover_response is not None
    assert len(window._bundle.front_elements)==3
    window.enclosure_type.setCurrentIndex(window.enclosure_type.findData('sealed'))
    window.calculate()
    assert window._bundle.sealed is not None
    window.enclosure_type.setCurrentIndex(window.enclosure_type.findData('bass_reflex'))
    window.port_type.setCurrentIndex(window.port_type.findData('slot'))
    window.calculate()
    assert window._bundle.port.shape=='slot'
    window._load_demo()
    saved=window._project_from_form().model_dump_json()
    project=SpeakerProject.model_validate_json(saved)
    window._apply_project(project)
    window.calculate()
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()/'smoke_export'
    package=export_project_package(window._bundle,root)
    assert (package/'project.json').is_file()
    assert (package/'fertigung'/'fertigungsunterlagen.pdf').is_file()
    window.close();app.quit()
    print('SMOKE_OK',package)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
