import numpy as np
import pytest

from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.targets.curve import (
    PRESETS,
    TargetBand,
    TargetCurve,
    derive_f3_target_hz,
    deviation,
)

F = np.geomspace(20, 20000, 500)


def test_neutral_curve_is_flat_and_default() -> None:
    curve = TargetCurve()
    assert curve.is_neutral and curve.version == 1 and curve.name == "Neutral"
    assert np.allclose(curve.level_db(F), 0.0)
    assert derive_f3_target_hz(curve) is None


@pytest.mark.parametrize("kind", ["peak", "low_shelf", "high_shelf"])
def test_band_reaches_its_gain_where_expected(kind: str) -> None:
    band = TargetBand(kind=kind, frequency_hz=1000.0, gain_db=6.0, q=1.0)  # type: ignore[arg-type]
    level = TargetCurve(bands=(band,)).level_db(F)
    at = lambda f: float(np.interp(f, F, level))
    if kind == "peak":
        assert at(1000) == pytest.approx(6.0, abs=0.15) and abs(at(30)) < 0.2 and abs(at(15000)) < 0.4
    elif kind == "low_shelf":
        assert at(25) == pytest.approx(6.0, abs=0.3) and abs(at(15000)) < 0.3 and at(1000) == pytest.approx(3.0, abs=0.4)
    else:
        assert at(18000) == pytest.approx(6.0, abs=0.5) and abs(at(25)) < 0.3


def test_edit_operations_are_immutable_and_clamped() -> None:
    base = TargetCurve()
    one = base.with_band(TargetBand(frequency_hz=100.0, gain_db=3.0))
    assert base.bands == () and len(one.bands) == 1 and one.name == "Eigene Kurve"
    moved = one.with_moved(0, 1.0, 99.0)
    assert moved.bands[0].frequency_hz == 20.0 and moved.bands[0].gain_db == 18.0
    assert one.without_band(0).bands == ()
    with pytest.raises(ValueError):
        TargetBand(frequency_hz=5.0)


def test_json_roundtrip_and_optional_in_project() -> None:
    curve = PRESETS["Mehr Tiefbass"]
    assert TargetCurve.model_validate_json(curve.model_dump_json()) == curve
    project = demo_project()
    assert project.target_curve is None
    stored = project.model_copy(update={"target_curve": curve})
    from lautsprecher_konstruktion.project.models import SpeakerProject
    assert SpeakerProject.model_validate_json(stored.model_dump_json()).target_curve == curve
    assert SpeakerProject.model_validate_json(project.model_dump_json()).target_curve is None


def test_deviation_aligns_level_and_ignores_range_without_model_data() -> None:
    curve = TargetCurve(bands=(TargetBand(kind="peak", frequency_hz=60.0, gain_db=4.0, q=1.0),))
    f = np.geomspace(10, 500, 300)
    perfect = curve.level_db(f) + 17.0  # relative response with arbitrary absolute level
    dev = deviation(curve, f, perfect)
    assert dev is not None and dev.mean_abs_db < 1e-6 and dev.max_abs_db < 1e-6
    assert dev.low_hz >= 20.0 and dev.high_hz <= 500.0
    flat = deviation(curve, f, np.zeros_like(f))
    assert flat is not None and flat.max_abs_db > 3.0
    assert deviation(curve, np.geomspace(1000, 20000, 50), np.zeros(50)) is None


def test_f3_target_derived_from_low_shelf_cut() -> None:
    curve = TargetCurve(bands=(TargetBand(kind="low_shelf", frequency_hz=50.0, gain_db=-12.0, q=0.7),))
    f3 = derive_f3_target_hz(curve)
    assert f3 is not None and 25 < f3 < 120
