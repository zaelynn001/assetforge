# Rev 1.2.0 - Distro

from __future__ import annotations

import importlib
from pathlib import Path


def test_paths_respect_environment_overrides(monkeypatch, tmp_path) -> None:
    import src.utils.paths as paths

    custom_data = tmp_path / "data-home"
    custom_state = tmp_path / "state-home"
    monkeypatch.setenv("ASSETFORGE_DATA_DIR", str(custom_data))
    monkeypatch.setenv("ASSETFORGE_STATE_DIR", str(custom_state))

    try:
        module = importlib.reload(paths)

        assert module.DATA_HOME == custom_data
        assert module.STATE_HOME == custom_state
        assert module.DB_PATH == custom_data / "inventory.db"
        assert module.EXPORT_DIR == custom_data / "exports"
        assert module.LOG_DIR == custom_state / "logs"

        module.ensure_runtime_dirs()

        assert module.DB_PATH.parent.exists()
        assert module.EXPORT_DIR.exists()
        assert module.LOG_DIR.exists()
    finally:
        monkeypatch.delenv("ASSETFORGE_DATA_DIR", raising=False)
        monkeypatch.delenv("ASSETFORGE_STATE_DIR", raising=False)
        importlib.reload(paths)
