"""
Pure Python implementation of database operations.

This module provides the fallback Python implementation for database
connection pooling and operations when Rust acceleration is not available.
It provides a simple async database pool for FormID lookups.
"""

import asyncio
import logging
import sqlite3
from pathlib import Path

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
        Initializes the database connection pool and verifies database accessibility.

        This method ensures that the database pool is initialized only once, even if
        called multiple times concurrently. It verifies the existence and accessibility
        of the database and creates a pool of initial connections.

        Raises:
            FileNotFoundError: If the specified database file does not exist.
            Exception: If an unexpected error occurs during initialization.
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
        Creates and returns a connection to the SQLite database.

        This method attempts to establish a connection to the SQLite database using
        the provided database path. If the connection is successful, it enables
        column access by name using `sqlite3.Row`. If the connection cannot be
        established, it logs an error and returns `None`.

        Returns:
            sqlite3.Connection | None: A connection object to interact with the SQLite
            database if successful. Returns `None` if the connection fails.
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
        Retrieves a database connection from the pool or creates a new one if the pool is empty.

        This method manages a pool of database connections and ensures thread-safe access. If a connection
        is available in the pool, it is returned. If not, a new connection is created by invoking the
        connection creation logic. If the creation of the new connection fails, an exception is raised.

        Returns:
            sqlite3.Connection: An active SQLite connection.

        Raises:
            RuntimeError: If a new database connection cannot be created.
        """
        async with self.lock:
            # Try to get existing connection
            if self.connections:
                return self.connections.pop()

            # Create new connection if pool is empty
            conn = await asyncio.to_thread(self._create_connection)
            if conn:
                return conn
            raise RuntimeError("Failed to create database connection")

    async def _return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Manages the return of a database connection to the connection pool. Ensures thread-safe
        handling of connections and avoids exceeding the pool size by closing excess connections.

        Args:
            conn (sqlite3.Connection): The database connection to return to the pool.
        """
        async with self.lock:
            if len(self.connections) < self.pool_size:
                self.connections.append(conn)
            else:
                # Close excess connections
                conn.close()

    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """
        Fetches the description of a form entry by formid and plugin from the database.

        This asynchronous method retrieves a single entry's description from the database
        based on the provided formid and plugin. It ensures the connection is properly
        initialized and returned after use. If the queried entry does not exist, it returns None.

        Args:
            formid (str): The unique identifier of the form entry to be retrieved.
            plugin (str): The name of the plugin associated with the form entry.

        Returns:
            str | None: The description of the form entry if found, otherwise None.
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
        Fetches entries for a batch of (formid, plugin) pairs from the database asynchronously.

        This method retrieves descriptions corresponding to each provided (formid, plugin) pair
        from the database in a batch operation. It establishes a database connection,
        executes the batch query, and processes the results into a dictionary. The method
        handles connection management and ensures proper functioning even if the input list
        is empty.

        Args:
            formid_plugin_pairs: A list of tuples where each tuple contains the form ID and
                plugin as strings.

        Returns:
            A dictionary mapping each (formid, plugin) tuple to its corresponding description
            as a string.

        Raises:
            Any database-related exceptions encountered while executing the query will be raised.
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
        Executes a single query on a SQLite database and retrieves the description of the
        first row if available.

        Args:
            conn (sqlite3.Connection): A connection object to the SQLite database.
            query (str): The query string to be executed.
            params (tuple): The parameters for the query.

        Returns:
            str | None: The value of the "description" field from the first row, or None
            if no such row exists or an error occurs.
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
        Executes a batch SQL query on the given SQLite connection.

        This method executes a query with provided parameters against a SQLite database connection,
        fetches all results, and processes them into a list of dictionaries. If an error occurs
        during query execution, it logs the error and returns an empty list.

        Args:
            conn (sqlite3.Connection): The SQLite database connection where the query will be executed.
            query (str): The SQL query to be executed.
            params (list): A list of parameters to pass to the SQL query.

        Returns:
            list[dict]: A list of dictionaries representing the rows returned by the query. If
            an error occurs, an empty list is returned.
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
        Closes all database connections in the connection pool.

        This method ensures all connections in the pool are properly closed,
        the pool is emptied, and its status is updated to reflect that it is no
        longer initialized. It uses an asynchronous lock to prevent concurrent
        access while performing these operations.

        Raises:
            None

        Returns:
            None
        """
        async with self.lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()
            self._initialized = False
            logger.info("Database pool closed")

    async def __aenter__(self):
        """
        Handles asynchronous context management for the class. Ensures proper initialization
        of necessary resources before entering the context.

        Returns:
            self: The initialized instance of the class, ready for use within the
            asynchronous context.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Handles the asynchronous exit of an async context manager by performing necessary cleanup actions,
        such as closing connections or resources.

        Args:
            exc_type: The exception type if an exception was raised during the execution of the context.
            exc_val: The exception value if an exception was raised.
            exc_tb: The traceback object if an exception was raised.
        """
        await self.close()

# Alias for compatibility
AsyncDatabasePool = PythonDatabasePool
