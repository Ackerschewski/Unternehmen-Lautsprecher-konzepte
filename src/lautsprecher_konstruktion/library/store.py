"""Validated JSON/CSV component catalog with a writable local overlay.

Bundled records are examples only. User imports live in LOCALAPPDATA and never
modify the program installation. Records are indexed in memory once per load.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from lautsprecher_konstruktion.appdata import user_data_dir
from lautsprecher_konstruktion.drivers.catalog import DriverCatalog
from lautsprecher_konstruktion.drivers.models import Driver

Category = Literal["drivers", "passive_radiators", "ports", "crossover", "hardware", "materials"]
CATEGORIES: tuple[Category, ...] = (
    "drivers", "passive_radiators", "ports", "crossover", "hardware", "materials"
)


class LibraryEntry(BaseModel):
    id: str
    category: Category
    manufacturer: str = ""
    model: str
    driver: Driver | None = None
    specs: dict[str, str | float | int | bool | None] = Field(default_factory=dict)
    source: str = ""
    price_eur: float | None = Field(default=None, ge=0)
    price_checked_on: date | None = None
    product_url: HttpUrl | None = None
    is_test_data: bool = False
    active: bool = True
    frd_file: str | None = None  # measured/manufacturer FRD reference; readiness is derived from it, never typed in
    zma_file: str | None = None

    @model_validator(mode="after")
    def check_driver(self) -> LibraryEntry:
        if self.category == "drivers" and self.driver is None and not self.source:
            raise ValueError("Katalogeintrag ohne T/S-Daten benötigt eine Quelle.")
        if self.driver is not None and self.price_eur is not None:
            self.driver = self.driver.model_copy(update={"price": self.price_eur,
                "currency": "EUR", "product_url": self.product_url or self.driver.product_url})
        return self

    def display(self) -> str:
        return f"{self.manufacturer} {self.model}".strip()


def _bundled_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return base / "data" / "library"


def _user_root() -> Path:
    return user_data_dir() / "library"


class ComponentLibrary:
    def __init__(self, bundled_root: Path | None = None, user_root: Path | None = None) -> None:
        self.bundled_root = bundled_root or _bundled_root()
        self.user_root = user_root or _user_root()
        self._items: dict[str, LibraryEntry] = {}
        self.reload()

    def reload(self) -> None:
        self._items.clear()
        for root in (self.bundled_root, self.user_root):
            for category in CATEGORIES:
                folder = root / category
                if not folder.is_dir():
                    continue
                for file in sorted((*folder.glob("*.json"), *folder.glob("*.csv"))):
                    for entry in self._read_file(file, category):
                        self._items[entry.id] = entry
        inactive = self.user_root / "inactive.json"
        if inactive.is_file():
            for key in json.loads(inactive.read_text(encoding="utf-8")):
                if key in self._items:
                    self._items[key] = self._items[key].model_copy(update={"active": False})

    @staticmethod
    def _read_file(path: Path, category: Category) -> tuple[LibraryEntry, ...]:
        records: list[Any]
        if path.suffix.lower() == ".json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            loaded = raw.get("components", raw.get("drivers", [])) if isinstance(raw, dict) else raw
            if not isinstance(loaded, list):
                raise ValueError(f"{path.name}: Katalogdatei muss eine Liste von Komponenten enthalten.")
            records = loaded
        else:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                records = list(csv.DictReader(stream, delimiter=";"))
            if category == "drivers" and records and "vas_l" in records[0]:
                records = [driver.model_dump(mode="json") for driver in DriverCatalog.load_csv(path).drivers]
        result = []
        for index, raw in enumerate(records):
            if category == "drivers" and "driver" not in raw and "category" not in raw:
                driver = Driver.model_validate({key: value for key, value in raw.items()
                                                if value not in (None, "")})
                key = f"driver:{driver.manufacturer}:{driver.model}".casefold()
                result.append(LibraryEntry(id=key, category="drivers", manufacturer=driver.manufacturer,
                    model=driver.model, driver=driver, source=driver.source_name or str(path.name),
                    is_test_data=driver.manufacturer == "TESTDATEN"))
            else:
                data = dict(raw)
                for field in ("driver", "specs"):
                    if field in data and isinstance(data[field], str) and data[field].strip():
                        data[field] = json.loads(data[field])
                data.setdefault("category", category)
                data.setdefault("id", f"{category}:{path.stem}:{index}")
                result.append(LibraryEntry.model_validate(data))
        return tuple(result)

    def entries(self, category: Category | None = None, query: str = "",
                include_inactive: bool = False) -> tuple[LibraryEntry, ...]:
        needle = query.casefold().strip()
        return tuple(sorted((item for item in self._items.values()
            if (category is None or item.category == category)
            and (include_inactive or item.active)
            and (not needle or needle in f"{item.display()} {item.id}".casefold())),
            key=lambda item: (item.category, item.display().casefold())))

    def drivers(self, *types: str) -> tuple[Driver, ...]:
        return tuple(item.driver for item in self.entries("drivers")
                     if item.driver is not None and (not types or item.driver.driver_type in types))

    def import_file(self, path: Path, category: Category) -> int:
        records = self._read_file(path, category)
        if not records:
            raise ValueError("Die Datei enthält keine Komponenten.")
        for item in records:
            self.upsert(item)
        return len(records)

    def upsert(self, item: LibraryEntry) -> None:
        folder = self.user_root / item.category
        folder.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() else "_" for ch in item.id)
        (folder / f"{safe}.json").write_text(
            json.dumps([item.model_dump(mode="json")], ensure_ascii=False, indent=2), encoding="utf-8")
        self.reload()

    def set_active(self, key: str, active: bool) -> None:
        if key not in self._items:
            raise KeyError(key)
        inactive = {item.id for item in self._items.values() if not item.active}
        if active:
            inactive.discard(key)
        else:
            inactive.add(key)
        self.user_root.mkdir(parents=True, exist_ok=True)
        (self.user_root / "inactive.json").write_text(
            json.dumps(sorted(inactive), ensure_ascii=False, indent=2), encoding="utf-8")
        self.reload()
