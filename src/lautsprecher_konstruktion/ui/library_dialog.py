"""Searchable local component library editor."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from lautsprecher_konstruktion.library.store import CATEGORIES, ComponentLibrary, LibraryEntry

LABELS = ("Treiber", "Passivmembranen", "Ports", "Weichenbauteile", "Hardware", "Materialien")


class LibraryDialog(QDialog):
    def __init__(self, library: ComponentLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.library = library
        self.setWindowTitle("Komponentenbibliothek")
        self.resize(1050, 660)
        outer = QVBoxLayout(self)
        sourced = sum(not e.is_test_data for e in library.entries())
        ready = sum(e.driver is not None for e in library.entries("drivers"))
        priced = sum(e.price_eur is not None or
                     (e.driver is not None and e.driver.currency == "EUR" and e.driver.price is not None)
                     for e in library.entries())
        outer.addWidget(QLabel(f"Lokale Komponentenbibliothek · {sourced} Quelleneinträge · "
                               f"{ready} Treiber mit T/S-Daten · {priced} Einträge mit Preis"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Hersteller oder Modell suchen")
        self.search.textChanged.connect(self.refresh)
        outer.addWidget(self.search)
        self.tabs = QTabWidget()
        self.tables: list[QTableWidget] = []
        for label in LABELS:
            table = QTableWidget(0, 5)
            table.setHorizontalHeaderLabels(["Hersteller", "Modell", "Preis/Stück", "Quelle", "Status"])
            table.horizontalHeader().setStretchLastSection(True)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.itemSelectionChanged.connect(self._select)
            self.tables.append(table)
            self.tabs.addTab(table, label)
        self.tabs.currentChanged.connect(self.refresh)
        row = QHBoxLayout()
        row.addWidget(self.tabs, 3)
        right = QVBoxLayout()
        right.addWidget(QLabel("Datensatz (JSON)"))
        self.details = QPlainTextEdit()
        self.details.setPlaceholderText("Komponente auswählen oder neuen Datensatz als JSON eingeben")
        right.addWidget(self.details, 1)
        row.addLayout(right, 2)
        outer.addLayout(row, 1)
        actions = QHBoxLayout()
        for label, callback in (
            ("Import JSON/CSV", self._import), ("Neu", self._new),
            ("Hinzufügen / speichern", self._save), ("Aktivieren / deaktivieren", self._toggle),
            ("Preisquelle öffnen", self._open_price_source),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        outer.addLayout(actions)
        self.refresh()

    def _category(self) -> str:
        return CATEGORIES[self.tabs.currentIndex()]

    def _selected_id(self) -> str | None:
        table = self.tables[self.tabs.currentIndex()]
        row = table.currentRow()
        item = table.item(row, 0) if row >= 0 else None
        return item.data(256) if item else None

    def refresh(self, *_: object) -> None:
        for category, table in zip(CATEGORIES, self.tables, strict=True):
            records = self.library.entries(category, self.search.text(), include_inactive=True)
            table.setRowCount(len(records))
            for row, entry in enumerate(records):
                status = ("deaktiviert" if not entry.active else
                          "TESTDATEN" if entry.is_test_data else
                          "Katalog · T/S fehlen" if entry.category == "drivers" and entry.driver is None else
                          "T/S vorhanden" if entry.category == "drivers" else "Quellendaten")
                price = entry.price_eur if entry.price_eur is not None else (
                    entry.driver.price if entry.driver and entry.driver.currency == "EUR" else None)
                for column, value in enumerate((entry.manufacturer, entry.model,
                    f"{price:.2f} €" if price is not None else "Preis fehlt",
                    (entry.source or "–")[:54], status)):
                    cell = QTableWidgetItem(value)
                    if column == 2:
                        cell.setToolTip(f"Preisquelle: {entry.product_url or 'nicht angegeben'}\n"
                                        f"Stand: {entry.price_checked_on or 'unbekannt'}")
                    if column == 3:
                        cell.setToolTip(entry.source)
                    if column == 0:
                        cell.setData(256, entry.id)
                    table.setItem(row, column, cell)
            table.resizeColumnsToContents()

    def _select(self) -> None:
        key = self._selected_id()
        if key:
            entry = next((e for e in self.library.entries(include_inactive=True) if e.id == key), None)
            if entry:
                self.details.setPlainText(json.dumps(entry.model_dump(mode="json"),
                    indent=2, ensure_ascii=False))

    def _new(self) -> None:
        self.details.setPlainText(json.dumps({"id": "eigene:neue_komponente",
            "category": self._category(), "manufacturer": "", "model": "",
            "specs": {}, "source": "Manuelle Eingabe", "active": True},
            indent=2, ensure_ascii=False))

    def _save(self) -> None:
        try:
            entry = LibraryEntry.model_validate_json(self.details.toPlainText())
            if entry.category != self._category():
                raise ValueError("Die Kategorie muss zum geöffneten Tab passen.")
            self.library.upsert(entry)
            self.refresh()
        except (ValidationError, ValueError, OSError) as exc:
            QMessageBox.warning(self, "Datensatz ungültig", str(exc))

    def _import(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Komponenten importieren", "",
            "Komponenten (*.json *.csv)")
        if filename:
            try:
                count = self.library.import_file(Path(filename), self._category())
                self.refresh()
                QMessageBox.information(self, "Import", f"{count} Datensätze importiert.")
            except (OSError, ValueError, ValidationError, KeyError) as exc:
                QMessageBox.warning(self, "Import fehlgeschlagen", str(exc))

    def _toggle(self) -> None:
        key = self._selected_id()
        if key:
            current = next(e for e in self.library.entries(include_inactive=True) if e.id == key)
            self.library.set_active(key, not current.active)
            self.refresh()

    def _open_price_source(self) -> None:
        key = self._selected_id()
        entry = next((e for e in self.library.entries(include_inactive=True) if e.id == key), None)
        if entry is None or entry.product_url is None:
            QMessageBox.information(self, "Preisquelle", "Für diesen Eintrag ist keine Preisquelle hinterlegt.")
            return
        QDesktopServices.openUrl(QUrl(str(entry.product_url)))
