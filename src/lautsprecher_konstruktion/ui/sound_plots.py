"""Secondary sound-lab plots: one chart at a time, chosen by the user, drawn only from calculated data."""
from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes

from lautsprecher_konstruktion.services.design import DesignBundle

# (key, label); "Gesamt" is the main graph (target curve editor) and needs no entry here.
PLOT_KINDS: tuple[tuple[str, str], ...] = (
    ("excursion", "Hub"),
    ("port", "Port"),
    ("impedance", "Impedanz"),
    ("delay", "Gruppenlaufzeit"),
    ("crossover", "Weiche"),
    ("dsp", "DSP"),
)


def _response(bundle: DesignBundle):
    return bundle.vented_response or bundle.sealed_response


def available_plots(bundle: DesignBundle | None) -> dict[str, tuple[bool, str]]:
    """Per plot kind: (available, reason when not). Nothing is drawn from data that does not exist."""
    if bundle is None:
        return {key: (False, "Noch kein Entwurf") for key, _ in PLOT_KINDS}
    r = _response(bundle)
    return {
        "excursion": (r is not None and r.excursion_mm is not None, "Mess-/Treiberwerte fehlen"),
        "port": (r is not None and r.port_velocity_m_s is not None and bundle.port is not None,
                 "Kein Port in diesem Gehäuse"),
        "impedance": (r is not None and r.impedance_ohm is not None, "Keine Impedanzdaten"),
        "delay": (r is not None, "Keine Daten"),
        "crossover": (bundle.crossover_response is not None, "Keine Weiche berechnet"),
        "dsp": (False, "DSP-Entwurf ist noch nicht Teil dieser Version"),
    }


def draw_plot(ax: Axes, bundle: DesignBundle, kind: str, tokens: dict[str, str]) -> None:
    """Draw one secondary plot. Raises ValueError for unavailable kinds so callers show the reason instead."""
    ok, reason = available_plots(bundle)[kind]
    if not ok:
        raise ValueError(reason)
    r = _response(bundle)
    ax.set_xlabel("Frequenz [Hz]")
    if kind == "crossover":
        cr = bundle.crossover_response
        assert cr is not None
        f = cr.frequencies_hz
        ax.set_title("Weiche · Pegel der Wege")
        ax.set_ylabel("Pegel [dB]")
        for label, values in (("Tieftöner", cr.woofer_acoustic_db), ("Hochtöner", cr.tweeter_acoustic_db),
                              ("Summe", cr.sum_acoustic_db)):
            if values is not None:
                ax.semilogx(f, values, linewidth=1.8, label=label)
        ax.legend(loc="lower left")
        return
    assert r is not None
    f = r.frequencies_hz
    ax.set_xlim(10, 500)
    if kind == "excursion":
        assert r.excursion_mm is not None
        ax.set_title("Hub · Membranauslenkung")
        ax.set_ylabel("mm")
        ax.semilogx(f, r.excursion_mm, linewidth=1.8)
        xmax = bundle.project.driver.xmax_mm
        if xmax is not None:
            ax.axhline(xmax, color=tokens["textPrimary"], linestyle="--", linewidth=1.2, label="Xmax")
            ax.legend(loc="upper right")
    elif kind == "port":
        assert r.port_velocity_m_s is not None
        ax.set_title("Port · Strömungsgeschwindigkeit")
        ax.set_ylabel("m/s")
        ax.semilogx(f, r.port_velocity_m_s, linewidth=1.8)
        ax.axhline(17.0, color=tokens["textPrimary"], linestyle="--", linewidth=1.2, label="Richtwert 17 m/s")
        ax.legend(loc="upper right")
    elif kind == "impedance":
        assert r.impedance_ohm is not None
        ax.set_title("Impedanz · Betrag")
        ax.set_ylabel("Ω")
        ax.semilogx(f, np.abs(r.impedance_ohm), linewidth=1.8)
    elif kind == "delay":
        ax.set_title("Gruppenlaufzeit")
        ax.set_ylabel("ms")
        ax.semilogx(f, r.group_delay_ms, linewidth=1.8)
