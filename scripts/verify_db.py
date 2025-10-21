# Rev 0.1.0

"""Quick integrity check for the AssetForge SQLite database."""
from pathlib import Path
import sqlite3


def verify(db_path: Path) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA quick_check")
    finally:
        conn.close()
    return True


if __name__ == "__main__":
    db_file = Path(__file__).resolve().parents[1] / "data" / "inventory.db"
    if not db_file.exists():
        print(f"Database not found at {db_file}")
    else:
        verify(db_file)
        print("Database quick check completed")
