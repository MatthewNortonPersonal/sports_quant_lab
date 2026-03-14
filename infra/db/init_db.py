"""
Initialize the SQLite database from schema.sql.

Usage:
    python -m infra.db.init_db
    python -m infra.db.init_db --db-path path/to/custom.db
"""

import argparse
import sqlite3
from pathlib import Path


def init_db(db_path: str = "data/quant_lab.db") -> None:
    """
    Create the SQLite database and initialize the schema.

    Safe to re-run — uses CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS,
    so calling this on an existing database won't destroy data.

    Args:
        db_path: Path to the SQLite database file. Parent directory is created
                 if it doesn't exist.
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    schema_path = Path(__file__).parent / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()

    print(f"Database initialized at {db_file.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the quant lab SQLite database")
    parser.add_argument(
        "--db-path",
        default="data/quant_lab.db",
        help="Path to the database file (default: data/quant_lab.db)",
    )
    args = parser.parse_args()
    init_db(args.db_path)
