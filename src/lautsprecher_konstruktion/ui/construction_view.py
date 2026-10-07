"""'3D & Konstruktion' workspace: the interactive scene next to an honest list of what it contains."""
from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QTextBrowser, QWidget

from lautsprecher_konstruktion.enclosure.scene import Scene, SolidKind, build_scene
from lautsprecher_konstruktion.services.design import DesignBundle
from lautsprecher_konstruktion.ui.scene_view import ScenePreview

KIND_TITLES = {
    SolidKind.PANEL: "Gehäuseplatten", SolidKind.DRIVER: "Chassis", SolidKind.PASSIVE_RADIATOR: "Passivmembranen",
    SolidKind.PORT: "Ports", SolidKind.BRACE: "Verstärkungen", SolidKind.DIVIDER: "Trennwände",
    SolidKind.TREATMENT: "Dämmung",
}


def scene_overview_html(scene: Scene | None) -> str:
    """Objects of the scene by kind with size and accuracy label; objects without a 3D position are listed separately."""
    if scene is None:
        return ("<h3>Keine 3D-Geometrie</h3><p>Für diese Bauart gibt es noch kein 3D-Modell. "
                "Die Zeichnungen unter „Zeichnungen“ bleiben die verbindliche Quelle.</p>")
    ex, ey, ez = scene.extent
    parts = [f"<h3>Konstruktion</h3><p>Außenmaß {ex*1000:.0f} × {ey*1000:.0f} × {ez*1000:.0f} mm</p>"]
    for kind in SolidKind:
        solids = [s for s in scene.solids if s.kind is kind]
        if not solids:
            continue
        rows = "".join(
            f"<li>{escape(s.label)} <i>({escape(s.accuracy)})</i></li>"
            for s in {s.label: s for s in solids}.values())
        parts.append(f"<p><b>{KIND_TITLES[kind]}</b> ({len(solids)} Körper)</p><ul>{rows}</ul>")
    if scene.unplaced:
        parts.append("<p><b>Ohne 3D-Position</b></p><ul>" + "".join(f"<li>{escape(u)}</li>" for u in scene.unplaced) + "</ul>")
    parts.append("<p>" + " ".join(escape(n) for n in scene.notes) + "</p>")
    return "".join(parts)


class ConstructionView(QWidget):
    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.preview = ScenePreview(mode)
        self.overview = QTextBrowser()
        self.overview.setMinimumWidth(260)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.preview)
        split.addWidget(self.overview)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(split)

    def set_mode(self, mode: str) -> None:
        self.preview.set_mode(mode)

    def set_bundle(self, bundle: DesignBundle | None) -> None:
        self.preview.set_bundle(bundle)
        self.overview.setHtml(scene_overview_html(build_scene(bundle) if bundle is not None else None)
                              if bundle is not None else "<p>Berechne zuerst einen Entwurf.</p>")
