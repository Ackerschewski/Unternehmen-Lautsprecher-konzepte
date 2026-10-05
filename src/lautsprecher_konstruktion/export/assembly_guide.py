"""Build instructions derived from the calculated design.

The sequence follows the construction actually present in the bundle (partition,
isobaric coupler, horn, folded line, baffle, ...). Instructions contain only
steps that follow from the geometry; no values are invented beyond the
design's own numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lautsprecher_konstruktion.export.cutting import CuttingPlan, plan_cutting
from lautsprecher_konstruktion.export.weight import estimate_weight
from lautsprecher_konstruktion.services.design import DesignBundle


@dataclass(frozen=True)
class Step:
    title: str
    text: str
    check: str = ""


def _mm(value_m: float) -> str:
    return f"{value_m * 1000:.1f} mm"


def build_instructions(bundle: DesignBundle, cutting: CuttingPlan | None = None) -> tuple[Step, ...]:
    project = bundle.project
    cfg = project.enclosure
    cutting = cutting or plan_cutting(bundle)
    steps: list[Step] = []

    steps.append(Step(
        "Material und Werkzeug prüfen",
        f"Benötigt werden {cutting.sheet_count} Platte(n) {project.material} "
        f"(Verschnitt laut Zuschnittplan {cutting.waste_percent:.1f} %). Plattendicken am gelieferten Material "
        "mit dem Messschieber nachmessen und mit der Zuschnittliste vergleichen.",
        "Gemessene Dicke weicht nicht von der Planung ab; sonst Zeichnung neu berechnen."))
    steps.append(Step(
        "Zuschnitt",
        "Teile nach `zuschnittplan.pdf` einzeln sägen; Teilenummern (P01 …) sofort mit Bleistift auf die Kanten schreiben. "
        "Sägeschnitt und Maße der ersten Teile kontrollieren, bevor weitergesägt wird.",
        "Gegenüberliegende Teile sind auf 0,5 mm gleich lang; Winkel rechtwinklig."))

    if bundle.baffle_mode == "infinite_baffle":
        steps.extend((
            Step("Schallwand ausschneiden", "Treiberausschnitt laut `frontplatte.dxf` fräsen oder mit der Stichsäge schneiden; "
                 "Kanten sauber verschleifen. Der Chassisrahmen muss rundum auf der Wand aufliegen."),
            Step("Rückraum abdichten", "Der Rückraum muss luftdicht vom Hörraum getrennt sein. Die Wanddichtung "
                 "umlaufend aufbringen und Leitungsdurchführungen mit Dichtmasse schließen.",
                 "Mit der Hand gegen die Membran drücken: Sie muss langsam und gedämpft zurückfedern."),
        ))
    elif bundle.baffle_mode in {"open_baffle", "dipole"}:
        steps.extend((
            Step("Schallwand ausschneiden", "Treiberausschnitt laut `frontplatte.dxf`; Schraubenlöcher nur anbohren, "
                 "wenn der Bohrdurchmesser in der Zeichnung angegeben ist, sonst am Chassis anreißen."),
            Step("Flügel verleimen" if bundle.baffle_mode == "dipole" else "Standfuß prüfen",
                 "Seitenflügel stumpf verleimen und rechtwinklig spannen." if bundle.baffle_mode == "dipole" else
                 "Der offene Schallwandlautsprecher kippt leicht. Fuß oder Wandbefestigung vor der ersten Aufstellung dimensionieren."),
        ))
    else:
        steps.append(Step(
            "Ausschnitte fertigen",
            "Treiber-, Port- und Terminalausschnitte laut DXF-Dateien (`frontplatte.dxf`"
            + (", `rueckwand.dxf`" if any(e.surface == "back" for e in bundle.front_elements) else "")
            + (", `trennwand.dxf`" if any(e.surface == "partition" for e in bundle.front_elements) else "")
            + ") bzw. Einbaukoordinaten fräsen. Koordinaten beziehen sich jeweils auf die linke untere Ecke der Fläche.",
            "Treiber und Port probeweise einsetzen; Freiraum zu Wänden und Streben prüfen."))
        if cfg.front_layers > 1:
            steps.append(Step("Doppelte Front verleimen",
                f"{cfg.front_layers} Frontlagen deckungsgleich verleimen und pressen, danach erst ausschneiden oder Ausschnitte nachschneiden.",
                "Lagen fluchten; Ausschnitt ist durch alle Lagen sauber."))
        if bundle.coupler:
            steps.append(Step("Isobarik-Koppelkammer bauen",
                f"Ring laut `isobarik_montagering.dxf` fertigen, Koppelrohr (innen Ø {_mm(bundle.coupler.inner_diameter_m)}, "
                f"Länge {_mm(bundle.coupler.length_m)}) luftdicht mit Front und Ring verbinden.",
                "Kammer ist dicht; beide Chassis passen ohne Berührung hinein."))
        if bundle.front_horn:
            steps.append(Step("Hornplatten sägen",
                "Die vier Trapezplatten laut `horn_trapez_top_bottom.dxf` und `horn_trapez_sides.dxf` zuschneiden; "
                "Kanten- und Gehrungswinkel am realen Stoß prüfen und Probe-Zusammenbau trocken durchführen.",
                "Hornhals und -mund entsprechen den Maßen im Blatt."))
        if bundle.tapped_horn:
            steps.append(Step("Platte F1 fertigen",
                "Innenliegende Platte F1 laut `tapped_horn_f1.dxf` mit Treiberausschnitt anfertigen. Der Treiber sitzt auf F1 "
                "zwischen den beiden Kanalwegen; Umlenkspalt und Frontmündung laut Zeichnung einhalten.",
                "Kanalquerschnitte entsprechen dem Blatt."))
        if bundle.folded_line:
            steps.append(Step("Faltungsplatten einsetzen",
                "Faltungsplatten in der Reihenfolge F1, F2 … von vorn nach hinten setzen. Abwechselnd hinten bzw. vorn offene Platten "
                "lassen den Luftweg offen; die Stufenmaße der Zeichnung beachten.",
                "Der Luftweg ist durchgängig und nirgends verengt."))
        if bundle.brace:
            steps.append(Step("Fensterstreben einbauen",
                f"{bundle.brace.quantity} Fensterstrebe(n) an den Positionen laut Innenaufbau-Maßblatt verleimen; "
                "die Fensteröffnung bleibt frei für Luftbewegung.",
                "Strebe berührt weder Chassis noch Portrohr."))
        steps.append(Step("Trockenmontage",
            "Gehäuse ohne Leim und mit Zwingen zusammenstellen. Treiber, Port, Streben und Terminal einsetzen und prüfen, "
            "ob alles passt und die Kabel durchgeführt werden können.",
            "Alle Teile passen ohne Gewalt; Maße stimmen mit `massblatt.svg`."))
        if cfg.joint_style == "mitre":
            steps.append(Step("Gehrungen sägen und verkleben",
                "Seiten, Deckel und Boden mit 45°-Gehrungen an den Längskanten sägen (Maße gelten für die lange Außenkante). "
                "Die vier Platten außen aneinanderlegen, Klebeband über die Fugen, Leim auftragen und zum Kasten falten; "
                "Front und Rückwand werden stumpf aufgesetzt.",
                "Winkel stimmen, Fugen schließen ohne Spalt; Diagonalen messen."))
        steps.append(Step("Verleimen",
            "Seitenwände, Deckel und Boden mit Leim bestreichen und rechtwinklig verspannen; Diagonalen messen. "
            "Rückwand erst nach Einbau von Dämmung, Verkabelung und Innenteilen schließen; hierbei Dichtmasse verwenden.",
            "Diagonalen unterscheiden sich um weniger als 1 mm; Leimaustritt innen sofort entfernen."))
        if cfg.enclosure_type.startswith("bandpass_"):
            steps.append(Step("Kammertrennung dicht verleimen",
                "Trennwand mit Treiberausschnitt in die vorgesehene Tiefe einsetzen und umlaufend dicht verleimen. "
                "Front- und Rückkammer müssen getrennt Netto-Volumen und Portverbindung laut Zeichnung erhalten.",
                "Es gibt keine Leckage zwischen den Kammern."))
        if bundle.port:
            steps.append(Step("Port einbauen",
                f"Port {bundle.port.shape} mit der berechneten Länge einbauen; Länge am Prototyp nachmessen. "
                "Rohrkanten innen und außen verrunden und das Rohr dicht einkleben.",
                "Portlänge stimmt mit der Stückliste."))
        if bundle.rear_port:
            steps.append(Step("Zweiten Port einbauen",
                "BR2 wie BR1 einbauen; bei Bandpass 6. Ordnung seriell/parallel die Zuordnung zu Front- und Rückkammer beachten."))
        if bundle.radiator:
            steps.append(Step("Passivmembran montieren",
                f"Passivmembran einbauen und Zusatzmasse ({bundle.radiator.added_mass_kg * 1000:.0f} g) laut Berechnung anbringen; "
                "Zusatzmasse nach Impedanzmessung feinjustieren.",
                "Membran bewegt sich frei; Zusatzmasse sitzt fest."))
        if bundle.port_resistance_pa_s_m3 is not None:
            steps.append(Step("Dämpfungseinsatz vorbereiten",
                f"Zielwiderstand {bundle.port_resistance_pa_s_m3:.0f} Pa·s/m³ anfangs mit Schaumstoff oder Dämmvlies einstellen; "
                "am Prototyp prüfen.",
                "Nach der Messung Dämpfung nachjustieren."))

    if not bundle.baffle_mode:
        steps.append(Step(
            "Dämmung",
            "Dämmmaterial gemäß Stückliste lose einlegen. Port, Treiberrückseite und Membranweg nicht blockieren; "
            "Dämmung verändert die Abstimmung leicht (nach Aufbau messen).",
            "Nichts berührt die Membran oder den Portauslass."))
    if bundle.crossover:
        steps.append(Step(
            "Frequenzweiche aufbauen",
            "Bauteile laut `frequenzweiche_schema.svg` und `frequenzweiche/stueckliste.csv` verdrahten. "
            "Die E12-Werte sind Startwerte; Spulenpolarität, Bauteilbelastbarkeit und akustische Summe am gebauten Lautsprecher prüfen.",
            "Beide Wege spielen mit korrekter Polung; Messung der Weichenschaltung vor Endabnahme."))
    wiring = ("Chassis in Reihe" if cfg.isobaric_wiring == "series" else "Chassis parallel") if bundle.coupler else ""
    steps.append(Step(
        "Verkabeln und Abschließen",
        f"Terminal einsetzen, Leitung durchführen, Chassis anschließen und festschrauben"
        f"{'; Isobarik-Verdrahtung: ' + wiring + ', beide Chassis in gleicher Bewegungsrichtung' if wiring else ''}. "
        + ("" if bundle.baffle_mode else "Rückwand mit Dichtmasse und Schrauben schließen."),
        "" if bundle.baffle_mode else
        "Gehäuse ist luftdicht (bei geschlossenen Typen: Membran drücken, Luft darf nicht hörbar entweichen)."))
    steps.append(Step(
        "Messen und Abstimmen",
        "Impedanzkurve und Nahfeld bzw. Frequenzgang messen und über das Prototypvergleich-Werkzeug mit der Simulation vergleichen. "
        "Bei Abweichung Port oder Dämmung anpassen. Die Simulation ist eine lineare Kleinsignal-Näherung.",
        "Abstimmfrequenz und Pegel liegen innerhalb der geplanten Grenzen."))
    weight = estimate_weight(bundle)
    steps.append(Step("Transport und Aufstellung", weight.describe() + ". Schwere Gehäuse zu zweit heben und auf Standfestigkeit prüfen."))
    return tuple(steps)


def render_markdown(bundle: DesignBundle, steps: tuple[Step, ...] | None = None) -> str:
    steps = steps or build_instructions(bundle)
    lines = [f"# Bauanleitung – {bundle.project.name}", "",
             f"Revision: {bundle.project.revision} · Gehäusetyp: {bundle.project.enclosure.enclosure_type}", "",
             "> Die Anleitung folgt der berechneten Geometrie. Maße, Chassisdaten und Bohrbilder vor dem Zuschnitt am echten Bauteil prüfen.", ""]
    for number, step in enumerate(steps, start=1):
        lines.extend((f"## {number}. {step.title}", "", step.text, ""))
        if step.check:
            lines.extend((f"**Kontrolle:** {step.check}", ""))
    return "\n".join(lines)


def write_assembly_guide(directory: str | Path, bundle: DesignBundle,
                         cutting: CuttingPlan | None = None) -> tuple[Path, Path]:
    folder = Path(directory)
    steps = build_instructions(bundle, cutting)
    markdown = folder / "bauanleitung.md"
    markdown.write_text(render_markdown(bundle, steps), encoding="utf-8")
    pdf = folder / "bauanleitung.pdf"
    _write_pdf(pdf, bundle, steps)
    return markdown, pdf


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def _write_pdf(path: Path, bundle: DesignBundle, steps: tuple[Step, ...]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    _, height = A4
    canvas = Canvas(str(path), pagesize=A4)
    page = 1

    def page_frame() -> float:
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(40, height - 50, f"Bauanleitung – {bundle.project.name}"[:70])
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 24, f"{bundle.project.revision} · Seite {page}")
        return float(height) - 80

    y = page_frame()
    for number, step in enumerate(steps, start=1):
        wrapped = _wrap(step.text, 95)
        if step.check:
            wrapped.extend(_wrap(f"Kontrolle: {step.check}", 95))
        if y - 16 * (len(wrapped) + 2) < 50:
            canvas.showPage()
            page += 1
            y = page_frame()
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(40, y, f"{number}. {step.title}"[:80])
        y -= 16
        canvas.setFont("Helvetica", 9.5)
        for entry in wrapped:
            canvas.drawString(52, y, entry)
            y -= 13
        y -= 8
    canvas.save()
