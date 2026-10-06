from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from lautsprecher_konstruktion import REVISION
from lautsprecher_konstruktion.appdata import configure_logging, get_logger, install_excepthook
from lautsprecher_konstruktion.export.package import export_project_package
from lautsprecher_konstruktion.project.models import SpeakerProject
from lautsprecher_konstruktion.services.design import calculate_project
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.fonts import apply_default_font


class _ErrorRelay(QObject):
    reported = Signal(str)

    def __init__(self, log_path: Path) -> None:
        super().__init__()
        self._log_path = log_path
        self.reported.connect(self._show)

    def _show(self, text: str) -> None:
        QMessageBox.critical(None, "Unerwarteter Fehler",
                             f"{text}\n\nDetails stehen in der Protokolldatei:\n{self._log_path}")


def main() -> int:
    log_path = configure_logging()
    get_logger().info("Start %s, Protokoll: %s", REVISION, log_path)
    smoke = "--smoke" in sys.argv
    assistant_smoke = "--smoke-assistant" in sys.argv
    app = QApplication([arg for arg in sys.argv if arg not in {"--smoke", "--smoke-assistant"}])
    relay = _ErrorRelay(log_path)  # shows the dialog on the GUI thread, even for worker-thread errors
    install_excepthook(relay.reported.emit)
    apply_default_font(app)  # bundled Inter; the platform font stays if loading fails
    window = AssistantWindow()
    window.show()
    if not (smoke or assistant_smoke):
        window.offer_recovery()
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
                plan = window.cutting_panel.plan
                if plan is None or not plan.feasible or window.cutting_panel.sheet_choice.count() == 0:
                    raise ValueError("Zuschnittplan fehlt")
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
