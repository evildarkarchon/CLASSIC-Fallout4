"""
Pure Python implementation of database operations.

This module provides the fallback Python implementation for database
connection pooling and operations when Rust acceleration is not available.
It provides a simple async database pool for FormID lookups.
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class PythonDatabasePool:
    """
    Pure Python implementation of an async database connection pool.

    This class provides the fallback implementation for database operations,
    managing SQLite connections and providing async methods for FormID lookups.
    It uses thread pool executors to run synchronous SQLite operations asynchronously.

    Attributes:
        db_path: Path to the SQLite database file.
        pool_size: Maximum number of connections in the pool.
        connections: List of available database connections.
        lock: Async lock for thread-safe connection management.
    """

    def __init__(self, db_path: Path | str, pool_size: int = 5) -> None:
        """
        Initialize the database pool with the specified configuration.

        Args:
            db_path: Path to the SQLite database file.
            pool_size: Maximum number of connections to maintain.
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.pool_size = pool_size
        self.connections: list[sqlite3.Connection] = []
        self.lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the database connection pool.

        Creates the initial set of connections and verifies database accessibility.
        This method should be called before using the pool.
        """
        if self._initialized:
            return

        async with self.lock:
            if self._initialized:  # Double-check after acquiring lock
                return

            try:
                # Verify database exists and is accessible
                if not self.db_path.exists():
                    raise FileNotFoundError(f"Database not found: {self.db_path}")

                # Create initial connections
                for _ in range(min(self.pool_size, 3)):  # Start with fewer connections
                    conn = await asyncio.to_thread(self._create_connection)
                    if conn:
                        self.connections.append(conn)

                self._initialized = True
                logger.info(f"Database pool initialized with {len(self.connections)} connections")

            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise

    def _create_connection(self) -> sqlite3.Connection | None:
        """
        Create a new SQLite database connection.

        Returns:
            sqlite3.Connection: New database connection or None if failed.
        """
        try:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None

    async def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool or create a new one if needed.

        Returns:
            sqlite3.Connection: Database connection from the pool.
        """
        async with self.lock:
            # Try to get existing connection
            if self.connections:
                return self.connections.pop()

            # Create new connection if pool is empty
            conn = await asyncio.to_thread(self._create_connection)
            if conn:
                return conn
            else:
                raise RuntimeError("Failed to create database connection")

    async def _return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool for reuse.

        Args:
            conn: Database connection to return to the pool.
        """
        async with self.lock:
            if len(self.connections) < self.pool_size:
                self.connections.append(conn)
            else:
                # Close excess connections
                conn.close()

    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """
        Look up a single FormID entry in the database.

        Args:
            formid: The FormID to look up.
            plugin: The plugin associated with the FormID.

        Returns:
            str | None: The FormID description if found, otherwise None.
        """
        if not self._initialized:
            await self.initialize()

        conn = await self._get_connection()
        try:
            # Execute query in thread pool
            result = await asyncio.to_thread(
                self._execute_query_single,
                conn,
                "SELECT description FROM formids WHERE formid = ? AND plugin = ?",
                (formid, plugin)
            )
            return result
        finally:
            await self._return_connection(conn)

    async def get_entries_batch(self, formid_plugin_pairs: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
        """
        Look up multiple FormID entries in a single batch operation.

        This method is optimized for batch lookups, reducing database round-trips.

        Args:
            formid_plugin_pairs: List of (formid, plugin) tuples to look up.

        Returns:
            dict: Mapping of (formid, plugin) tuples to their descriptions.
        """
        if not self._initialized:
            await self.initialize()

        if not formid_plugin_pairs:
            return {}

        conn = await self._get_connection()
        try:
            # Build batch query
            placeholders = ",".join(["(?, ?)"] * len(formid_plugin_pairs))
            query = f"""
                SELECT formid, plugin, description
                FROM formids
                WHERE (formid, plugin) IN ({placeholders})
            """

            # Flatten the pairs for query parameters
            params = [item for pair in formid_plugin_pairs for item in pair]

            # Execute batch query
            results = await asyncio.to_thread(
                self._execute_query_batch,
                conn,
                query,
                params
            )

            # Convert to dictionary
            return {(row["formid"], row["plugin"]): row["description"] for row in results}

        finally:
            await self._return_connection(conn)

    def _execute_query_single(self, conn: sqlite3.Connection, query: str, params: tuple) -> str | None:
        """
        Execute a query that returns a single result.

        Args:
            conn: Database connection to use.
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            str | None: Single result value or None if not found.
        """
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row["description"] if row else None
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return None

    def _execute_query_batch(self, conn: sqlite3.Connection, query: str, params: list) -> list[dict]:
        """
        Execute a query that returns multiple results.

        Args:
            conn: Database connection to use.
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            list[dict]: List of result rows as dictionaries.
        """
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Database batch query error: {e}")
            return []

    async def close(self) -> None:
        """
        Close all connections in the pool.

        This method should be called when the pool is no longer needed.
        """
        async with self.lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()
            self._initialized = False
            logger.info("Database pool closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

# Alias for compatibility
AsyncDatabasePool = PythonDatabasePool
