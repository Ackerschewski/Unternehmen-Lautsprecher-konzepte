"""R12 DXF outlines of the front-horn section trapezoids (side by side), dimensions in mm."""
from __future__ import annotations

from lautsprecher_konstruktion.enclosure.front_horn import FrontHorn


def render_horn_trapezoid_dxf(horn: FrontHorn, kind: str) -> str:
    if kind == "top_bottom":
        borders, offset = horn.section_widths_m, 0
    elif kind == "sides":
        borders, offset = horn.section_heights_m, 1
    else:
        raise ValueError("Unknown horn panel")
    lines: list[str] = []
    ox = 0.0
    for index in range(len(borders)-1):
        throat, mouth = borders[index]*1000, borders[index+1]*1000
        slant = horn.panels[2*index+offset].height_m*1000
        points = ((ox, (mouth-throat)/2), (ox, (mouth+throat)/2), (ox+slant, mouth), (ox+slant, 0.0))
        for (x1, y1), (x2, y2) in zip(points, points[1:]+points[:1], strict=True):
            lines.extend(("0", "LINE", "8", "CUT_TRAPEZOID", "10", f"{x1:.3f}",
                          "20", f"{y1:.3f}", "11", f"{x2:.3f}", "21", f"{y2:.3f}"))
        ox += slant+30.0
    header = ("0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4",
              "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES")
    tail = ("0", "ENDSEC", "0", "EOF")
    return "\n".join((*header, *lines, *tail))+"\n"
