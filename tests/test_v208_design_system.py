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
from lautsprecher_konstruktion.ui.theme import chart_rc, resolve_mode, stylesheet

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = json.loads((ROOT / "docs/design/design-tokens.snapshot.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_theme_colours_match_the_design_system_snapshot(mode: str) -> None:
    approved = SNAPSHOT["color"]["themes"][mode]
    for role in ("background", "surface", "surfaceElevated", "textPrimary", "textSecondary", "border", "accent"):
        assert tokens.theme(mode)[role].casefold() == approved[role].casefold(), role
    assert tokens.ACCENT == SNAPSHOT["color"]["accent"]["primary"] == "#F27216"
    assert tokens.SPACING == tuple(SNAPSHOT["spacing"]["scale"])


def test_status_colours_are_the_approved_semantic_roles() -> None:
    assert tokens.STATUS == {"success": "#22C55E", "warning": "#F59E0B", "danger": "#EF4444", "info": "#3B82F6"}
    assert all(tokens.status_line(role, "x").startswith(tokens.STATUS_GLYPH[role]) for role in tokens.STATUS)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_text_and_primary_button_contrast(mode: str) -> None:
    t = tokens.theme(mode)
    for text in ("textPrimary", "textSecondary"):
        for ground in ("background", "surface", "surfaceElevated"):
            assert tokens.contrast(t[text], t[ground]) >= 4.5, (text, ground)
    on_accent = tokens.text_on(t["accent"])
    assert tokens.contrast(on_accent, t["accent"]) >= 4.5
    assert tokens.contrast(on_accent, t["accentHover"]) >= 4.5 and tokens.contrast(on_accent, t["accentPressed"]) >= 3.0


def test_stylesheet_uses_tokens_and_no_legacy_blue() -> None:
    for mode in ("light", "dark"):
        css = stylesheet(mode)
        assert "#F27216" in css and "'Inter'" in css and "Source Serif 4" in css and "JetBrains Mono" in css
        assert "border-radius:4px" in css and "#1769b3" not in css.casefold()
        assert "QPushButton#primary" in css and "QTabBar::tab:selected" in css


def test_no_hard_coded_legacy_colours_in_ui_code() -> None:
    allowed = {"tokens.py", "theme.py"}
    pattern = re.compile(r"#[0-9a-fA-F]{6}\b")
    for path in (ROOT / "src/lautsprecher_konstruktion/ui").glob("*.py"):
        if path.name not in allowed:
            assert not pattern.search(path.read_text(encoding="utf-8")), f"{path.name} hard-codes a colour"


def test_bundled_fonts_load_and_charts_use_them(app: QApplication) -> None:
    families = load_fonts()
    assert {"Inter", "Source Serif 4", "JetBrains Mono"} <= set(families)
    assert all((fonts_dir() / name).is_file() for name in ("LICENSE-Inter.txt", "LICENSE-SourceSerif4.md",
                                                           "LICENSE-JetBrainsMono-OFL.txt"))
    apply_default_font(app)
    assert app.font().family() == "Inter"
    assert "Inter" in QFontDatabase.families()
    assert chart_rc("dark")["font.family"][0] == "Inter"


def test_system_preference_resolves_to_a_concrete_mode(app: QApplication) -> None:
    assert resolve_mode("dark") == "dark" and resolve_mode("light") == "light"
    assert resolve_mode("system") in {"light", "dark"}


def test_status_line_has_glyph_text_and_role(app: QApplication) -> None:
    window = AssistantWindow()
    window._set_state("danger", "Fehler")
    assert window.state.text().startswith("✕") and window.state.property("role") == "danger"
    window._set_state("success", "Fertig")
    assert window.state.text().startswith("✓")


def test_default_simulation_shows_two_charts_and_more_on_request(app: QApplication, tmp_path: Path) -> None:
    window = AssistantWindow()
    path = tmp_path / "p.json"
    path.write_text(demo_project().model_dump_json(), encoding="utf-8")
    window.open_project_file(path)
    window.tabs.setCurrentIndex(3)
    window._redraw_simulation()
    assert len(window.figure.axes) == 2
    window.more_charts.setChecked(True)
    assert len(window.figure.axes) == 4


def test_tabs_are_grouped_and_branding_is_subtle(app: QApplication) -> None:
    window = AssistantWindow()
    names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert names == ["Entwürfe", "Variantenvergleich", "Zeichnungen", "Simulation", "Stückliste", "Zuschnitt"]
    assert window.export_button.objectName() == "primary" and window.create_button.objectName() == "primary"
    assert window.statusBar().findChild(type(window.state), "brand").text() == "Ackerschewski_code"


def test_expert_window_follows_mode_and_hides_three_way_fields(app: QApplication) -> None:
    window = MainWindow()
    window.set_mode("dark")
    assert "#121212" in window.styleSheet() and window.calculate_button.objectName() == "primary"
    assert window._crossover_form.isRowVisible(window.upper_frequency) is False
    window.crossover_ways.setCurrentIndex(window.crossover_ways.findData(3))
    assert window._crossover_form.isRowVisible(window.upper_frequency) is True
