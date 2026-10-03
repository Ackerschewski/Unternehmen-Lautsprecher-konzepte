"""R12 machining drawing for the tapped horn F1 internal driver baffle."""
from __future__ import annotations

from math import cos, pi, sin

from lautsprecher_konstruktion.drivers.models import Driver
from lautsprecher_konstruktion.enclosure.tapped_horn import TappedHorn


def render_tapped_f1_dxf(horn: TappedHorn, driver: Driver) -> str:
    def pair(code: int, value: object) -> str:
        return f'{code}\n{value}\n'

    width=horn.panel.width_m*1000
    length=horn.panel.height_m*1000
    x,y=width/2,length/2
    entities=[]
    points=((0,0),(width,0),(width,length),(0,length))
    for (x1,y1),(x2,y2) in zip(points,points[1:]+points[:1],strict=True):
        entities.append(pair(0,'LINE')+pair(8,'PANEL')+pair(10,x1)+pair(20,y1)+
                        pair(11,x2)+pair(21,y2))
    assert driver.cutout_diameter_m is not None
    entities.append(pair(0,'CIRCLE')+pair(8,'CUTOUT_DRIVER')+
                    pair(10,x)+pair(20,y)+pair(40,driver.cutout_diameter_m*500))
    if (driver.bolt_count and driver.bolt_circle_diameter_m and
            driver.bolt_hole_diameter_m):
        radius=driver.bolt_circle_diameter_m*500
        for index in range(driver.bolt_count):
            angle=2*pi*index/driver.bolt_count
            entities.append(pair(0,'CIRCLE')+pair(8,'DRILL')+
                            pair(10,x+radius*cos(angle))+
                            pair(20,y+radius*sin(angle))+
                            pair(40,driver.bolt_hole_diameter_m*500))
    return (pair(0,'SECTION')+pair(2,'HEADER')+pair(9,'$INSUNITS')+
            pair(70,4)+pair(0,'ENDSEC')+pair(0,'SECTION')+
            pair(2,'ENTITIES')+''.join(entities)+pair(0,'ENDSEC')+pair(0,'EOF'))
