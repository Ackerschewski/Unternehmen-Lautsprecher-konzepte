"""Sound-lab analysis: envelope of variant curves, influence spans and DSP headroom notes (no widgets created here)."""
from __future__ import annotations

from typing import Any

import numpy as np

from lautsprecher_konstruktion.enclosure.registry import registry
from lautsprecher_konstruktion.services.automatic import SpeakerDesign


def sound_curve(
    design: SpeakerDesign,
) -> tuple[np.ndarray, np.ndarray, str] | None:
    crossover = design.bundle.crossover_response
    if crossover is not None and crossover.sum_acoustic_db is not None:
        return (
            np.asarray(crossover.frequencies_hz, dtype=float),
            np.asarray(crossover.sum_acoustic_db, dtype=float),
            "Ist · FRD/Weichensumme",
        )
    response = design.bundle.vented_response or design.bundle.sealed_response
    if response is None:
        return None
    return (
        np.asarray(response.frequencies_hz, dtype=float),
        np.asarray(response.response_db, dtype=float),
        "Ist · Gehäuse-/Tieftonsimulation",
    )

def relative_curve(
    frequencies: np.ndarray, levels: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    valid = np.isfinite(frequencies) & np.isfinite(levels) & (frequencies > 0)
    f = frequencies[valid]
    v = levels[valid].astype(float, copy=True)
    if not f.size:
        return f, v
    reference = (f >= 80.0) & (f <= 120.0)
    v -= float(np.median(v[reference])) if np.any(reference) else float(np.median(v))
    return f, v

def curve_value_at(
    design: SpeakerDesign, frequency_hz: float
) -> float | None:
    data = sound_curve(design)
    if data is None:
        return None
    f, v = relative_curve(data[0], data[1])
    if not f.size or frequency_hz < f[0] or frequency_hz > f[-1]:
        return None
    return float(np.interp(np.log10(frequency_hz), np.log10(f), v))

def span_label(values: list[float], variants: int) -> str:
    if variants < 2 or len(values) < 2:
        return "keine belastbare Vergleichsvariante"
    span = max(values)-min(values)
    if span >= 2.5:
        level = "stark"
    elif span >= 0.75:
        level = "mittel"
    else:
        level = "gering"
    return f"{level} · {span:.1f} dB berechnete Spannweite"


def update_sound_lab(win: Any) -> None:
    """Refresh the sound lab's candidate envelope, actual curve and influence notes for the current design."""
    if not hasattr(win, "target_curve"):
        return
    current = win._current()
    if current is None:
        win.target_curve.set_candidate_curves(())
        win.target_curve.clear_actual()
        win.target_curve.set_component_influence({})
        win.target_curve.set_influence_summary(
            "Berechne zuerst Varianten; danach zeigt die Hülle nur tatsächlich gefundene Lösungen."
        )
        return

    mode = win.target_curve.analysis_mode()
    current_enclosure = current.project.enclosure.enclosure_type
    current_driver = current.woofer.model

    candidates = list(win.designs)
    if mode == "enclosure":
        candidates = [d for d in candidates if d.woofer.model == current_driver]
    elif mode == "driver":
        candidates = [
            d for d in candidates
            if d.project.enclosure.enclosure_type == current_enclosure
        ]
    elif mode == "crossover":
        candidates = [
            d for d in candidates
            if d.bundle.crossover_response is not None
            and d.bundle.crossover_response.sum_acoustic_db is not None
        ]

    curves: list[tuple[np.ndarray, np.ndarray]] = []
    for design in candidates:
        data = sound_curve(design)
        if data is not None:
            curves.append((data[0], data[1]))
    win.target_curve.set_candidate_curves(curves)

    current_curve = sound_curve(current)
    if current_curve is not None:
        win.target_curve.set_actual_curve(
            current_curve[0], current_curve[1], label=current_curve[2]
        )
    else:
        win.target_curve.clear_actual()

    selected_frequency = win.target_curve.selected_frequency_hz()
    current_tweeter = current.tweeter.model if current.tweeter else ""

    enclosure_group = [
        d for d in win.designs
        if d.woofer.model == current_driver
        and (d.tweeter.model if d.tweeter else "") == current_tweeter
    ]
    enclosure_signatures = {
        d.project.enclosure.enclosure_type for d in enclosure_group
    }
    enclosure_values = [
        value for d in enclosure_group
        if (value := curve_value_at(d, selected_frequency)) is not None
    ]

    driver_group = [
        d for d in win.designs
        if d.project.enclosure.enclosure_type == current_enclosure
    ]
    driver_signatures = {d.woofer.model for d in driver_group}
    driver_values = [
        value for d in driver_group
        if (value := curve_value_at(d, selected_frequency)) is not None
    ]

    crossover_group = [
        d for d in win.designs
        if d.woofer.model == current_driver
        and d.project.enclosure.enclosure_type == current_enclosure
        and d.bundle.crossover_response is not None
        and d.bundle.crossover_response.sum_acoustic_db is not None
    ]
    crossover_signatures = {
        (
            d.project.crossover.topology,
            round(d.project.crossover.crossover_hz, 1),
            d.tweeter.model if d.tweeter else "",
        )
        for d in crossover_group
    }
    crossover_values = [
        value for d in crossover_group
        if (value := curve_value_at(d, selected_frequency)) is not None
    ]

    dsp_text = "keine belastbaren Hubdaten"
    response = current.bundle.vented_response or current.bundle.sealed_response
    xmax = current.bundle.project.driver.xmax_mm
    if (
        response is not None
        and response.excursion_mm is not None
        and xmax
        and response.frequencies_hz[0] <= selected_frequency <= response.frequencies_hz[-1]
    ):
        excursion = float(np.interp(
            np.log10(selected_frequency),
            np.log10(response.frequencies_hz),
            response.excursion_mm,
        ))
        if excursion > 0:
            headroom = 20*np.log10(xmax/excursion)
            dsp_text = (
                f"Hubgrenze erreicht ({headroom:.1f} dB Reserve)"
                if headroom <= 0
                else f"bis ca. +{headroom:.1f} dB Hubreserve"
            )

    win.target_curve.set_component_influence({
        "enclosure": span_label(
            enclosure_values, len(enclosure_signatures)
        ),
        "driver": span_label(driver_values, len(driver_signatures)),
        "crossover": span_label(
            crossover_values, len(crossover_signatures)
        ),
        "dsp": dsp_text,
    })

    notes: list[str] = []
    outside = win.target_curve.outside_envelope()
    if outside is not None:
        notes.append(
            f"Ziel bei {outside[0]:.0f} Hz liegt etwa {outside[1]:.1f} dB außerhalb "
            "der aktuell berechneten Variantenhülle."
        )

    if mode == "crossover" and not candidates:
        notes.append(
            "Für eine belastbare Weichen-/Fullrange-Aussage fehlen FRD-Daten. "
            "Vorhandene T/S-Daten reichen dafür absichtlich nicht."
        )
    elif mode == "dsp":
        response = current.bundle.vented_response or current.bundle.sealed_response
        xmax = current.bundle.project.driver.xmax_mm
        if response is not None and response.excursion_mm is not None and xmax:
            margins: list[tuple[float, float]] = []
            rf = np.asarray(response.frequencies_hz, dtype=float)
            ex = np.asarray(response.excursion_mm, dtype=float)
            for frequency, target_db in win.target_curve.effective_points():
                if frequency < rf[0] or frequency > rf[-1] or target_db <= 0:
                    continue
                excursion = float(np.interp(np.log10(frequency), np.log10(rf), ex))
                if excursion > 0:
                    headroom_db = 20*np.log10(xmax/excursion)
                    margins.append((frequency, headroom_db-target_db))
            if margins:
                frequency, margin = min(margins, key=lambda item: item[1])
                if margin < 0:
                    notes.append(
                        f"DSP-Anhebung bei {frequency:.0f} Hz überschreitet die berechnete "
                        f"Hubreserve um etwa {-margin:.1f} dB. Gehäuse/Chassis ändern statt nur boosten."
                    )
                else:
                    notes.append(
                        f"Tiefton-DSP bleibt in den geprüften Punkten mindestens {margin:.1f} dB "
                        "unter der berechneten Xmax-Grenze."
                    )
        else:
            notes.append("DSP-Headroom ist ohne belastbare Hubdaten nicht quantifizierbar.")

    if mode in {"overall", "enclosure", "driver", "influence"} and current_curve is not None:
        cf, cv = relative_curve(current_curve[0], current_curve[1])
        best: tuple[float, int, float, float] | None = None
        targets = win.target_curve.effective_points()
        for alt_index, alternative in enumerate(win.designs):
            if alternative is current:
                continue
            if mode == "enclosure" and alternative.woofer.model != current_driver:
                continue
            if mode == "driver" and (
                alternative.project.enclosure.enclosure_type != current_enclosure
            ):
                continue
            alt_curve = sound_curve(alternative)
            if alt_curve is None:
                continue
            af, av = relative_curve(alt_curve[0], alt_curve[1])
            for frequency, target_db in targets:
                if (
                    not cf.size or not af.size
                    or frequency < cf[0] or frequency > cf[-1]
                    or frequency < af[0] or frequency > af[-1]
                ):
                    continue
                current_db = float(np.interp(np.log10(frequency), np.log10(cf), cv))
                alternative_db = float(np.interp(np.log10(frequency), np.log10(af), av))
                improvement = abs(current_db-target_db)-abs(alternative_db-target_db)
                if improvement > 1.0 and (best is None or improvement > best[0]):
                    best = (improvement, alt_index, frequency, alternative_db)
        if best is not None:
            improvement, alt_index, frequency, _alternative_db = best
            alternative = win.designs[alt_index]
            enclosure = registry.get(
                alternative.project.enclosure.enclosure_type
            ).label
            change = (
                f"anderes Gehäuse ({enclosure})"
                if alternative.woofer.model == current_driver
                else f"anderes Chassis ({alternative.woofer.model})"
            )
            notes.append(
                f"Bei {frequency:.0f} Hz liegt {alternative.label} rund {improvement:.1f} dB "
                f"näher am Ziel – hier wäre {change} die bessere Richtung."
            )

    if not notes:
        notes.append(
            f"{len(curves)} berechnete Kurve(n) bilden die aktuell belegbare Vergleichsbasis."
        )
    win.target_curve.set_influence_summary(" ".join(notes))
