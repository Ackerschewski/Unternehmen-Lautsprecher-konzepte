from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from lautsprecher_konstruktion.services.design import DesignBundle


@dataclass(frozen=True)
class BomItem:
    category: str
    reference: str
    description: str
    quantity: int
    specification: str
    notes: str = ""
    unit_price_eur: float | None = None
    price_source_url: str = ""
    price_kind: str = "retail"

    @property
    def line_total_eur(self) -> float | None:
        return None if self.unit_price_eur is None else self.quantity * self.unit_price_eur


def priced_subtotal(items: tuple[BomItem, ...]) -> tuple[float, int]:
    """Known subtotal and number of unpriced positions; never imply a complete quote."""
    return (sum(item.line_total_eur or 0 for item in items),
            sum(item.unit_price_eur is None for item in items))


def build_bom(bundle: DesignBundle) -> tuple[BomItem, ...]:
    project = bundle.project
    items: list[BomItem] = []

    for panel in bundle.panels:
        items.append(
            BomItem(
                category="Gehäuseplatten",
                reference=panel.name,
                description=project.material,
                quantity=panel.quantity,
                specification=(
                    f"{panel.width_m*1000:.1f} x {panel.height_m*1000:.1f} x "
                    f"{panel.thickness_m*1000:.1f} mm"
                ),
            )
        )

    if bundle.brace:
        b = bundle.brace
        items.append(
            BomItem(
                category="Versteifungen",
                reference="Brace",
                description=f"Fenster-Versteifung, {project.material}",
                quantity=b.quantity,
                specification=(
                    f"{b.outer_width_m*1000:.1f} x {b.outer_height_m*1000:.1f} x "
                    f"{b.thickness_m*1000:.1f} mm, Rand {b.border_m*1000:.1f} mm"
                ),
            )
        )

    items.append(
        BomItem(
            category="Treiber",
            reference="W1",
            description=f"{project.driver.manufacturer} {project.driver.model}",
            quantity=2 if bundle.coupler else 1,
            specification=f"{project.driver.nominal_impedance_ohm or '-'} Ohm",
            notes=project.driver.source_name or "",
            unit_price_eur=(project.driver.price if project.driver.currency == "EUR" else None),
            price_source_url=str(project.driver.product_url or ""),
        )
    )
    if bundle.coupler:
        k = bundle.coupler
        items.append(BomItem("Isobarik", "K1", "Luftdichtes Koppelrohr", 1,
            f"Innen Ø {k.inner_diameter_m*1000:.1f} × außen Ø {k.outer_diameter_m*1000:.1f} × Länge {k.length_m*1000:.1f} mm",
            ("W2 umgedreht montieren und elektrisch gegensinnig polen; Koppelvolumen luftdicht."
             if project.enclosure.enclosure_type == "compound_push_pull" else
             "Rohr/Verbindung luftdicht ausführen; beide Treiber phasenrichtig verschalten.")))
    if project.additional_drivers:
        for index, driver in enumerate(project.additional_drivers, start=1):
            items.append(BomItem("Treiber", f"T{index}" if driver.driver_type == "tweeter" else f"D{index}",
                f"{driver.manufacturer} {driver.model}", 1,
                f"{driver.nominal_impedance_ohm or '-'} Ohm", driver.source_name or "",
                driver.price if driver.currency == "EUR" else None,
                str(driver.product_url or "")))
    elif project.tweeter_name:
        items.append(
            BomItem(
                category="Treiber",
                reference="T1",
                description=project.tweeter_name,
                quantity=1,
                specification=f"{project.crossover.tweeter_impedance_ohm:g} Ohm",
            )
        )

    if bundle.crossover and bundle.crossover.ways == 3 and not project.additional_drivers:
        items.append(BomItem("Treiber", "M1", "Mitteltöner", 1,
                             f"{project.crossover.mid_impedance_ohm:g} Ohm"))

    if bundle.port:
        p = bundle.port
        if p.shape == "round":
            spec = f"Ø {p.diameter_m*1000:.1f} x {p.physical_length_m*1000:.1f} mm"
        else:
            spec = (
                f"{p.width_m*1000:.1f} x {p.height_m*1000:.1f} x "
                f"{p.physical_length_m*1000:.1f} mm"
            )
        if bundle.port_resistance_pa_s_m3 is not None:
            cardioid = bundle.project.enclosure.enclosure_type == "cardioid"
            items.append(BomItem("Kardioid-Rückvent" if cardioid else "Aperiodischer Vent", "BR1",
                "Rückwärtiger Dämpfungseinsatz / Vent" if cardioid else "Dämpfungseinsatz / Vent", 1,
                spec, f"Zielwiderstand {bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³; am Prototyp messen"))
        elif ((bundle.folded_line is not None and bundle.folded_line.family != "mltl")
              or bundle.tapped_horn is not None):
            items.append(BomItem("Fräsung", "BR1", "Linien-/Hornmündung in Frontplatte", 1,
                f"{p.width_m*1000:.1f} x {p.height_m*1000:.1f} mm",
                "Ausschnitt, kein separates Portrohr; Kanten verrunden"))
        else:
            items.append(BomItem("Ports", "BR1", f"{p.shape} port", 1, spec))
    if bundle.rear_port:
        p = bundle.rear_port
        second_surface = next((e.surface for e in bundle.front_elements if e.id == "BR2"), "back")
        items.append(BomItem("Ports", "BR2",
            "Interner Verbindungskanal" if second_surface == "partition" else "Rückkammer Rundport", 1,
            f"Ø {p.diameter_m*1000:.1f} x {p.physical_length_m*1000:.1f} mm"))
    if bundle.radiator:
        r=bundle.radiator
        items.append(BomItem("Passivmembran", "PM1", "Passivmembran mit Zusatzmasse", 1,
            f"Sd {r.area_m2*10000:.1f} cm²; Mms {r.stock_mass_kg*1000:.1f} g; Zusatz {r.added_mass_kg*1000:.1f} g",
            "Zusatzmasse nach Impedanzmessung feinabstimmen"))

    if bundle.crossover:
        for component in bundle.crossover.components:
            items.append(
                BomItem(
                    category="Frequenzweichenkomponenten",
                    reference=component.reference,
                    description=component.kind,
                    quantity=1,
                    specification=component.display_value,
                    notes=f"{component.branch}; {component.connection}; Soll {component.target_display_value}",
                )
            )

    screw_count = sum(e.bolt_count for e in bundle.front_elements)
    if bundle.tapped_horn:
        screw_count += project.driver.bolt_count or 0
    if screw_count:
        items.append(BomItem("Schrauben", "MONTAGE", "Treiberbefestigung", screw_count,
                             "Bohrungsdurchmesser gemäß F1-Platte" if bundle.tapped_horn else
                             "Bohrungsdurchmesser gemäß Frontlayout"))
    for accessory in project.accessories:
        items.append(BomItem(accessory.category, accessory.reference,
            accessory.description, accessory.quantity, accessory.specification, accessory.notes,
            accessory.unit_price_eur, accessory.price_source_url))
    if bundle.baffle_mode:
        items.extend((
            BomItem("Montage", "KABEL", "Lautsprecherleitung", 3, "Meter, 2 × 1,5 mm²"),
            BomItem("Montage", "BEFEST", "Schallwandbefestigung", 1,
                    "Wandanker oder standsicherer Fuß nach Einbauort dimensionieren"),
        ))
        if bundle.baffle_mode == "infinite_baffle":
            items.append(BomItem("Montage", "DICHT", "Umlaufende Wanddichtung", 1,
                                 "Rückraum luftdicht abtrennen"))
        elif bundle.baffle_mode == "dipole":
            items.append(BomItem("Montage", "LEIM", "Holzleim für Seitenflügel", 1,
                                 "Stumpf verleimte U-Frame-Verbindung"))
    else:
        items.extend((
            BomItem("Montage", "LEIM", "Holzleim und Dichtmasse", 1, "Material für ein Gehäuse"),
            BomItem("Montage", "KABEL", "Interne Lautsprecherleitung", 3, "Meter, 2 × 1,5 mm²"),
            BomItem("Montage", "HOLZSCHR", "Gehäuseschrauben", 32, "4 × 30 mm, Richtmenge"),
        ))
    from lautsprecher_konstruktion.export.pricing import price_bom
    return price_bom(bundle, tuple(items))


def write_bom_csv(path: str | Path, items: tuple[BomItem, ...]) -> None:
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Kategorie", "Referenz", "Beschreibung", "Anzahl", "Spezifikation", "Hinweise",
                         "Einzelpreis_EUR", "Positionspreis_EUR", "Preisquelle", "Preisart"])
        for item in items:
            writer.writerow([
                item.category,
                item.reference,
                item.description,
                item.quantity,
                item.specification,
                item.notes,
                f"{item.unit_price_eur:.2f}" if item.unit_price_eur is not None else "",
                f"{item.line_total_eur:.2f}" if item.line_total_eur is not None else "",
                item.price_source_url,
                item.price_kind if item.unit_price_eur is not None else "fehlt",
            ])
        subtotal, missing = priced_subtotal(items)
        writer.writerow(["", "", "Materialsumme", "", "", f"{missing} Positionen ohne Preis",
                         "", f"{subtotal:.2f}", "Preise sind Momentaufnahmen, kein Angebot", ""])
        from lautsprecher_konstruktion.export.pricing import budget_cost
        total = budget_cost(items)
        writer.writerow(["", "", "Budgetbedarf inkl. 15 % Reserve", "", "",
                         "nicht berechenbar" if total is None else "Planwert",
                         "", f"{total:.2f}" if total is not None else "", "", ""])


def write_cutlist_csv(path: str | Path, bundle: DesignBundle) -> None:
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Bauteil", "Anzahl", "Länge_mm", "Breite_mm", "Dicke_mm", "Material", "Bemerkung"])
        for panel in bundle.panels:
            note=("Treiberausschnitt gemäß Trennwand-DXF" if panel.name.startswith("Partition") else
                  "Kreisprofil und Treiberausschnitt gemäß Isobarik-Ring-DXF" if panel.name.startswith("Isobarik") else "")
            writer.writerow([
                panel.name,
                panel.quantity,
                f"{panel.width_m*1000:.1f}",
                f"{panel.height_m*1000:.1f}",
                f"{panel.thickness_m*1000:.1f}",
                bundle.project.material,
                note,
            ])
        if bundle.brace:
            b = bundle.brace
            writer.writerow(["Fensterstrebe", b.quantity, f"{b.outer_width_m*1000:.1f}",
                f"{b.outer_height_m*1000:.1f}", f"{b.thickness_m*1000:.1f}",
                bundle.project.material, f"Randbreite {b.border_m*1000:.1f} mm"])


def write_crossover_bom_csv(path: str | Path, bundle: DesignBundle) -> None:
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["Referenz", "Typ", "Sollwert", "Gewählter Wert", "Zweig", "Anschluss", "Anzahl", "Leistung", "Hinweis"])
        if bundle.crossover:
            for c in bundle.crossover.components:
                writer.writerow([c.reference, c.kind, c.target_display_value, c.display_value, c.branch,
                                 c.connection, 1, "", "Startentwurf - Bauteiltoleranz und Belastbarkeit prüfen"])
