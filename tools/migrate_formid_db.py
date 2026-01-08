"""Migration script for FormID database optimization.

This script adds covering indexes to existing FormID databases to enable
index-only queries. The covering index includes (formid, plugin, entry)
allowing SELECT queries to be satisfied entirely from the index without
requiring table lookups for the entry column.

Performance Impact:
    The covering index provides 2-5x speedup for batch FormID lookups by
    eliminating table lookups. This is especially beneficial when scanning
    50+ crash logs with large FormID databases (100+ MB).

Usage:
    python migrate_formid_db.py [database_paths...]

    If no paths provided, migrates all databases in standard locations.

Example:
    # Migrate specific database
    python migrate_formid_db.py Fallout4_FormIDs.db

    # Migrate all databases in default locations
    python migrate_formid_db.py

"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

# Default database locations relative to CLASSIC root
DEFAULT_DB_LOCATIONS = [
    "CLASSIC Data/Databases/Fallout4 FormIDs (MAIN).db",
    "CLASSIC Data/Databases/Fallout4 FormIDs (LOCAL).db",
    "CLASSIC Data/Databases/Skyrim FormIDs (MAIN).db",
    "CLASSIC Data/Databases/Skyrim FormIDs (LOCAL).db",
    "CLASSIC Data/Databases/Starfield FormIDs (MAIN).db",
    "CLASSIC Data/Databases/Starfield FormIDs (LOCAL).db",
]

# Supported game table names
GAME_TABLES = ["Fallout4", "Skyrim", "Starfield"]


def get_classic_root() -> Path:
    """Determine the CLASSIC root directory.

    Returns:
        Path to the CLASSIC root directory.

    Raises:
        FileNotFoundError: If CLASSIC root cannot be determined.

    """
    # Try relative to this script
    script_dir = Path(__file__).parent
    root_candidates = [
        script_dir.parent,  # tools/ is one level down from root
        Path.cwd(),
        Path.cwd().parent,
    ]

    for candidate in root_candidates:
        if (candidate / "CLASSIC Data").is_dir():
            return candidate

    raise FileNotFoundError(
        "Cannot determine CLASSIC root directory. Please run from CLASSIC directory or specify database paths explicitly."
    )


def get_existing_indexes(conn: sqlite3.Connection, table: str) -> set[str]:
    """Get all existing index names for a table.

    Args:
        conn: SQLite database connection.
        table: Name of the table to check indexes for.

    Returns:
        Set of index names that exist for the table.

    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?", (table,))
    return {row[0] for row in cursor.fetchall()}


def get_tables_in_database(conn: sqlite3.Connection) -> list[str]:
    """Get all game tables present in the database.

    Args:
        conn: SQLite database connection.

    Returns:
        List of game table names found in the database.

    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = {row[0] for row in cursor.fetchall()}
    return [table for table in GAME_TABLES if table in all_tables]


def add_covering_index(
    conn: sqlite3.Connection,
    table: str,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Add covering index to a game table.

    The covering index includes (formid, plugin COLLATE nocase, entry) which
    allows queries that SELECT formid, plugin, entry to be satisfied entirely
    from the index without table lookups.

    Args:
        conn: SQLite database connection.
        table: Name of the game table (e.g., "Fallout4").
        dry_run: If True, only report what would be done.
        verbose: If True, print detailed progress.

    Returns:
        True if index was added (or would be added in dry run), False if already exists.

    """
    index_name = f"{table}_covering_idx"
    existing_indexes = get_existing_indexes(conn, table)

    if index_name in existing_indexes:
        if verbose:
            print(f"  ✓ Covering index '{index_name}' already exists")
        return False

    if dry_run:
        print(f"  Would create covering index '{index_name}' on {table}")
        return True

    if verbose:
        print(f"  Creating covering index '{index_name}'...")

    start_time = time.time()
    cursor = conn.cursor()
    cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} (formid, plugin COLLATE nocase, entry)")
    conn.commit()
    elapsed = time.time() - start_time

    if verbose:
        print(f"  ✓ Created '{index_name}' in {elapsed:.2f}s")

    return True


def analyze_table(
    conn: sqlite3.Connection,
    table: str,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Run ANALYZE on a table to update query planner statistics.

    Args:
        conn: SQLite database connection.
        table: Name of the table to analyze.
        dry_run: If True, only report what would be done.
        verbose: If True, print detailed progress.

    """
    if dry_run:
        if verbose:
            print(f"  Would run ANALYZE on {table}")
        return

    if verbose:
        print(f"  Running ANALYZE on {table}...")

    cursor = conn.cursor()
    cursor.execute(f"ANALYZE {table}")
    conn.commit()

    if verbose:
        print(f"  ✓ ANALYZE complete for {table}")


def migrate_database(
    db_path: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, bool]:
    """Migrate a single database file to add covering indexes.

    Args:
        db_path: Path to the SQLite database file.
        dry_run: If True, only report what would be done.
        verbose: If True, print detailed progress.

    Returns:
        Dictionary mapping table names to whether they were modified.

    Raises:
        FileNotFoundError: If database file does not exist.
        sqlite3.DatabaseError: If database operation fails.

    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    results: dict[str, bool] = {}

    print(f"\nMigrating: {db_path}")

    with sqlite3.connect(db_path) as conn:
        tables = get_tables_in_database(conn)

        if not tables:
            print("  No game tables found in database")
            return results

        for table in tables:
            if verbose:
                print(f"\n  Processing table: {table}")

            modified = add_covering_index(conn, table, dry_run=dry_run, verbose=verbose)
            results[table] = modified

            if modified and not dry_run:
                analyze_table(conn, table, dry_run=dry_run, verbose=verbose)

    return results


def main() -> int:
    """Run the FormID database migration.

    Returns:
        Exit code (0 for success, non-zero for errors).

    """
    parser = argparse.ArgumentParser(
        description="Add covering indexes to FormID databases for improved query performance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Migrate all databases in default locations
    python migrate_formid_db.py

    # Migrate specific database
    python migrate_formid_db.py path/to/Fallout4.db

    # Preview changes without modifying
    python migrate_formid_db.py --dry-run

    # Verbose output
    python migrate_formid_db.py -v
""",
    )
    parser.add_argument(
        "databases",
        nargs="*",
        help="Database file paths to migrate. If not specified, migrates default locations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed progress information.",
    )
    args = parser.parse_args()

    # Determine database paths
    if args.databases:
        db_paths = [Path(p) for p in args.databases]
    else:
        try:
            root = get_classic_root()
            db_paths = [root / loc for loc in DEFAULT_DB_LOCATIONS]
            db_paths = [p for p in db_paths if p.exists()]
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if not db_paths:
        print("No databases found to migrate.", file=sys.stderr)
        print("Specify database paths or run from CLASSIC directory.", file=sys.stderr)
        return 1

    print("=" * 60)
    print("FormID Database Optimization Migration")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]")

    total_modified = 0
    total_tables = 0
    errors = []

    for db_path in db_paths:
        try:
            results = migrate_database(db_path, dry_run=args.dry_run, verbose=args.verbose)
            total_tables += len(results)
            total_modified += sum(1 for modified in results.values() if modified)
        except FileNotFoundError:
            if args.verbose:
                print(f"  Skipping (not found): {db_path}")
        except sqlite3.DatabaseError as e:
            errors.append((db_path, str(e)))
            print(f"  ERROR: {e}", file=sys.stderr)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Databases processed: {len(db_paths)}")
    print(f"Tables checked: {total_tables}")
    print(f"Indexes added: {total_modified}")

    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for path, error in errors:
            print(f"  - {path}: {error}")
        return 1

    if args.dry_run:
        print("\n[DRY RUN - No changes were made]")
    else:
        print("\n✓ Migration complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
