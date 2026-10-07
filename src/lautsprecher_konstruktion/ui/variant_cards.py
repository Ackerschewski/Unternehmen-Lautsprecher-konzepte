"""Compact variant cards (A/B/C) that compare without horizontal scrolling."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


@dataclass(frozen=True)
class CardData:
    label: str
    enclosure: str
    size_mm: str
    f3_hz: float | None
    total_price_eur: float | None  # None = unknown, never treated as cheap
    check: str  # glyph + text
    deviation: str
    chassis: str


class VariantCard(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, data: CardData) -> None:
        super().__init__()
        self.index = index
        self.setObjectName("variantCard")
        self.setProperty("selected", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        eyebrow = QLabel(escape(data.label))
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)
        title = QLabel(f"<b>{escape(data.enclosure)}</b>")
        layout.addWidget(title)
        for text in (data.size_mm + " mm", f"F3 {data.f3_hz:.0f} Hz" if data.f3_hz else "F3 nicht berechenbar",
                     (f"{data.total_price_eur:.0f} € inkl. Reserve" if data.total_price_eur is not None
                      else "Preis unvollständig · nicht vergleichbar"),
                     data.check, f"Abw. Zielkurve {data.deviation}"):
            label = QLabel(escape(text))
            label.setObjectName("caption")
            layout.addWidget(label)
        chassis = QLabel(escape(data.chassis))
        chassis.setObjectName("caption")
        chassis.setWordWrap(True)
        layout.addWidget(chassis)
        self.setToolTip("Klicken, um diese Variante anzuzeigen")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit(self.index)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class VariantCards(QWidget):
    selected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)
        self._cards: list[VariantCard] = []

    def set_cards(self, cards: list[CardData]) -> None:
        self.clear()
        for index, data in enumerate(cards):
            card = VariantCard(index, data)
            card.clicked.connect(self.selected)
            self._layout.addWidget(card, 1)
            self._cards.append(card)

    def clear(self) -> None:
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards = []

    def count(self) -> int:
        return len(self._cards)

    def select(self, index: int) -> None:
        for i, card in enumerate(self._cards):
            card.set_selected(i == index)
