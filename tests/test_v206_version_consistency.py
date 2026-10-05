"""One version source: lautsprecher_konstruktion.__version__."""
import json
import tomllib
from pathlib import Path

from lautsprecher_konstruktion import REVISION, __version__, revision_label
from lautsprecher_konstruktion.project.models import SpeakerProject

ROOT = Path(__file__).resolve().parents[1]


def test_revision_label_format() -> None:
    assert revision_label("2.6.0") == "V-02.06.00"
    assert revision_label("12.0.3") == "V-12.00.03"
    assert REVISION == revision_label(__version__)


def test_package_metadata_matches() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == __version__


def test_documents_and_scripts_name_the_current_revision() -> None:
    status = json.loads((ROOT / "docs/application/PROJECT_STATUS.json").read_text(encoding="utf-8"))
    assert status["version"] == REVISION
    assert REVISION in (ROOT / "APP_README.md").read_text(encoding="utf-8").splitlines()[0]
    assert REVISION in (ROOT / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert (ROOT / f"scripts/package_v{__version__.split('.')[0]}{__version__.split('.')[1]:0>2}.py").is_file()
    assert (ROOT / f"docs/application/BUILD_REPORT_{REVISION}.md").is_file()
    assert f"## {REVISION}" in (ROOT / "APP_README.md").read_text(encoding="utf-8")


def test_new_projects_carry_the_current_revision() -> None:
    from lautsprecher_konstruktion.project.demo import demo_project
    assert demo_project().revision == REVISION
    assert SpeakerProject.model_validate_json(demo_project().model_dump_json()).revision == REVISION
