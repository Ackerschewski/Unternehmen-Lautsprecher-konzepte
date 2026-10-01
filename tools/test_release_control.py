from pathlib import Path

from tools import release_control as rc


def test_pass_values_include_not_required():
    assert "PASS" in rc.PASS_VALUES
    assert "NOT_REQUIRED" in rc.PASS_VALUES


def test_version_regex():
    assert rc.VERSION_RE.fullmatch("V-01.03.00")
    assert rc.VERSION_RE.fullmatch("V-01.03.00-RC1")
    assert not rc.VERSION_RE.fullmatch("1.3.0")
