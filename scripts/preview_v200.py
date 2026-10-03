"""Render a deterministic offscreen screenshot of the V-02 assistant."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from lautsprecher_konstruktion.services.automatic import automatic_design  # noqa: E402
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow  # noqa: E402


def main() -> None:
    app = QApplication([])
    font = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font))
    if font_id >= 0:
        app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    window = AssistantWindow()
    window.resize(1600, 960)
    window.demo_choice.setCurrentIndex(1)
    window._demo()
    result = automatic_design(window._request(), window.library)
    if result.status != "ok":
        raise RuntimeError(result.rejection_reasons)
    window._completed(result)
    window.show()
    for tab, name in ((window.panel_svg.parentWidget(), "preview_v200.png"),
                      (window.comparison, "preview_v200_vergleich.png"),
                      (window.internal_svg, "preview_v200_innen.png")):
        window.tabs.setCurrentWidget(tab)
        app.processEvents()
        output = Path(__file__).resolve().parents[1] / name
        window.grab().save(str(output))
        print(output)
    window.close()
    app.quit()


if __name__ == "__main__":
    main()
