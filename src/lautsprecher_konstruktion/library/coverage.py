"""Coverage report over the bundled component library (rendered to docs/application/LIBRARY_COVERAGE.md)."""
from __future__ import annotations

from collections import Counter

from lautsprecher_konstruktion.library.readiness import READINESS_LABELS_DE, Readiness, assess
from lautsprecher_konstruktion.library.store import ComponentLibrary, LibraryEntry


def _share(count: int, total: int) -> str:
    return f"{count} ({round(100 * count / total)} %)" if total else "0"


def _section(title: str, entries: list[LibraryEntry]) -> list[str]:
    total = len(entries)
    reports = [assess(e) for e in entries]
    complete = sum(1 for e, r in zip(entries, reports, strict=True) if e.driver is not None and r.coverage_percent == 100)
    lines = [f"## {title}", "", f"Chassis gesamt: **{total}**", "", "| Kriterium | Anzahl |", "|---|---|"]
    for kind in Readiness:
        lines.append(f"| {READINESS_LABELS_DE[kind]} (`{kind.value}`) | {_share(sum(r.ready(kind) for r in reports), total)} |")
    lines.append(f"| vollständige Herstellerdaten (alle Abdeckungsfelder) | {_share(complete, total)} |")
    drivers = sum(1 for e in entries if e.driver is not None)
    lines += ["", (f"Mit hinterlegten T/S-Daten: {_share(drivers, total)}. "
                  f"Reine Katalog-/Preiseinträge ohne Treiberdaten: {_share(total - drivers, total)}."), ""]
    missing: Counter[str] = Counter()
    for r in reports:
        missing.update(r.missing)
    if missing:
        lines += ["Häufigste Lücken:", ""] + [f"- {name}: {_share(n, total)} fehlen" for name, n in missing.most_common()] + [""]
    return lines


def coverage_markdown(library: ComponentLibrary) -> str:
    drivers = list(library.entries("drivers"))
    real = [e for e in drivers if not e.is_test_data]
    demo = [e for e in drivers if e.is_test_data]
    intro = ("Erzeugt aus `data/library` mit `python -m lautsprecher_konstruktion.library.coverage`. "
             "Alle Werte sind aus den gespeicherten Datensätzen abgeleitet; fehlende Felder werden nie ergänzt.")
    out = ["# Bibliotheks-Abdeckung", "", intro, ""]
    out += _section("Reale Herstellerdaten", real)
    out += _section("Demo-/Testdaten (getrennt, nicht Teil der realen Abdeckung)", demo)
    out += ["## Lesehinweise", "",
            ("- `crossover_ready` und `fullrange_ready` erfordern eine FRD- und eine ZMA-Datei am Eintrag. "
             "Ohne diese Dateien gilt keine Aussage über 20 Hz–20 kHz."),
            "- `three_d_ready` bedeutet nur: Außen-/Ausschnittsmaße und Einbautiefe reichen für eine vereinfachte Hüllgeometrie.",
            "- Preise gelten als geprüft nur mit Preis und Prüfdatum; sie sind Momentaufnahmen.", ""]
    return "\n".join(out)


if __name__ == "__main__":  # pragma: no cover - documentation helper
    from pathlib import Path

    target = Path(__file__).resolve().parents[3] / "docs" / "application" / "LIBRARY_COVERAGE.md"
    target.write_text(coverage_markdown(ComponentLibrary(user_root=Path("/nonexistent"))), encoding="utf-8")
    print(target)
