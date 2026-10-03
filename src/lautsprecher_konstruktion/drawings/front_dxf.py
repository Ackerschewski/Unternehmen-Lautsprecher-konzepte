from __future__ import annotations

from lautsprecher_konstruktion.enclosure.isobaric import Coupler
from lautsprecher_konstruktion.enclosure.layout import FrontElement, bolt_holes
from lautsprecher_konstruktion.enclosure.ports import PortDesign
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions


def _pair(code: int, value: object) -> str:
    return f"{code}\n{value}\n"


def render_coupler_ring_dxf(coupler: Coupler) -> str:
    """Concentric ring profile in millimetres; hole pattern needs field verification."""
    center = coupler.outer_diameter_m*500
    circles = "".join(
        _pair(0,"CIRCLE")+_pair(8,layer)+_pair(10,center)+_pair(20,center)+_pair(40,radius)
        for layer,radius in (("OUTER",center),("CUTOUT_DRIVER",coupler.driver_cutout_m*500))
    )
    return (_pair(0,"SECTION")+_pair(2,"HEADER")+_pair(0,"ENDSEC")+
            _pair(0,"SECTION")+_pair(2,"ENTITIES")+circles+
            _pair(0,"ENDSEC")+_pair(0,"EOF"))


def render_front_panel_dxf(
    cabinet: CabinetDimensions,
    *,
    driver_cutout_diameter_m: float | None = None,
    port: PortDesign | None = None,
    front_elements: tuple[FrontElement, ...] = (),
    surface: str = "front",
) -> str:
    """Minimal ASCII DXF R12 panel geometry in millimetres."""
    if surface not in {"front", "back", "partition"}:
        raise ValueError("unknown panel surface")
    w = (cabinet.internal_width_m if surface == "partition" else cabinet.width_m) * 1000.0
    h = (cabinet.internal_height_m if surface == "partition" else cabinet.height_m) * 1000.0
    elements = tuple(e for e in front_elements if e.surface == surface)
    entities: list[str] = []

    def line(x1: float, y1: float, x2: float, y2: float, layer: str = "CUT") -> None:
        entities.append(
            _pair(0, "LINE") + _pair(8, layer)
            + _pair(10, x1) + _pair(20, y1)
            + _pair(11, x2) + _pair(21, y2)
        )

    line(0, 0, w, 0, "PANEL")
    line(w, 0, w, h, "PANEL")
    line(w, h, 0, h, "PANEL")
    line(0, h, 0, 0, "PANEL")

    if elements:
        for element in elements:
            x = element.x_m*1000-(cabinet.panel_thickness_m*1000 if surface == "partition" else 0)
            y = element.y_m*1000-(cabinet.bottom_thickness_m or cabinet.panel_thickness_m)*1000 if surface == "partition" else element.y_m*1000
            layer = "CUTOUT_PORT" if element.type == "port" else "CUTOUT_DRIVER"
            if element.outer_diameter_m is not None:
                radius = (element.cutout_diameter_m or element.outer_diameter_m)*500
                entities.append(_pair(0,"CIRCLE")+_pair(8,layer)+_pair(10,x)+_pair(20,y)+_pair(40,radius))
            else:
                ew, eh = element.width*1000/2, element.height*1000/2
                line(x-ew,y-eh,x+ew,y-eh,layer)
                line(x+ew,y-eh,x+ew,y+eh,layer)
                line(x+ew,y+eh,x-ew,y+eh,layer)
                line(x-ew,y+eh,x-ew,y-eh,layer)
            for hx,hy,hr in bolt_holes(element):
                dx = hx*1000-(cabinet.panel_thickness_m*1000 if surface == "partition" else 0)
                dy = hy*1000-(cabinet.bottom_thickness_m or cabinet.panel_thickness_m)*1000 if surface == "partition" else hy*1000
                entities.append(_pair(0,"CIRCLE")+_pair(8,"DRILL")+_pair(10,dx)+_pair(20,dy)+_pair(40,hr*1000))
    elif surface == "front" and not front_elements and driver_cutout_diameter_m:
        dia = driver_cutout_diameter_m * 1000.0
        entities.append(
            _pair(0, "CIRCLE") + _pair(8, "CUT")
            + _pair(10, w / 2.0) + _pair(20, h * 0.62)
            + _pair(40, dia / 2.0)
        )

    if surface == "front" and port is not None and not front_elements:
        if port.shape == "round" and port.diameter_m:
            dia = port.diameter_m * 1000.0
            entities.append(
            _pair(0, "CIRCLE") + _pair(8, "CUTOUT_PORT")
                + _pair(10, w / 2.0) + _pair(20, max(dia / 2.0 + 18.0, h * 0.12))
                + _pair(40, dia / 2.0)
            )
        elif port.shape == "slot" and port.width_m and port.height_m:
            pw = port.width_m * 1000.0
            ph = port.height_m * 1000.0
            x = (w - pw) / 2.0
            y = 18.0
            line(x, y, x + pw, y)
            line(x + pw, y, x + pw, y + ph)
            line(x + pw, y + ph, x, y + ph)
            line(x, y + ph, x, y)

    return (
        _pair(0, "SECTION") + _pair(2, "HEADER") + _pair(0, "ENDSEC")
        + _pair(0, "SECTION") + _pair(2, "ENTITIES")
        + "".join(entities)
        + _pair(0, "ENDSEC") + _pair(0, "EOF")
    )
