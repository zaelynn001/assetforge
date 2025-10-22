# Rev 1.0.0

"""Placeholder asset tag generation test."""
from src.utils.timestamp import now_iso


def test_now_iso_includes_t_separator() -> None:
    assert "T" in now_iso()
