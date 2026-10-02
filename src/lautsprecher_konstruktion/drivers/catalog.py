from __future__ import annotations

import csv
import json
from pathlib import Path

from lautsprecher_konstruktion.drivers.models import Driver


class DriverCatalog:
    def __init__(self, drivers: list[Driver] | None = None) -> None:
        self._drivers = list(drivers or [])

    @property
    def drivers(self) -> tuple[Driver, ...]:
        return tuple(self._drivers)

    def add(self, driver: Driver) -> None:
        key = (driver.manufacturer.casefold(), driver.model.casefold())
        for index, existing in enumerate(self._drivers):
            existing_key = (existing.manufacturer.casefold(), existing.model.casefold())
            if existing_key == key:
                self._drivers[index] = driver
                return
        self._drivers.append(driver)

    def search(self, text: str) -> tuple[Driver, ...]:
        needle = text.strip().casefold()
        if not needle:
            return self.drivers
        return tuple(
            driver
            for driver in self._drivers
            if needle in f"{driver.manufacturer} {driver.model}".casefold()
        )

    @classmethod
    def load_json(cls, path: str | Path) -> DriverCatalog:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = raw["drivers"] if isinstance(raw, dict) else raw
        return cls([Driver.model_validate(item) for item in records])

    def save_json(self, path: str | Path) -> None:
        data = {"drivers": [driver.model_dump(mode="json") for driver in self._drivers]}
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load_csv(cls, path: str | Path) -> DriverCatalog:
        drivers: list[Driver] = []
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                drivers.append(
                    Driver(
                        manufacturer=row["manufacturer"],
                        model=row["model"],
                        fs_hz=float(row["fs_hz"]),
                        qts=float(row["qts"]),
                        vas_m3=float(row["vas_l"]) / 1000.0,
                        qes=_optional_float(row.get("qes")),
                        qms=_optional_float(row.get("qms")),
                        re_ohm=_optional_float(row.get("re_ohm")),
                        le_h=_optional_mh(row.get("le_mh")),
                        sd_m2=_optional_cm2(row.get("sd_cm2")),
                        xmax_m=_optional_mm(row.get("xmax_mm")),
                        power_rms_w=_optional_float(row.get("power_rms_w")),
                        displacement_m3=(_optional_float(row.get("displacement_l")) or 0.0) / 1000.0,
                        nominal_impedance_ohm=_optional_float(row.get("nominal_impedance_ohm")),
                        cutout_diameter_m=_optional_mm(row.get("cutout_diameter_mm")),
                        mounting_depth_m=_optional_mm(row.get("mounting_depth_mm")),
                        source_name=row.get("source_name") or None,
                        source_document=row.get("source_document") or None,
                    )
                )
        return cls(drivers)


def _optional_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    return float(value.replace(",", "."))


def _optional_mm(value: str | None) -> float | None:
    parsed = _optional_float(value)
    return None if parsed is None else parsed / 1000.0


def _optional_cm2(value: str | None) -> float | None:
    parsed = _optional_float(value)
    return None if parsed is None else parsed / 10_000.0


def _optional_mh(value: str | None) -> float | None:
    parsed = _optional_float(value)
    return None if parsed is None else parsed / 1000.0
