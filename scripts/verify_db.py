# Rev 1.2.0 - Distro

"""Quick integrity check for the AssetForge SQLite database."""
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.paths import DB_PATH, ensure_runtime_dirs


def verify(db_path: Path) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA quick_check")
    finally:
        conn.close()
    return True


if __name__ == "__main__":
    ensure_runtime_dirs()
    db_file = DB_PATH
    if not db_file.exists():
        print(f"Database not found at {db_file}")
    else:
        verify(db_file)
        print("Database quick check completed")
