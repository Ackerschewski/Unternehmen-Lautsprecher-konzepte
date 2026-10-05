from __future__ import annotations

from dataclasses import dataclass, replace
from math import pi, sqrt


@dataclass(frozen=True)
class PassiveComponent:
    reference: str
    kind: str
    value_si: float
    unit: str
    connection: str
    branch: str
    target_value_si: float | None = None

    @property
    def target_display_value(self) -> str:
        return replace(self, value_si=self.target_value_si).display_value if self.target_value_si else self.display_value

    @property
    def display_value(self) -> str:
        if self.unit == "H":
            if self.value_si >= 1e-3:
                return f"{self.value_si * 1e3:.3g} mH"
            return f"{self.value_si * 1e6:.3g} uH"
        if self.unit == "F":
            return f"{self.value_si * 1e6:.3g} uF"
        if self.unit == "ohm":
            return f"{self.value_si:.3g} Ohm"
        return f"{self.value_si:.4g} {self.unit}"


@dataclass(frozen=True)
class CrossoverDesign:
    name: str
    crossover_hz: float
    slope_db_oct: int
    components: tuple[PassiveComponent, ...]
    notes: tuple[str, ...]
    ways: int = 2
    upper_crossover_hz: float | None = None


def _validate(fc_hz: float, impedance_ohm: float) -> None:
    if fc_hz <= 0:
        raise ValueError("crossover frequency must be positive")
    if impedance_ohm <= 0:
        raise ValueError("impedance must be positive")


def first_order_two_way(
    crossover_hz: float,
    woofer_impedance_ohm: float,
    tweeter_impedance_ohm: float,
) -> CrossoverDesign:
    """Ideal 6 dB/oct passive two-way network using resistive loads."""
    _validate(crossover_hz, woofer_impedance_ohm)
    _validate(crossover_hz, tweeter_impedance_ohm)

    woofer_l = woofer_impedance_ohm / (2.0 * pi * crossover_hz)
    tweeter_c = 1.0 / (2.0 * pi * crossover_hz * tweeter_impedance_ohm)
    return CrossoverDesign(
        name="Butterworth 1st order",
        crossover_hz=crossover_hz,
        slope_db_oct=6,
        components=(
            PassiveComponent("L1", "inductor", woofer_l, "H", "series", "woofer low-pass"),
            PassiveComponent("C1", "capacitor", tweeter_c, "F", "series", "tweeter high-pass"),
        ),
        notes=(
            "Electrical starting point based on nominal resistive impedance.",
            "Real loudspeaker impedance and acoustic response must be measured for final tuning.",
        ),
    )


def second_order_butterworth_two_way(
    crossover_hz: float,
    woofer_impedance_ohm: float,
    tweeter_impedance_ohm: float,
) -> CrossoverDesign:
    """Ideal 12 dB/oct Butterworth passive two-way network.

    Component scaling follows the common constant-resistance prototype:
    low-pass L = sqrt(2) R / (2 pi f), C = 1 / (sqrt(2) 2 pi f R).
    The high-pass uses the dual arrangement.
    """
    _validate(crossover_hz, woofer_impedance_ohm)
    _validate(crossover_hz, tweeter_impedance_ohm)

    wl = sqrt(2.0) * woofer_impedance_ohm / (2.0 * pi * crossover_hz)
    wc = 1.0 / (sqrt(2.0) * 2.0 * pi * crossover_hz * woofer_impedance_ohm)
    tc = 1.0 / (sqrt(2.0) * 2.0 * pi * crossover_hz * tweeter_impedance_ohm)
    tl = sqrt(2.0) * tweeter_impedance_ohm / (2.0 * pi * crossover_hz)

    return CrossoverDesign(
        name="Butterworth 2nd order",
        crossover_hz=crossover_hz,
        slope_db_oct=12,
        components=(
            PassiveComponent("L1", "inductor", wl, "H", "series", "woofer low-pass"),
            PassiveComponent("C1", "capacitor", wc, "F", "shunt", "woofer low-pass"),
            PassiveComponent("C2", "capacitor", tc, "F", "series", "tweeter high-pass"),
            PassiveComponent("L2", "inductor", tl, "H", "shunt", "tweeter high-pass"),
        ),
        notes=(
            "Electrical component calculator assumes resistive nominal loads.",
            "Driver phase, impedance peaks, baffle step and acoustic slopes are not yet compensated.",
        ),
    )


def second_order_linkwitz_riley_two_way(
    crossover_hz: float,
    woofer_impedance_ohm: float,
    tweeter_impedance_ohm: float,
) -> CrossoverDesign:
    """Ideal passive LR2 approximation for nominal resistive loads."""
    _validate(crossover_hz, woofer_impedance_ohm)
    _validate(crossover_hz, tweeter_impedance_ohm)

    wl = woofer_impedance_ohm / (pi * crossover_hz)
    wc = 1.0 / (4.0 * pi * crossover_hz * woofer_impedance_ohm)
    tc = 1.0 / (4.0 * pi * crossover_hz * tweeter_impedance_ohm)
    tl = tweeter_impedance_ohm / (pi * crossover_hz)

    return CrossoverDesign(
        name="Linkwitz-Riley 2nd order approximation",
        crossover_hz=crossover_hz,
        slope_db_oct=12,
        components=(
            PassiveComponent("L1", "inductor", wl, "H", "series", "woofer low-pass"),
            PassiveComponent("C1", "capacitor", wc, "F", "shunt", "woofer low-pass"),
            PassiveComponent("C2", "capacitor", tc, "F", "series", "tweeter high-pass"),
            PassiveComponent("L2", "inductor", tl, "H", "shunt", "tweeter high-pass"),
        ),
        notes=(
            "LR2 is sensitive to acoustic phase and driver offset; treat this as a starting network.",
            "Final crossover requires measured frequency and impedance data.",
        ),
    )


def l_pad(load_ohm: float, attenuation_db: float) -> tuple[PassiveComponent, PassiveComponent]:
    """Constant-impedance L-pad for attenuation of a nominal resistive load."""
    if load_ohm <= 0:
        raise ValueError("load_ohm must be positive")
    if attenuation_db <= 0:
        raise ValueError("attenuation_db must be positive")

    ratio = 10.0 ** (attenuation_db / 20.0)
    series = load_ohm * (ratio - 1.0) / ratio
    parallel = load_ohm / (ratio - 1.0)
    return (
        PassiveComponent("Rpad-S", "resistor", series, "ohm", "series", "attenuation"),
        PassiveComponent("Rpad-P", "resistor", parallel, "ohm", "shunt", "attenuation"),
    )


def zobel_from_re_le(re_ohm: float, le_h: float) -> tuple[PassiveComponent, PassiveComponent]:
    """Simple voice-coil inductance compensation starting point."""
    if re_ohm <= 0 or le_h <= 0:
        raise ValueError("Re and Le must be positive")
    rz = re_ohm
    cz = le_h / (rz * rz)
    return (
        PassiveComponent("Rz", "resistor", rz, "ohm", "series RC branch", "zobel"),
        PassiveComponent("Cz", "capacitor", cz, "F", "series RC branch", "zobel"),
    )


def baffle_step_compensation(baffle_step_hz: float, load_ohm: float,
                             step_db: float = 6.0) -> tuple[PassiveComponent, PassiveComponent]:
    """Series inductor with a parallel resistor in the woofer branch.

    The inductor passes low frequencies unattenuated; above the transition the resistor
    attenuates the woofer by step_db. Half of the step is reached at baffle_step_hz.
    """
    _validate(baffle_step_hz, load_ohm)
    if not 0 < step_db <= 6.0206 + 1e-9:
        raise ValueError("step_db must be between 0 and 6.02 dB")
    k = 10.0 ** (step_db / 20.0)
    resistor = load_ohm * (k - 1.0)
    inductor = resistor / (2.0 * pi * baffle_step_hz * sqrt(k))
    return (
        PassiveComponent("Lbs", "inductor", inductor, "H", "series, parallel zu Rbs", "woofer baffle step"),
        PassiveComponent("Rbs", "resistor", resistor, "ohm", "parallel zu Lbs", "woofer baffle step"),
    )
