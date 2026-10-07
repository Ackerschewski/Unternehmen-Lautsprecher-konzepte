import numpy as np
import pytest

from lautsprecher_konstruktion.targets.eq import EQBand, FilterType
from lautsprecher_konstruktion.targets.smooth import render_frequencies
from lautsprecher_konstruktion.targets.state import NODE_FREQUENCIES, PRESET_LEVELS, TargetModel


def test_model_starts_neutral_with_fixed_nodes() -> None:
    m = TargetModel()
    assert m.is_neutral and len(m.points()) == len(NODE_FREQUENCIES) == 13
    assert np.allclose(m.curve(render_frequencies()), 0.0)


def test_levels_are_clamped_and_curve_stays_smooth_through_nodes() -> None:
    m = TargetModel()
    m.checkpoint()
    m.set_level(4, 99.0)
    assert m.state.levels[4] == 12.0
    f = np.asarray([NODE_FREQUENCIES[4]])
    assert m.curve(f)[0] == pytest.approx(12.0, abs=1e-6)


def test_bands_add_update_move_remove_with_unique_ids_and_undo_redo() -> None:
    m = TargetModel()
    a = m.add_band(EQBand(filter_type=FilterType.BELL, frequency_hz=100, gain_db=3))
    b = m.add_band(EQBand(filter_type=FilterType.HIGH_SHELF, frequency_hz=5000, gain_db=-2))
    c = m.add_band()
    assert len({a.id, b.id, c.id}) == 3 and len(m.bands) == 3
    m.checkpoint()
    m.move_band(a.id, 120, gain_delta_db=2)
    assert m.band(a.id).frequency_hz == 120 and m.band(a.id).gain_db == pytest.approx(5.0)
    m.update_band(b.id, q=0.7, enabled=False)
    assert m.band(b.id).enabled is False and m.band(b.id).q == 0.7
    assert m.undo() and m.band(a.id).frequency_hz == 100 and m.band(a.id).gain_db == 3
    assert m.redo() and m.band(a.id).frequency_hz == 120
    m.remove_band(c.id)
    assert [x.id for x in m.bands] == [a.id, b.id]
    assert m.undo() and len(m.bands) == 3


def test_move_band_ignores_gain_for_pass_filters_and_clamps_frequency() -> None:
    m = TargetModel()
    hp = m.add_band(EQBand(filter_type=FilterType.HIGH_PASS, frequency_hz=40))
    moved = m.move_band(hp.id, 5.0, gain_delta_db=9.0)
    assert moved.frequency_hz == 20.0 and moved.gain_db == 0.0


def test_curve_is_base_plus_bands_and_effective_points_include_them() -> None:
    m = TargetModel()
    m.apply_preset("warm")
    band = m.add_band(EQBand(filter_type=FilterType.BELL, frequency_hz=1000, gain_db=6, q=1))
    f = np.asarray([1000.0])
    base = m.curve(f)[0] - 6.0
    assert m.curve(f)[0] == pytest.approx(base + 6.0, abs=0.1)
    eff = dict(m.effective_points())
    assert eff[1000.0] == pytest.approx(PRESET_LEVELS["warm"][1][7] + 6.0, abs=0.1)
    m.update_band(band.id, enabled=False)
    assert dict(m.effective_points())[1000.0] == pytest.approx(PRESET_LEVELS["warm"][1][7], abs=1e-6)


def test_history_is_bounded_and_load_clears_it() -> None:
    m = TargetModel()
    for i in range(120):
        m.checkpoint()
        m.set_level(0, i % 5)
    assert len(m._undo) <= 80
    m.load([0.0] * 13, [EQBand(id="x", frequency_hz=200, gain_db=2)])
    assert not m.can_undo and not m.can_redo and m.bands[0].id == "x"


def test_set_from_points_resamples_and_validates() -> None:
    m = TargetModel()
    m.set_from_points([(20, 3.0), (20000, -3.0)])
    assert m.state.levels[0] == pytest.approx(3.0) and m.state.levels[-1] == pytest.approx(-3.0)
    with pytest.raises(ValueError):
        m.set_from_points([(0, 1.0), (10, 2.0)])
    m.set_from_points([])
    assert all(v == 0 for v in m.state.levels)


def test_project_and_request_round_trip_with_bands() -> None:
    from lautsprecher_konstruktion.project.demo import demo_project
    from lautsprecher_konstruktion.project.models import SpeakerProject

    bands = (EQBand(id="band-1", filter_type=FilterType.LOW_SHELF, frequency_hz=80, gain_db=4, q=0.7),)
    project = demo_project().model_copy(update={"target_eq_bands": bands})
    again = SpeakerProject.model_validate_json(project.model_dump_json())
    assert again.target_eq_bands == bands
    assert SpeakerProject.model_validate_json(demo_project().model_dump_json()).target_eq_bands == ()
