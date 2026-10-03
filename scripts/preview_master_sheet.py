"""Render a representative overall sheet for local visual inspection."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from lautsprecher_konstruktion.drawings.master_sheet_svg import render_master_sheet_svg
from lautsprecher_konstruktion.library.store import ComponentLibrary
from lautsprecher_konstruktion.services.automatic import AutomaticDesignRequest, automatic_design


def main() -> None:
    output = Path(sys.argv[1])
    result = automatic_design(AutomaticDesignRequest(
        speaker_type="Breitbandlautsprecher", way_count=1,
        preferred_driver="Visaton B 200 - 6 Ohm",
        max_width_m=.45, max_height_m=.8, max_depth_m=.7), ComponentLibrary())
    if result.status != "ok":
        raise RuntimeError(str(result.rejection_reasons))
    svg = render_master_sheet_svg(result.designs[0].bundle)
    output.with_suffix(".svg").write_text(svg, encoding="utf-8")
    app = QGuiApplication.instance() or QGuiApplication([])
    _ = app
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    image = QImage(1800, renderer.defaultSize().height(), QImage.Format.Format_ARGB32)
    image.fill(0xffffffff)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(output)):
        raise RuntimeError("Vorschau konnte nicht gespeichert werden")
    print(output)


if __name__ == "__main__":
    main()
