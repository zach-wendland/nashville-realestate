from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

try:  # Support running as a standalone script.
    from db.db_migrator import (
        PRIMARY_KEY_COLUMN,
        SQLITE_DB,
        TABLE_NAME,
        ensure_table_exists,
        load_schema,
    )
except ImportError:  # pragma: no cover - executed only when run directly.
    import sys

    REPO_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(REPO_ROOT))
    from db.db_migrator import (
        PRIMARY_KEY_COLUMN,
        SQLITE_DB,
        TABLE_NAME,
        ensure_table_exists,
        load_schema,
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _default_destination(path: Path) -> Path:
    suffix = path.suffix or ".db"
    return path.with_name(f"{path.stem}_pk_test{suffix}")


def migrate_database(source: Path, destination: Path, overwrite: bool = False) -> Path:
    """Copy the source DB to destination (unless in-place) and ensure the PK schema is applied."""
    if not source.exists():
        raise FileNotFoundError(f"Source database not found: {source}")

    if source != destination:
        if destination.exists():
            if not overwrite:
                raise FileExistsError(
                    f"Destination database already exists: {destination}. "
                    "Pass --overwrite to replace it."
                )
            destination.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        logging.info("Copied %s to %s for migration.", source, destination)

    schema = load_schema(extra_columns=["INGESTION_DATE", PRIMARY_KEY_COLUMN])
    ensure_table_exists(destination, TABLE_NAME, schema)
    logging.info(
        "Primary-key migration complete for %s (table: %s).",
        destination,
        TABLE_NAME,
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a test copy of the rental database and upgrade it to the new primary-key schema."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SQLITE_DB,
        help=f"Path to the source SQLite database (default: {SQLITE_DB}).",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        help="Destination path for the migrated test database. Defaults to '<source>_pk_test.db'.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Migrate the source database directly (no copy). Use with caution.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting the destination database if it already exists.",
    )

    args = parser.parse_args()
    source = args.source
    destination = source if args.in_place else (args.destination or _default_destination(source))
    migrate_database(source, destination, overwrite=args.overwrite or args.in_place)


if __name__ == "__main__":
    main()
