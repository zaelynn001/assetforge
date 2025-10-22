# Rev 1.0.0

"""Thin launcher wrapper so `python -m src.app_launcher` works."""
from __future__ import annotations

from src.main import main


if __name__ == "__main__":
    raise SystemExit(main())
