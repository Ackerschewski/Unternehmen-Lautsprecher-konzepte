"""Variant cards with metric chips and a mini comparison; replaces the old text-block cards."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.services.automatic import SpeakerDesign
from lautsprecher_konstruktion.services.price_status import cheaper_than, price_info
from lautsprecher_konstruktion.services.variant_metrics import (
    Chip,
    Tone,
    chips_for,
    comparison_rows,
    f3_of,
)
from lautsprecher_konstruktion.ui.tokens import UI_FONT, theme

TONE_PROPERTY = {Tone.OK: "ok", Tone.WARN: "warn", Tone.BAD: "bad", Tone.MUTED: "muted"}


def variant_tag(index: int, design: SpeakerDesign, baseline: SpeakerDesign) -> str:
    """Short label of what sets the variant apart; "Günstiger" only with complete, comparable prices."""
    if index == 0:
        return "Empfehlung"
    f3, base_f3 = f3_of(design), f3_of(baseline)
    cab, base = design.bundle.cabinet, baseline.bundle.cabinet
    volume = cab.width_m * cab.height_m * cab.depth_m
    if f3 is not None and base_f3 is not None and f3 < base_f3 - 3:
        return "Mehr Tiefbass"
    if volume < base.width_m * base.height_m * base.depth_m * 0.92:
        return "Kompakter"
    if cheaper_than(price_info(design.bom), price_info(baseline.bom)):
        return "Günstiger"
    return "Alternative"


class ChipLabel(QLabel):
    def __init__(self, chip: Chip) -> None:
        super().__init__(chip.text)
        self.setObjectName("metricChip")
        self.setProperty("tone", TONE_PROPERTY[chip.tone])
        self.setProperty("chip", chip.key)
        self.setWordWrap(False)


class VariantCard(QFrame):
    """Clickable card: title, tag, enclosure, then metric chips (no free-text block)."""

    clicked = Signal()

    def __init__(self, design: SpeakerDesign, tag: str, chips: tuple[Chip, ...]) -> None:
        super().__init__()
        self.setObjectName("variantCard")
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        head = QHBoxLayout()
        self.title = QLabel(design.label)
        self.title.setObjectName("variantTitle")
        self.tag = QLabel(tag)
        self.tag.setObjectName("variantTag")
        head.addWidget(self.title)
        head.addStretch(1)
        if tag.casefold() not in design.label.casefold():  # the label often already says "Empfehlung"
            head.addWidget(self.tag)
        else:
            self.tag.hide()
        layout.addLayout(head)
        self.subtitle = QLabel(registry.get(design.project.enclosure.enclosure_type).label)
        self.subtitle.setObjectName("caption")
        layout.addWidget(self.subtitle)
        self.chips: list[ChipLabel] = []
        row: QHBoxLayout | None = None
        for index, chip in enumerate(chips):
            if index % 2 == 0:
                row = QHBoxLayout()
                row.setSpacing(4)
                layout.addLayout(row)
            label = ChipLabel(chip)
            self.chips.append(label)
            assert row is not None
            row.addWidget(label)
            if index % 2 == 1 or index == len(chips) - 1:
                row.addStretch(1)
        self.score = QLabel(f"Zielerfüllung {design.score:.0f} % (nur belegte Kriterien)")
        self.score.setObjectName("caption")
        layout.addWidget(self.score)

    def text(self) -> str:
        return " | ".join([self.title.text(), self.tag.text(), self.subtitle.text(), *(c.text() for c in self.chips), self.score.text()])

    def set_selected(self, on: bool) -> None:
        self.setProperty("selected", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def keyPressEvent(self, event: object) -> None:
        key = getattr(event, "key", lambda: None)()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)  # type: ignore[arg-type]


class ComparisonBars(QWidget):
    """Mini bar comparison of the decision metrics; no decorative charts, unknown values stay empty."""

    BAR_H = 11
    GAP = 6
    LABEL_W = 130
    TEXT_W = 190
    TRACK_MAX = 460

    def __init__(self, mode: str = "light") -> None:
        super().__init__()
        self.mode = mode
        self.designs: tuple[SpeakerDesign, ...] = ()
        self.rows = comparison_rows(())
        self.selected = 0
        self.setMinimumHeight(40)

    def _row_h(self) -> int:
        return len(self.designs) * (self.BAR_H + 1) + self.GAP + 8

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def set_designs(self, designs: tuple[SpeakerDesign, ...]) -> None:
        self.designs = designs
        self.rows = comparison_rows(designs) if designs else ()
        self.selected = 0
        self.setMinimumHeight(self._row_h() * len(self.rows) + 30 if self.rows else 40)
        self.update()

    def select(self, index: int) -> None:
        self.selected = index
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(560, self._row_h() * max(1, len(self.rows)) + 30)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = theme(self.mode)
        painter.fillRect(self.rect(), QColor(t["surface"]))
        if not self.rows:
            return
        font = QFont(UI_FONT)
        font.setPixelSize(11)
        painter.setFont(font)
        row_h = self._row_h()
        letter_w = 16
        track_x = self.LABEL_W + letter_w + 8
        track_w = max(60.0, min(float(self.TRACK_MAX), self.width() - track_x - self.TEXT_W - 12))
        for r, row in enumerate(self.rows):
            y = 6 + r * row_h
            disabled = bool(row.disabled_reason)
            painter.setPen(QColor(t["disabledText" if disabled else "textPrimary"]))
            painter.drawText(QRectF(0, y, self.LABEL_W, row_h - 6), Qt.AlignmentFlag.AlignVCenter, row.label)
            for i, value in enumerate(row.values):
                by = y + i * (self.BAR_H + 1)
                chosen = i == self.selected
                painter.setPen(QColor(t["textPrimary" if chosen else "textSecondary"]))
                painter.drawText(QRectF(self.LABEL_W, by - 1, letter_w, self.BAR_H + 2), Qt.AlignmentFlag.AlignVCenter,
                                 chr(ord("A") + i))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(t["band"]))
                painter.drawRoundedRect(QRectF(track_x, by, track_w, self.BAR_H), 2, 2)
                if value is not None:
                    painter.setBrush(QColor(t["accent"] if chosen else t["borderStrong"]))
                    painter.drawRoundedRect(QRectF(track_x, by, track_w * value, self.BAR_H), 2, 2)
                text = "Preisranking nicht möglich" if disabled and i == 0 else (
                    "" if disabled else (row.texts[i] if i < len(row.texts) else ""))
                painter.setPen(QColor(t["warning"] if disabled else t["textPrimary" if chosen else "textSecondary"]))
                painter.drawText(QRectF(track_x + track_w + 10, by - 1, self.TEXT_W, self.BAR_H + 2),
                                 Qt.AlignmentFlag.AlignVCenter, text)
        painter.setPen(QColor(t["textSecondary"]))
        painter.drawText(QRectF(0, self.height() - 22, self.width(), 18), Qt.AlignmentFlag.AlignVCenter,
                         "Längerer Balken = besser für dieses Kriterium. Zeilen A, B, C … sind die Varianten.")


class VariantCards(QWidget):
    """Row of decision cards (A, B, C, D) built from the metric chips of each variant."""

    selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: list[VariantCard] = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    def set_designs(self, designs: tuple[SpeakerDesign, ...]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()
        if not designs:
            label = QLabel("Noch keine Varianten berechnet.")
            label.setObjectName("caption")
            self._layout.addWidget(label)
            return
        baseline = designs[0]
        for index, design in enumerate(designs):
            card = VariantCard(design, variant_tag(index, design, baseline), chips_for(design, baseline))
            card.clicked.connect(lambda i=index: self.selected.emit(i))
            self._layout.addWidget(card, 1)
            self._buttons.append(card)
        self.select(0)

    def select(self, index: int) -> None:
        for i, card in enumerate(self._buttons):
            card.set_selected(i == index)
