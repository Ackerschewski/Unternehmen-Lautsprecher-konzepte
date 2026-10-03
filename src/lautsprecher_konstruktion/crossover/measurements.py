"""FRD/ZMA measurements kept independent of the desktop UI."""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class FrequencyResponseData(BaseModel):
    frequencies_hz: tuple[float, ...]
    magnitude_db: tuple[float, ...]
    phase_deg: tuple[float, ...] | None = None
    source: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_points(self) -> FrequencyResponseData:
        n = len(self.frequencies_hz)
        if n < 2 or len(self.magnitude_db) != n or (self.phase_deg is not None and len(self.phase_deg) != n):
            raise ValueError("FRD needs at least two equally sized columns")
        if any(f <= 0 for f in self.frequencies_hz) or any(b <= a for a,b in zip(self.frequencies_hz, self.frequencies_hz[1:])):
            raise ValueError("FRD frequencies must increase strictly")
        return self


class ImpedanceData(BaseModel):
    frequencies_hz: tuple[float, ...]
    magnitude_ohm: tuple[float, ...]
    phase_deg: tuple[float, ...]
    source: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_points(self) -> ImpedanceData:
        n = len(self.frequencies_hz)
        if n < 2 or len(self.magnitude_ohm) != n or len(self.phase_deg) != n:
            raise ValueError("ZMA needs at least two equally sized columns")
        if any(f <= 0 for f in self.frequencies_hz) or any(b <= a for a,b in zip(self.frequencies_hz, self.frequencies_hz[1:])):
            raise ValueError("ZMA frequencies must increase strictly")
        if any(z <= 0 for z in self.magnitude_ohm):
            raise ValueError("ZMA impedance must be positive")
        return self


_SPLIT = re.compile(r"[\s;,]+")


def _parse_columns(text: str) -> tuple[list[list[float]], dict[str, str]]:
    rows: list[list[float]] = []
    metadata: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.startswith(("#", "*", "//", ";")):
            comment = line.lstrip("#*/; ").strip()
            if ":" in comment:
                key, value = comment.split(":", 1)
                metadata[key.strip()] = value.strip()
            continue
        line = re.split(r"\s+(?:#|//|;)", line, maxsplit=1)[0]
        values = _SPLIT.split(line.strip())
        try:
            numbers = [float(value) for value in values]
        except ValueError:
            # A textual column header is accepted only before the data begins.
            if rows:
                raise ValueError(f"invalid measurement row {lineno}: {raw}") from None
            continue
        if len(numbers) < 2 or len(numbers) > 3:
            raise ValueError(f"measurement row {lineno} needs two or three columns")
        rows.append(numbers)
    if len(rows) < 2:
        raise ValueError("measurement file needs at least two data rows")
    if len({len(row) for row in rows}) != 1:
        raise ValueError("measurement rows have inconsistent column counts")
    return rows, metadata


def parse_frd(text: str, source: str = "") -> FrequencyResponseData:
    rows, metadata = _parse_columns(text)
    return FrequencyResponseData(frequencies_hz=tuple(row[0] for row in rows),
        magnitude_db=tuple(row[1] for row in rows),
        phase_deg=tuple(row[2] for row in rows) if len(rows[0]) == 3 else None,
        source=source, metadata=metadata)


def parse_zma(text: str, source: str = "") -> ImpedanceData:
    rows, metadata = _parse_columns(text)
    if len(rows[0]) != 3:
        raise ValueError("ZMA requires frequency, magnitude and phase")
    return ImpedanceData(frequencies_hz=tuple(row[0] for row in rows),
        magnitude_ohm=tuple(row[1] for row in rows),
        phase_deg=tuple(row[2] for row in rows), source=source, metadata=metadata)


def load_frd(path: str | Path) -> FrequencyResponseData:
    path = Path(path)
    return parse_frd(path.read_text(encoding="utf-8-sig"), str(path))


def load_zma(path: str | Path) -> ImpedanceData:
    path = Path(path)
    return parse_zma(path.read_text(encoding="utf-8-sig"), str(path))
