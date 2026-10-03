"""R12 DXF outlines for a pair of trapezoid patterns, dimensions in mm."""
from __future__ import annotations

from lautsprecher_konstruktion.enclosure.front_horn import FrontHorn


def render_horn_trapezoid_dxf(horn: FrontHorn, kind: str) -> str:
    if kind == "top_bottom":
        throat=horn.throat_width_m*1000
        mouth=horn.mouth_width_m*1000
        slant=horn.panels[0].height_m*1000
    elif kind == "sides":
        throat=horn.throat_height_m*1000
        mouth=horn.mouth_height_m*1000
        slant=horn.panels[1].height_m*1000
    else:
        raise ValueError("Unknown horn panel")
    points=((0.0,(mouth-throat)/2),(0.0,(mouth+throat)/2),
            (slant,mouth),(slant,0.0))
    lines=[]
    for (x1,y1),(x2,y2) in zip(points,points[1:]+points[:1],strict=True):
        lines.extend(("0","LINE","8","CUT_TRAPEZOID","10",f"{x1:.3f}",
                      "20",f"{y1:.3f}","11",f"{x2:.3f}","21",f"{y2:.3f}"))
    header=("0","SECTION","2","HEADER","9","$INSUNITS","70","4",
            "0","ENDSEC","0","SECTION","2","ENTITIES")
    tail=("0","ENDSEC","0","EOF")
    return "\n".join((*header,*lines,*tail))+"\n"
