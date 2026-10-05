"""mypy --strict stays green for all calculation, export and data packages."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(importlib.util.find_spec("mypy") is None, reason="mypy not installed")
def test_mypy_strict_has_no_findings() -> None:
    result = subprocess.run([sys.executable, "-m", "mypy"], cwd=ROOT, capture_output=True, text=True, timeout=600,
                            check=False)
    assert result.returncode == 0, result.stdout[-3000:]


def test_typed_package_marker_is_present() -> None:
    assert (ROOT / "src" / "lautsprecher_konstruktion" / "py.typed").is_file()


def test_ui_is_the_only_strict_exception() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'module = ["lautsprecher_konstruktion.ui.*", "lautsprecher_konstruktion.app"]' in text
    assert text.count("ignore_errors = true") == 1
