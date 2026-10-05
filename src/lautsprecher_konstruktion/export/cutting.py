"""Sheet-stock cutting optimisation for the cabinet panels.

The packer places rectangular parts on stock sheets with guillotine cuts, which
matches table-saw and panel-saw work. Every part is planned with its bounding
rectangle, so trapezoid and round parts are conservative. The saw kerf is
reserved on the right and bottom of every part. All lengths are in millimetres
here because shop drawings and sheet sizes are quoted in millimetres; the
project model itself stays in SI units.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from lautsprecher_konstruktion.services.design import DesignBundle

# Conservative retail sheet sizes. They are planning assumptions, not supplier data.
DEFAULT_STOCK_MM: dict[str, tuple[float, float]] = {
    "Birke Multiplex": (2500.0, 1250.0),
    "MDF": (2440.0, 1220.0),
    "Spanplatte": (2440.0, 1220.0),
}
FALLBACK_STOCK_MM = (2500.0, 1250.0)
DEFAULT_KERF_MM = 3.0
CONTOUR_HINTS = ("trapez", "ring", "isobarik", "koppel")


@dataclass(frozen=True)
class CuttingSettings:
    sheet_width_mm: float
    sheet_height_mm: float
    kerf_mm: float = DEFAULT_KERF_MM
    allow_rotation: bool = True
    trim_mm: float = 0.0

    def __post_init__(self) -> None:
        if min(self.sheet_width_mm, self.sheet_height_mm) <= 0:
            raise ValueError("Plattenmaße müssen positiv sein.")
        if self.kerf_mm < 0 or self.trim_mm < 0:
            raise ValueError("Sägeschnitt und Besäumung dürfen nicht negativ sein.")
        if 2 * self.trim_mm >= min(self.sheet_width_mm, self.sheet_height_mm):
            raise ValueError("Die Besäumung lässt keine nutzbare Plattenfläche übrig.")

    @classmethod
    def for_material(cls, material: str, *, kerf_mm: float = DEFAULT_KERF_MM,
                     allow_rotation: bool = True, trim_mm: float = 0.0) -> CuttingSettings:
        width, height = DEFAULT_STOCK_MM.get(material, FALLBACK_STOCK_MM)
        return cls(width, height, kerf_mm, allow_rotation, trim_mm)


@dataclass(frozen=True)
class Part:
    part_id: str
    name: str
    width_mm: float
    height_mm: float
    thickness_mm: float
    contour_note: bool = False

    @property
    def area_mm2(self) -> float:
        return self.width_mm * self.height_mm


@dataclass(frozen=True)
class PlacedPart:
    part: Part
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    rotated: bool


@dataclass(frozen=True)
class SheetLayout:
    index: int
    placed: tuple[PlacedPart, ...]
    used_area_mm2: float
    largest_offcut_mm2: float


@dataclass(frozen=True)
class ThicknessPlan:
    thickness_mm: float
    settings: CuttingSettings
    sheets: tuple[SheetLayout, ...]
    unplaced: tuple[Part, ...]

    @property
    def part_area_mm2(self) -> float:
        return sum(sheet.used_area_mm2 for sheet in self.sheets)

    @property
    def sheet_area_mm2(self) -> float:
        return len(self.sheets) * self.settings.sheet_width_mm * self.settings.sheet_height_mm

    @property
    def waste_percent(self) -> float:
        total = self.sheet_area_mm2
        return 0.0 if total == 0 else 100.0 * (1.0 - self.part_area_mm2 / total)


@dataclass(frozen=True)
class CuttingPlan:
    material: str
    groups: tuple[ThicknessPlan, ...]

    @property
    def sheet_count(self) -> int:
        return sum(len(group.sheets) for group in self.groups)

    @property
    def unplaced(self) -> tuple[Part, ...]:
        return tuple(part for group in self.groups for part in group.unplaced)

    @property
    def feasible(self) -> bool:
        return not self.unplaced

    @property
    def waste_percent(self) -> float:
        total = sum(group.sheet_area_mm2 for group in self.groups)
        used = sum(group.part_area_mm2 for group in self.groups)
        return 0.0 if total == 0 else 100.0 * (1.0 - used / total)

    @property
    def warnings(self) -> tuple[str, ...]:
        notes = [f"{part.name} ({part.width_mm:.0f} × {part.height_mm:.0f} mm) passt auf keine Platte."
                 for part in self.unplaced]
        if any(part.contour_note for group in self.groups for sheet in group.sheets
               for part in (placed.part for placed in sheet.placed)):
            notes.append("Trapez-, Ring- und Rundteile sind als umschreibendes Rechteck eingeplant; "
                         "echter Verschnitt kann kleiner ausfallen.")
        return tuple(notes)


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

def collect_parts(bundle: DesignBundle) -> tuple[Part, ...]:
    """Expand the bundle's panel list (including braces) into single pieces."""
    parts: list[Part] = []
    counter = 0

    def add(name: str, quantity: int, width_m: float, height_m: float, thickness_m: float) -> None:
        nonlocal counter
        for piece in range(1, quantity + 1):
            counter += 1
            label = name if quantity == 1 else f"{name} {piece}/{quantity}"
            parts.append(Part(f"P{counter:02d}", label, round(width_m * 1000, 1),
                              round(height_m * 1000, 1), round(thickness_m * 1000, 1),
                              any(hint in name.casefold() for hint in CONTOUR_HINTS)))

    for panel in bundle.panels:
        add(panel.name, panel.quantity, panel.width_m, panel.height_m, panel.thickness_m)
    if bundle.brace:
        brace = bundle.brace
        add("Fensterstrebe", brace.quantity, brace.outer_width_m, brace.outer_height_m,
            brace.thickness_m)
    return tuple(parts)


# ---------------------------------------------------------------------------
# Guillotine packer
# ---------------------------------------------------------------------------

@dataclass
class _Free:
    x: float
    y: float
    w: float
    h: float


@dataclass
class _Sheet:
    free: list[_Free]
    placed: list[PlacedPart]


_SORTS = {
    "area": lambda p: (-p.area_mm2, -max(p.width_mm, p.height_mm), p.part_id),
    "longest": lambda p: (-max(p.width_mm, p.height_mm), -p.area_mm2, p.part_id),
    "width": lambda p: (-p.width_mm, -p.height_mm, p.part_id),
    "height": lambda p: (-p.height_mm, -p.width_mm, p.part_id),
}
_FITS = ("short_side", "area")
_SPLITS = ("shorter_axis", "longer_axis", "min_area", "max_area")


def _score(free: _Free, w: float, h: float, fit: str) -> tuple[float, float]:
    if fit == "area":
        return (free.w * free.h - w * h, min(free.w - w, free.h - h))
    return (min(free.w - w, free.h - h), max(free.w - w, free.h - h))


def _split(free: _Free, w: float, h: float, rule: str) -> list[_Free]:
    """Split the space left around a placed w x h part into two free rectangles."""
    right_w, below_h = free.w - w, free.h - h
    horizontal_largest = max(free.w * below_h, right_w * h)  # full-width strip below
    vertical_largest = max(right_w * free.h, w * below_h)    # full-height strip right
    if rule == "shorter_axis":
        horizontal = free.w < free.h
    elif rule == "longer_axis":
        horizontal = free.w >= free.h
    elif rule == "min_area":
        horizontal = horizontal_largest <= vertical_largest
    else:  # max_area
        horizontal = horizontal_largest >= vertical_largest
    if horizontal:
        pieces = [_Free(free.x, free.y + h, free.w, below_h), _Free(free.x + w, free.y, right_w, h)]
    else:
        pieces = [_Free(free.x + w, free.y, right_w, free.h), _Free(free.x, free.y + h, w, below_h)]
    return [piece for piece in pieces if piece.w > 1e-6 and piece.h > 1e-6]


def _pack(parts: tuple[Part, ...], settings: CuttingSettings, sort: str, fit: str,
          split: str) -> list[_Sheet]:
    kerf = settings.kerf_mm
    usable_w = settings.sheet_width_mm - 2 * settings.trim_mm + kerf
    usable_h = settings.sheet_height_mm - 2 * settings.trim_mm + kerf
    sheets: list[_Sheet] = []
    for part in sorted(parts, key=_SORTS[sort]):
        options = [(part.width_mm, part.height_mm, False)]
        if settings.allow_rotation and part.width_mm != part.height_mm:
            options.append((part.height_mm, part.width_mm, True))
        best: tuple[tuple[float, float], _Sheet, _Free, float, float, bool] | None = None
        for sheet in sheets:
            for free in sheet.free:
                for width, height, rotated in options:
                    if width + kerf <= free.w + 1e-9 and height + kerf <= free.h + 1e-9:
                        score = _score(free, width + kerf, height + kerf, fit)
                        if best is None or score < best[0]:
                            best = (score, sheet, free, width, height, rotated)
        if best is None:
            fits_empty = [(w, h, r) for w, h, r in options if w + kerf <= usable_w and h + kerf <= usable_h]
            if not fits_empty:
                continue  # reported as unplaced by the caller
            sheet = _Sheet([_Free(0.0, 0.0, usable_w, usable_h)], [])
            sheets.append(sheet)
            free = sheet.free[0]
            width, height, rotated = min(fits_empty, key=lambda o: _score(free, o[0] + kerf, o[1] + kerf, fit))
            best = (_score(free, width + kerf, height + kerf, fit), sheet, free, width, height, rotated)
        _, sheet, free, width, height, rotated = best
        sheet.placed.append(PlacedPart(part, settings.trim_mm + free.x, settings.trim_mm + free.y,
                                       width, height, rotated))
        sheet.free.remove(free)
        sheet.free.extend(_split(free, width + kerf, height + kerf, split))
    return sheets


def _plan_thickness(parts: tuple[Part, ...], settings: CuttingSettings) -> ThicknessPlan:
    thickness = parts[0].thickness_mm
    best: list[_Sheet] | None = None
    best_key: tuple[int, float] | None = None
    for sort, fit, split in product(_SORTS, _FITS, _SPLITS):
        sheets = _pack(parts, settings, sort, fit, split)
        largest = max((max((f.w * f.h for f in sheet.free), default=0.0) for sheet in sheets[-1:]),
                      default=0.0)
        key = (len(sheets), -largest)
        if best_key is None or key < best_key:
            best, best_key = sheets, key
    assert best is not None
    placed_ids = {item.part.part_id for sheet in best for item in sheet.placed}
    unplaced = tuple(part for part in parts if part.part_id not in placed_ids)
    layouts = tuple(
        SheetLayout(index=i + 1, placed=tuple(sheet.placed),
                    used_area_mm2=sum(item.width_mm * item.height_mm for item in sheet.placed),
                    largest_offcut_mm2=max((f.w * f.h for f in sheet.free), default=0.0))
        for i, sheet in enumerate(best))
    return ThicknessPlan(thickness, settings, layouts, unplaced)


def plan_cutting(bundle: DesignBundle, settings: CuttingSettings | None = None) -> CuttingPlan:
    """Distribute all panels on stock sheets, one stock group per panel thickness."""
    material = bundle.project.material
    settings = settings or CuttingSettings.for_material(material)
    by_thickness: dict[float, list[Part]] = defaultdict(list)
    for part in collect_parts(bundle):
        by_thickness[part.thickness_mm].append(part)
    groups = tuple(_plan_thickness(tuple(by_thickness[t]), settings) for t in sorted(by_thickness))
    return CuttingPlan(material, groups)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_cutting_csv(path: str | Path, plan: CuttingPlan) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Dicke_mm", "Platte", "Teil", "Bezeichnung", "X_mm", "Y_mm",
                         "Breite_mm", "Höhe_mm", "Gedreht", "Hinweis"])
        for group in plan.groups:
            for sheet in group.sheets:
                for item in sheet.placed:
                    writer.writerow([f"{group.thickness_mm:.1f}", sheet.index, item.part.part_id,
                                     item.part.name, f"{item.x_mm:.1f}", f"{item.y_mm:.1f}",
                                     f"{item.width_mm:.1f}", f"{item.height_mm:.1f}",
                                     "ja" if item.rotated else "nein",
                                     "Umschreibendes Rechteck" if item.part.contour_note else ""])
            for part in group.unplaced:
                writer.writerow([f"{group.thickness_mm:.1f}", "", part.part_id, part.name, "", "",
                                 f"{part.width_mm:.1f}", f"{part.height_mm:.1f}", "",
                                 "passt auf keine Platte"])


def render_cutting_svg(plan: CuttingPlan, group_index: int, sheet_index: int) -> str:
    """One stock sheet as SVG; origin top-left, x to the right, y downwards."""
    group = plan.groups[group_index]
    sheet = group.sheets[sheet_index]
    cfg = group.settings
    scale = 1000.0 / cfg.sheet_width_mm
    width, height = cfg.sheet_width_mm * scale, cfg.sheet_height_mm * scale
    margin_top = 56
    used_percent = 100 * (1 - sheet.used_area_mm2 / (cfg.sheet_width_mm * cfg.sheet_height_mm))
    out = [
        (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width + 40:.0f} {height + margin_top + 40:.0f}" '
         f'width="{width + 40:.0f}" height="{height + margin_top + 40:.0f}" font-family="DejaVu Sans, Arial">'),
        (f'<text x="20" y="26" font-size="16" font-weight="bold">{plan.material} {group.thickness_mm:.0f} mm · '
         f'Platte {sheet.index}/{len(group.sheets)} ({cfg.sheet_width_mm:.0f} × {cfg.sheet_height_mm:.0f} mm)</text>'),
        (f'<text x="20" y="44" font-size="11" fill="#555">Sägeschnitt {cfg.kerf_mm:g} mm · '
         f'Verschnitt dieser Platte {used_percent:.1f} %</text>'),
        (f'<rect x="20" y="{margin_top}" width="{width:.1f}" height="{height:.1f}" fill="#f4efe6" '
         'stroke="#333" stroke-width="2"/>'),
    ]
    for item in sheet.placed:
        x, y = 20 + item.x_mm * scale, margin_top + item.y_mm * scale
        w, h = item.width_mm * scale, item.height_mm * scale
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#cfe3ee" '
                   f'stroke="#166b91" stroke-width="1.5"/>')
        size = max(8.0, min(13.0, w / 12, h / 3))
        label = f"{item.part.part_id} {item.part.name}"
        out.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2 - 3:.1f}" font-size="{size:.1f}" text-anchor="middle" '
                   f'fill="#172735">{_esc(label[:int(w / (size * 0.6)) + 1])}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + size:.1f}" font-size="{size:.1f}" '
                   f'text-anchor="middle" fill="#172735">{item.width_mm:.0f} × {item.height_mm:.0f}'
                   f'{" ↻" if item.rotated else ""}</text>')
    out.append("</svg>")
    return "\n".join(out)


def _dxf_pair(code: int, value: object) -> str:
    return f"{code}\n{value}\n"


def render_cutting_dxf(plan: CuttingPlan, group_index: int, sheet_index: int) -> str:
    """One stock sheet as ASCII DXF R12 in millimetres, origin bottom-left, for CNC and panel-saw services.

    Layers: SHEET (stock outline), PARTS (part outlines), TEXT (part id and size).
    """
    group = plan.groups[group_index]
    sheet = group.sheets[sheet_index]
    cfg = group.settings
    entities: list[str] = []

    def rectangle(x: float, y: float, w: float, h: float, layer: str) -> None:
        for (x1, y1), (x2, y2) in (((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)),
                                   ((x + w, y + h), (x, y + h)), ((x, y + h), (x, y))):
            entities.append(_dxf_pair(0, "LINE") + _dxf_pair(8, layer) + _dxf_pair(10, f"{x1:.3f}")
                            + _dxf_pair(20, f"{y1:.3f}") + _dxf_pair(30, 0) + _dxf_pair(11, f"{x2:.3f}")
                            + _dxf_pair(21, f"{y2:.3f}") + _dxf_pair(31, 0))

    rectangle(0.0, 0.0, cfg.sheet_width_mm, cfg.sheet_height_mm, "SHEET")
    for item in sheet.placed:
        y = cfg.sheet_height_mm - item.y_mm - item.height_mm  # scene y points down, DXF y up
        rectangle(item.x_mm, y, item.width_mm, item.height_mm, "PARTS")
        label = f"{item.part.part_id} {item.width_mm:.0f}x{item.height_mm:.0f}".replace("\n", " ")
        entities.append(_dxf_pair(0, "TEXT") + _dxf_pair(8, "TEXT") + _dxf_pair(10, f"{item.x_mm + 10:.3f}")
                        + _dxf_pair(20, f"{y + item.height_mm / 2:.3f}") + _dxf_pair(30, 0)
                        + _dxf_pair(40, f"{min(30.0, item.width_mm / 10):.1f}") + _dxf_pair(1, label))
    return (_dxf_pair(0, "SECTION") + _dxf_pair(2, "HEADER") + _dxf_pair(0, "ENDSEC")
            + _dxf_pair(0, "SECTION") + _dxf_pair(2, "ENTITIES") + "".join(entities)
            + _dxf_pair(0, "ENDSEC") + _dxf_pair(0, "EOF"))


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def summary_lines(plan: CuttingPlan) -> list[str]:
    lines = [f"Material: {plan.material} · {plan.sheet_count} Platte(n) · Verschnitt {plan.waste_percent:.1f} %"]
    for group in plan.groups:
        cfg = group.settings
        lines.append(f"{group.thickness_mm:.0f} mm: {len(group.sheets)} × {cfg.sheet_width_mm:.0f} × "
                     f"{cfg.sheet_height_mm:.0f} mm, Verschnitt {group.waste_percent:.1f} %")
    lines.extend(plan.warnings)
    return lines


def write_cutting_pdf(path: str | Path, plan: CuttingPlan, project_name: str) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.pdfgen.canvas import Canvas

    page_w, page_h = landscape(A3)
    canvas = Canvas(str(path), pagesize=(page_w, page_h))
    ink, blue = HexColor("#172735"), HexColor("#166b91")

    def header(title: str, number: int) -> None:
        canvas.setFillColor(ink)
        canvas.setFont("Helvetica-Bold", 19)
        canvas.drawString(42, page_h - 48, title)
        canvas.setStrokeColor(blue)
        canvas.setLineWidth(1.5)
        canvas.line(42, page_h - 60, page_w - 42, page_h - 60)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(42, 24, project_name[:90])
        canvas.drawRightString(page_w - 42, 24, str(number))

    page = 1
    header("Zuschnittplan – Übersicht", page)
    y = page_h - 100
    canvas.setFont("Helvetica", 11)
    for line in summary_lines(plan):
        canvas.drawString(42, y, line[:170])
        y -= 20
    y -= 10
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(42, y, "Teil")
    canvas.drawString(110, y, "Bezeichnung")
    canvas.drawString(520, y, "Maße [mm]")
    canvas.drawString(660, y, "Dicke")
    canvas.drawString(720, y, "Platte")
    y -= 18
    canvas.setFont("Helvetica", 9)
    for group in plan.groups:
        for sheet in group.sheets:
            for item in sheet.placed:
                if y < 50:
                    canvas.showPage()
                    page += 1
                    header("Zuschnittplan – Übersicht", page)
                    y = page_h - 100
                    canvas.setFont("Helvetica", 9)
                canvas.drawString(42, y, item.part.part_id)
                canvas.drawString(110, y, item.part.name[:70])
                canvas.drawString(520, y, f"{item.width_mm:.1f} × {item.height_mm:.1f}")
                canvas.drawString(660, y, f"{group.thickness_mm:.0f}")
                canvas.drawString(720, y, str(sheet.index))
                y -= 15
    canvas.showPage()
    for group in plan.groups:
        for sheet in group.sheets:
            page += 1
            header(f"Zuschnittplan – {group.thickness_mm:.0f} mm, Platte {sheet.index}", page)
            cfg = group.settings
            scale = min((page_w - 100) / cfg.sheet_width_mm, (page_h - 190) / cfg.sheet_height_mm)
            x0, y0 = 50, page_h - 100
            canvas.setFillColor(HexColor("#f4efe6"))
            canvas.setStrokeColor(ink)
            canvas.rect(x0, y0 - cfg.sheet_height_mm * scale, cfg.sheet_width_mm * scale,
                        cfg.sheet_height_mm * scale, fill=1, stroke=1)
            for item in sheet.placed:
                w, h = item.width_mm * scale, item.height_mm * scale
                px, py = x0 + item.x_mm * scale, y0 - item.y_mm * scale - h
                canvas.setFillColor(HexColor("#cfe3ee"))
                canvas.setStrokeColor(blue)
                canvas.rect(px, py, w, h, fill=1, stroke=1)
                canvas.setFillColor(ink)
                canvas.setFont("Helvetica", 8)
                canvas.drawCentredString(px + w / 2, py + h / 2 + 2, f"{item.part.part_id} {item.part.name}"[:max(6, int(w / 4.5))])
                canvas.drawCentredString(px + w / 2, py + h / 2 - 9, f"{item.width_mm:.0f} x {item.height_mm:.0f}")
            canvas.setFont("Helvetica", 9)
            canvas.drawString(42, 44, f"Sägeschnitt {cfg.kerf_mm:g} mm; Teile mit Trapez-/Rundkontur als Rechteck geplant.")
            canvas.showPage()
    canvas.save()
