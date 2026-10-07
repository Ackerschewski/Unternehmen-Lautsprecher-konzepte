"""The UI follows the Ackerschewski_code Design System (desktop profile)."""
import json
import os
import re
from pathlib import Path

import pytest
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from lautsprecher_konstruktion.project.demo import demo_project
from lautsprecher_konstruktion.ui import tokens
from lautsprecher_konstruktion.ui.assistant_window import AssistantWindow
from lautsprecher_konstruktion.ui.fonts import apply_default_font, fonts_dir, load_fonts
from lautsprecher_konstruktion.ui.main_window import MainWindow
from lautsprecher_konstruktion.ui.theme import chart_rc, stylesheet

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads((ROOT / "docs/design/ack-studio-tokens.snapshot.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_tokens_match_the_ack_studio_package_snapshot() -> None:
    assert (tokens.PAPER, tokens.INK, tokens.MUTED, tokens.LINE, tokens.ON_ACCENT) == (
        SNAPSHOT["color"]["paper"], SNAPSHOT["color"]["ink"], SNAPSHOT["color"]["muted"],
        SNAPSHOT["color"]["line"], SNAPSHOT["color"]["onAccent"])
    for key, values in SNAPSHOT["themes"].items():
        assert tokens.AREAS[key] == {k: values[k] for k in ("accent", "panel", "band")}, key
    assert tokens.SPACING == tuple(int(v[:-2]) for v in SNAPSHOT["space"].values())
    assert (tokens.RADIUS_CONTROL, tokens.RADIUS_CARD) == (8, 14) and tokens.TOUCH_TARGET == 44
    assert tokens.DEFAULT_AREA == "software" and tokens.theme()["accent"] == "#172d46"


def test_every_area_has_readable_text_and_accent_contrast() -> None:
    for name in tokens.AREAS:
        tokens.set_area(name)
        t = tokens.theme()
        for text in ("textPrimary", "textSecondary"):
            for ground in ("background", "panel", "band"):
                assert tokens.contrast(t[text], t[ground]) >= 4.5, (name, text, ground)
        assert tokens.contrast(t["onAccent"], t["accent"]) >= 4.5, name
        assert tokens.contrast(t["onAccent"], t["accentHover"]) >= 4.5, name
        assert tokens.contrast(t["accent"], t["background"]) >= 4.5, name
    tokens.set_area(tokens.DEFAULT_AREA)
    with pytest.raises(ValueError):
        tokens.set_area("gold")


def test_stylesheet_follows_the_package_look() -> None:
    css = stylesheet()
    assert "#172d46" in css and "#fbfaf7" in css and "'Inter'" in css and "Cormorant Garamond" in css
    assert "border-radius:8px" in css and "border-radius:14px" in css
    assert "JetBrains" not in css and "#F27216" not in css and "#1769b3" not in css.casefold()
    assert "QPushButton#primary" in css and "min-height:28px" in css


def test_no_hard_coded_colours_in_ui_code() -> None:
    allowed = {"tokens.py", "theme.py"}
    pattern = re.compile(r"#[0-9a-fA-F]{6}\b")
    for path in (ROOT / "src/lautsprecher_konstruktion/ui").glob("*.py"):
        if path.name not in allowed:
            assert not pattern.search(path.read_text(encoding="utf-8")), f"{path.name} hard-codes a colour"


def test_bundled_fonts_load_and_charts_use_them(app: QApplication) -> None:
    families = load_fonts()
    assert {"Inter", "Cormorant Garamond"} <= set(families)
    assert not {"Source Serif 4", "JetBrains Mono"} & set(families)
    assert all((fonts_dir() / name).is_file() for name in ("LICENSE-Inter.txt", "LICENSE-CormorantGaramond-OFL.txt"))
    apply_default_font(app)
    assert app.font().family() == "Inter" and "Cormorant Garamond" in QFontDatabase.families()
    assert chart_rc()["font.family"][0] == "Inter"


def test_status_line_has_glyph_text_and_role(app: QApplication) -> None:
    window = AssistantWindow()
    window._set_state("danger", "Fehler")
    assert window.state.text().startswith("✕") and window.state.property("role") == "danger"
    window._set_state("success", "Fertig")
    assert window.state.text().startswith("✓")
    assert 'QLabel#statusLine[role="danger"] {border:2px dashed' in stylesheet().replace("{{", "{")


def test_default_simulation_shows_two_charts_and_more_on_request(app: QApplication, tmp_path: Path) -> None:
    window = AssistantWindow()
    path = tmp_path / "p.json"
    path.write_text(demo_project().model_dump_json(), encoding="utf-8")
    window.open_project_file(path)
    window._redraw_simulation()
    assert len(window.figure.axes) == 2
    window.more_charts.setChecked(True)
    assert len(window.figure.axes) == 4


def test_tabs_are_grouped_and_there_is_no_theme_switch(app: QApplication) -> None:
    window = AssistantWindow()
    names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert names == ["Entwürfe", "Variantenvergleich", "Zeichnungen", "Simulation", "Stückliste", "Zuschnitt"]
    assert window.export_button.objectName() == "primary" and window.create_button.objectName() == "primary"
    titles = [a.text().replace("&", "") for a in window.menuBar().actions()]
    assert titles == ["Datei", "Werkzeuge", "Ansicht", "Hilfe"]
    assert window.mode == "light"


def test_area_can_be_chosen_in_settings(app: QApplication) -> None:
    from lautsprecher_konstruktion.appdata import Settings
    Settings().set("area", "construction")  # legacy key of the old default must not override the new default
    assert "#172d46" in AssistantWindow().styleSheet()
    Settings().set("area_v2", "construction")
    try:
        assert "#735419" in AssistantWindow().styleSheet()
    finally:
        Settings().set("area_v2", "bogus")
        assert "#172d46" in AssistantWindow().styleSheet()  # invalid values fall back to the software default


def test_expert_window_uses_the_same_stylesheet_and_hides_three_way_fields(app: QApplication) -> None:
    tokens.set_area(tokens.DEFAULT_AREA)
    window = MainWindow()
    assert "#172d46" in window.styleSheet() and window.calculate_button.objectName() == "primary"
    assert window._crossover_form.isRowVisible(window.upper_frequency) is False
    window.crossover_ways.setCurrentIndex(window.crossover_ways.findData(3))
    assert window._crossover_form.isRowVisible(window.upper_frequency) is True
