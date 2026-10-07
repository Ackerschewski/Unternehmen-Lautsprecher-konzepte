"""Compact result widgets: the variant strip above the visualisation and the key-figure stack beside it."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.services.automatic import SpeakerDesign


def f3_of(design: SpeakerDesign) -> float | None:
    bundle = design.bundle
    return bundle.sealed.f3_hz if bundle.sealed else (
        bundle.vented_response.f3_hz if bundle.vented_response else None)


def comparison_sentences(design: SpeakerDesign, baseline: SpeakerDesign) -> list[str]:
    """Why a variant is better or worse than the recommendation, from calculated values only."""
    lines: list[str] = []
    f3, base_f3 = f3_of(design), f3_of(baseline)
    if f3 is not None and base_f3 is not None and abs(f3 - base_f3) >= 1:
        lines.append(f"Tiefbass: F3 {f3:.0f} statt {base_f3:.0f} Hz – "
                     + ("reicht tiefer." if f3 < base_f3 else "endet höher."))
    cab, base = design.bundle.cabinet, baseline.bundle.cabinet
    volume = cab.width_m * cab.height_m * cab.depth_m
    base_volume = base.width_m * base.height_m * base.depth_m
    if base_volume > 0 and abs(volume / base_volume - 1) >= 0.03:
        change = (volume / base_volume - 1) * 100
        lines.append(f"Größe: Außenvolumen {change:+.0f} % ({'größer' if change > 0 else 'kleiner'}).")
    if design.total_price_eur is not None and baseline.total_price_eur is not None:
        delta = design.total_price_eur - baseline.total_price_eur
        if abs(delta) >= 1:
            lines.append(f"Kosten: {delta:+.0f} € inkl. Reserve ({'teurer' if delta > 0 else 'günstiger'}).")
    elif (design.total_price_eur is None) != (baseline.total_price_eur is None):
        lines.append("Kosten: nicht vergleichbar, weil mindestens ein Preis unvollständig ist "
                     "(unbekannte Preise gelten nie als günstiger).")
    if design.spl_limit_db is not None and baseline.spl_limit_db is not None:
        delta = design.spl_limit_db - baseline.spl_limit_db
        if abs(delta) >= 1:
            lines.append(f"Max-SPL (thermisch): {delta:+.0f} dB.")
    kind, base_kind = design.project.enclosure.enclosure_type, baseline.project.enclosure.enclosure_type
    if kind != base_kind:
        lines.append(f"Bauart: {registry.get(kind).label} statt {registry.get(base_kind).label}.")
    warnings, base_warnings = len(design.bundle.warnings), len(baseline.bundle.warnings)
    if warnings != base_warnings:
        lines.append(f"Hinweise: {warnings} statt {base_warnings}.")
    return lines or ["Praktisch gleichwertig zur Empfehlung bei den berechneten Kennwerten."]


class VariantStrip(QWidget):
    """One line of chips (A/B/C/D) with the two or three facts that decide; clicking switches the design."""

    selected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[QPushButton] = []

    def count(self) -> int:
        return len(self._buttons)

    def set_designs(self, designs: tuple[SpeakerDesign, ...]) -> None:
        self.clear()
        for index, design in enumerate(designs):
            f3 = f3_of(design)
            cab = design.bundle.cabinet
            label = design.label or f"Variante {index + 1}"
            facts = (f"{registry.get(design.project.enclosure.enclosure_type).label} · "
                     f"{cab.width_m*1000:.0f}×{cab.height_m*1000:.0f}×{cab.depth_m*1000:.0f} mm · "
                     + (f"F3 {f3:.0f} Hz" if f3 is not None else "F3 n/a"))
            button = QPushButton(f"{label}\n{facts}")
            button.setObjectName("variantChip")
            button.setCheckable(True)
            button.setToolTip("Variante anzeigen: Visualisierung und Kennwerte wechseln mit")
            button.clicked.connect(lambda _c=False, i=index: self.selected.emit(i))
            self._group.addButton(button)
            self._layout.addWidget(button, 1)
            self._buttons.append(button)
        if designs:
            self.select(0)

    def clear(self) -> None:
        for button in self._buttons:
            self._group.removeButton(button)
            button.setParent(None)
            button.deleteLater()
        self._buttons = []

    def select(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)


class KpiGrid(QWidget):
    """Six key figures as small cards in two columns; each card has a label, a value and a tooltip."""

    def __init__(self, keys: tuple[str, ...], columns: int = 2) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self._values: dict[str, QLabel] = {}
        self._cards: dict[str, QFrame] = {}
        for index, key in enumerate(keys):
            card = QFrame()
            card.setObjectName("kpiCard")
            card.setFixedHeight(58)
            inner = QVBoxLayout(card)
            inner.setContentsMargins(10, 6, 10, 6)
            inner.setSpacing(0)
            name = QLabel(key)
            name.setObjectName("kpiLabel")
            value = QLabel("–")
            value.setObjectName("kpiValue")
            value.setWordWrap(True)
            inner.addWidget(name)
            inner.addWidget(value)
            grid.addWidget(card, index // columns, index % columns)
            self._values[key] = value
            self._cards[key] = card

    def keys(self) -> tuple[str, ...]:
        return tuple(self._values)

    def set_value(self, key: str, value: str, note: str = "") -> None:
        self._values[key].setText(value)
        self._cards[key].setToolTip(note)

    def value(self, key: str) -> str:
        return self._values[key].text()

    def clear(self) -> None:
        for label in self._values.values():
            label.setText("–")
