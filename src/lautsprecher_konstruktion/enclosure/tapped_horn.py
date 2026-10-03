"""Two-run tapped horn with the driver in the first internal fold."""
from __future__ import annotations

from dataclasses import dataclass
from math import pi

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.rectangular import CabinetDimensions, CutPanel


@dataclass(frozen=True)
class TappedHorn:
    upper_height_m: float
    lower_height_m: float
    turn_gap_m: float
    baffle_length_m: float
    driver_depth_from_front_m: float
    path_length_m: float
    quarter_wave_hz: float
    mouth_width_m: float
    mouth_height_m: float
    panel: CutPanel


def design_tapped_horn(cabinet: CabinetDimensions, driver: Driver) -> TappedHorn:
    t=cabinet.panel_thickness_m
    diameter=driver.outer_diameter_m or driver.cutout_diameter_m
    cutout=driver.cutout_diameter_m
    if diameter is None or cutout is None:
        raise ValueError('Tapped-Horn benötigt Außen- und Ausschnittdurchmesser des Treibers')
    gap=max(0.035,min(0.07,cabinet.internal_height_m*0.08))
    length=cabinet.internal_depth_m-gap
    if length<diameter+0.02 or cabinet.internal_width_m<diameter+0.02:
        raise ValueError('Tapped-Horn: F1 zu kurz oder schmal für Treiber und 10 mm Randabstand')
    bolt_span=(driver.bolt_circle_diameter_m or 0)+(driver.bolt_hole_diameter_m or 0)
    if bolt_span and (bolt_span+0.02>length or bolt_span+0.02>cabinet.internal_width_m):
        raise ValueError('Tapped-Horn: Treiber-Lochkreis liegt zu nah an der F1-Kante')
    available=cabinet.internal_height_m-t
    upper=max((driver.mounting_depth_m or 0)+0.025,available*0.42)
    lower=available-upper
    if upper<(driver.mounting_depth_m or 0)+0.015 or lower<0.045:
        raise ValueError('Tapped-Horn: Kanalhöhe reicht für Magnet oder unteren Hornlauf nicht')
    mouth_w=cabinet.internal_width_m-0.02
    mouth_h=lower-0.02
    if mouth_w<=0 or mouth_h<=0:
        raise ValueError('Tapped-Horn-Mündung passt nicht in den unteren Kanal')
    path=2*(cabinet.internal_depth_m-gap)+(upper+lower)/2+gap
    panel=CutPanel('Tapped-Horn F1 mit Treiberausschnitt',1,
                   cabinet.internal_width_m,length,t)
    return TappedHorn(upper,lower,gap,length,length/2,path,343/(4*path),
                      mouth_w,mouth_h,panel)


def tapped_baffle_displacement_m3(horn: TappedHorn, driver: Driver) -> float:
    assert driver.cutout_diameter_m is not None
    return (horn.panel.width_m*horn.panel.height_m-
            pi*(driver.cutout_diameter_m/2)**2)*horn.panel.thickness_m
