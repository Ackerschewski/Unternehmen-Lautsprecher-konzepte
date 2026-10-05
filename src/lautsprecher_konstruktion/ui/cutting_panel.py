"""Results tab: stock sheet settings, cutting layout per sheet and cabinet weight."""
from __future__ import annotations

from html import escape

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.appdata import Settings
from lautsprecher_konstruktion.export.cutting import (
    DEFAULT_KERF_MM,
    CuttingPlan,
    CuttingSettings,
    plan_cutting,
    render_cutting_svg,
    summary_lines,
)
from lautsprecher_konstruktion.export.weight import estimate_weight
from lautsprecher_konstruktion.services.design import DesignBundle
from lautsprecher_konstruktion.ui.zoom_svg import ZoomableSvgView


def _spin(minimum: float, maximum: float, value: float, suffix: str, decimals: int = 0) -> QDoubleSpinBox:
    control = QDoubleSpinBox()
    control.setRange(minimum, maximum)
    control.setDecimals(decimals)
    control.setValue(value)
    control.setSuffix(suffix)
    return control


def stored_cutting_settings(material: str, store: Settings | None = None) -> CuttingSettings:
    """Cutting settings as last saved by the user; defaults if nothing is stored or values are invalid."""
    store = store or Settings()
    kerf = float(store.get("kerf_mm", DEFAULT_KERF_MM))
    rotate = bool(store.get("allow_rotation", True))
    try:
        if store.get("use_default_sheet", True):
            return CuttingSettings.for_material(material, kerf_mm=kerf, allow_rotation=rotate)
        return CuttingSettings(float(store.get("sheet_width_mm", 2500)),
                               float(store.get("sheet_height_mm", 1250)), kerf, rotate)
    except (TypeError, ValueError):
        return CuttingSettings.for_material(material)


class CuttingPanel(QWidget):
    """Plans the cut on every change; settings persist per user."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self._settings = settings or Settings()
        self._bundle: DesignBundle | None = None
        self.plan: CuttingPlan | None = None

        box = QGroupBox("Plattenmaß und Sägeschnitt")
        grid = QGridLayout(box)
        self.sheet_width = _spin(300, 6000, float(self._settings.get("sheet_width_mm", 2500)), " mm")
        self.sheet_height = _spin(300, 4000, float(self._settings.get("sheet_height_mm", 1250)), " mm")
        self.kerf = _spin(0, 10, float(self._settings.get("kerf_mm", DEFAULT_KERF_MM)), " mm", 1)
        self.rotation = QCheckBox("Teile dürfen gedreht werden (Maserung unbeachtet)")
        self.rotation.setChecked(bool(self._settings.get("allow_rotation", True)))
        self.use_defaults = QCheckBox("Standardplatte des Materials verwenden")
        self.use_defaults.setChecked(bool(self._settings.get("use_default_sheet", True)))
        for column, (label, widget) in enumerate((("Plattenbreite", self.sheet_width),
                                                  ("Plattenhöhe", self.sheet_height),
                                                  ("Sägeschnitt", self.kerf))):
            grid.addWidget(QLabel(label), 0, 2 * column)
            grid.addWidget(widget, 0, 2 * column + 1)
        grid.addWidget(self.use_defaults, 1, 0, 1, 3)
        grid.addWidget(self.rotation, 1, 3, 1, 3)

        self.summary = QTextBrowser()
        self.summary.setMaximumHeight(120)
        self.sheet_choice = QComboBox()
        self.view = ZoomableSvgView()
        layout = QVBoxLayout(self)
        for widget in (box, self.summary, self.sheet_choice):
            layout.addWidget(widget)
        layout.addWidget(self.view, 1)

        for control in (self.sheet_width, self.sheet_height, self.kerf):
            control.valueChanged.connect(self._changed)
        self.rotation.toggled.connect(self._changed)
        self.use_defaults.toggled.connect(self._changed)
        self.sheet_choice.currentIndexChanged.connect(self._show_sheet)
        self._sync_enabled()

    def settings(self, material: str = "") -> CuttingSettings:
        """Current settings; with the default-sheet option the material's stock size applies."""
        if self.use_defaults.isChecked():
            return CuttingSettings.for_material(material, kerf_mm=self.kerf.value(),
                                                allow_rotation=self.rotation.isChecked())
        return CuttingSettings(self.sheet_width.value(), self.sheet_height.value(), self.kerf.value(),
                               self.rotation.isChecked())

    def set_bundle(self, bundle: DesignBundle | None) -> None:
        self._bundle = bundle
        self._replan()

    def _sync_enabled(self) -> None:
        manual = not self.use_defaults.isChecked()
        self.sheet_width.setEnabled(manual)
        self.sheet_height.setEnabled(manual)

    def _changed(self, *_args: object) -> None:
        self._sync_enabled()
        self._settings.set("sheet_width_mm", self.sheet_width.value())
        self._settings.set("sheet_height_mm", self.sheet_height.value())
        self._settings.set("kerf_mm", self.kerf.value())
        self._settings.set("allow_rotation", self.rotation.isChecked())
        self._settings.set("use_default_sheet", self.use_defaults.isChecked())
        self._replan()

    def _replan(self) -> None:
        self.sheet_choice.blockSignals(True)
        self.sheet_choice.clear()
        self.plan = None
        if self._bundle is None:
            self.summary.setHtml("<p>Noch kein Entwurf.</p>")
            self.sheet_choice.blockSignals(False)
            return
        try:
            self.plan = plan_cutting(self._bundle, self.settings(self._bundle.project.material))
        except ValueError as exc:
            self.summary.setHtml(f"<p>Zuschnitt nicht berechenbar: {escape(str(exc))}</p>")
            self.sheet_choice.blockSignals(False)
            return
        for g_index, group in enumerate(self.plan.groups):
            for s_index, sheet in enumerate(group.sheets):
                self.sheet_choice.addItem(f"{group.thickness_mm:.0f} mm · Platte {sheet.index}/{len(group.sheets)}",
                                          (g_index, s_index))
        self.sheet_choice.blockSignals(False)
        lines = "".join(f"<li>{escape(line)}</li>" for line in summary_lines(self.plan))
        weight = estimate_weight(self._bundle)
        self.summary.setHtml(f"<ul>{lines}</ul><p><b>Gewicht:</b> {escape(weight.describe())}</p>"
                             "<p>Zuschnittplan und Bauanleitung liegen im Export unter <i>fertigung</i>.</p>")
        if self.sheet_choice.count():
            self.sheet_choice.setCurrentIndex(0)
            self._show_sheet(0)

    def _show_sheet(self, index: int) -> None:
        if self.plan is None or index < 0:
            return
        g_index, s_index = self.sheet_choice.itemData(index)
        self.view.load(QByteArray(render_cutting_svg(self.plan, g_index, s_index).encode("utf-8")))
