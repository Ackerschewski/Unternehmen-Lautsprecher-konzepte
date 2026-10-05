"""Lautsprecher Konstruktion."""

__version__ = "2.6.0"


def revision_label(version: str = __version__) -> str:
    """Project revision label, e.g. 2.6.0 -> V-02.06.00."""
    major, minor, patch = (int(part) for part in version.split("."))
    return f"V-{major:02d}.{minor:02d}.{patch:02d}"


REVISION = revision_label()
