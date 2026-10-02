from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import matplotlib
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow


def main() -> int:
    smoke = "--smoke" in sys.argv
    assistant_smoke = "--smoke-assistant" in sys.argv
    app = QApplication([arg for arg in sys.argv if arg not in {"--smoke", "--smoke-assistant"}])
    # Matplotlib ships this open font; it also makes offscreen/packaged Qt builds
    # readable on machines where Qt cannot discover system fonts.
    font_path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id >= 0:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 9))
    window = AssistantWindow()
    window.show()
    if smoke:
        if not window.library.entries("drivers"):
            return 3
        QTimer.singleShot(500, app.quit)
    if assistant_smoke:
        if not window.library.entries("drivers"):
            return 3

        def verify(result: object) -> None:
            try:
                if result.status != "ok" or not window.designs:
                    raise ValueError("Automatischer Entwurf fehlt")
                design = window.designs[0]
                if (not window.svg.renderer().isValid() or
                        not window.dimension_svg.renderer().isValid() or
                        not window.internal_svg.renderer().isValid() or
                        not window.panel_svg.renderer().isValid() or not design.bom):
                    raise ValueError("Zeichnung oder Stückliste fehlt")
                if not any(not item.is_test_data for item in window.library.entries("drivers")):
                    raise ValueError("Herstellerbibliothek fehlt")
                project = SpeakerProject.model_validate_json(design.project.model_dump_json())
                calculate_project(project)
                with tempfile.TemporaryDirectory(prefix="lk-v102-") as temp:
                    package = export_project_package(design.bundle, temp)
                    if not (package / "fertigung" / "fertigungsunterlagen.pdf").is_file():
                        raise ValueError("PDF-Export fehlt")
                    if not (package / "zeichnungen" / "massblatt.svg").is_file():
                        raise ValueError("Maßblatt fehlt")
                    if not (package / "zeichnungen" / "einzelteil_front.svg").is_file():
                        raise ValueError("Einzelteilplan fehlt")
                window._expert()
                if window.expert_window is None or window.expert_window._bundle is None:
                    raise ValueError("Expertenmodus fehlt")
                window.expert_window.close()
                app.exit(0)
            except (ValueError, OSError, AttributeError):
                app.exit(4)

        def start() -> None:
            window.demo_choice.setCurrentIndex(1)
            window._demo()
            window.create_design()
            if window.worker is None:
                app.exit(5)
                return
            window.worker.completed.connect(verify)
            window.worker.failed.connect(lambda _: app.exit(5))

        QTimer.singleShot(0, start)
        QTimer.singleShot(25000, lambda: app.exit(6))
    code = app.exec()
    if window.worker and window.worker.isRunning():
        window.worker.wait(5000)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
