# Rev 0.1.0

"""Entry point for the AssetForge desktop application."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, Qt

from src.logging_setup import setup_logging
from src.repositories.db import Database
from src.utils.paths import DB_PATH, ensure_runtime_dirs
from src.ui.main_window import MainWindow


def main() -> int:
    """Boot the Qt application, ensuring migrations and logging are ready."""
    ensure_runtime_dirs()
    logger = setup_logging()
    logger.info("AssetForge starting up")

    with Database(DB_PATH) as db:
        applied = db.run_migrations()
        if applied:
            logger.info("Applied migrations: %s", ", ".join(applied))
        else:
            logger.info("Database already up-to-date")

        app = QApplication(sys.argv)
        QCoreApplication.setOrganizationName("assetforge")
        QCoreApplication.setApplicationName("AssetForge")
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)

        window = MainWindow(database=db)
        window.show()
        exit_code = app.exec()

    logger.info("AssetForge shutting down with code %s", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
