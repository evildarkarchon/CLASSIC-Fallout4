"""
Async utilities for crash log scanning.

This module provides async versions of I/O-bound operations to improve
performance through concurrent execution.
"""

import asyncio
from pathlib import Path
from typing import Any

import aiofiles
import aiosqlite

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS
from ClassicLib.Logger import logger


class AsyncDatabasePool:
    """Manages a pool of async database connections for FormID lookups."""
    
    def __init__(self, max_connections: int = 5) -> None:
        """Initialize the database connection pool."""
        self.max_connections = max_connections
        self.connections: dict[Path, aiosqlite.Connection] = {}
        self.query_cache: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()
        
    async def __aenter__(self) -> "AsyncDatabasePool":
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self) -> None:
        """Initialize database connections."""
        async with self._lock:
            for db_path in DB_PATHS:
                if db_path.is_file():
                    try:
                        conn = await aiosqlite.connect(db_path)
                        self.connections[db_path] = conn
                        logger.debug(f"Opened async connection to {db_path}")
                    except (OSError, aiosqlite.Error) as e:
                        logger.error(f"Failed to open database {db_path}: {e}")
                        
    async def close(self) -> None:
        """Close all database connections."""
        async with self._lock:
            for conn in self.connections.values():
                await conn.close()
            self.connections.clear()
            
    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """
        Async version of FormID database lookup with caching.
        
        Args:
            formid: The FormID to look up
            plugin: The plugin name
            
        Returns:
            The database entry or None if not found
        """
        # Check cache first
        cache_key = (formid, plugin)
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
            
        # Query databases
        game_table = GlobalRegistry.get_game()
        query = f"SELECT entry FROM {game_table} WHERE formid=? AND plugin=? COLLATE nocase"
        
        for db_path, conn in self.connections.items():
            try:
                async with conn.execute(query, (formid, plugin)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        entry = result[0]
                        self.query_cache[cache_key] = entry
                        return entry
            except (aiosqlite.Error, OSError) as e:
                logger.error(f"Database query error in {db_path}: {e}")
                
        return None


async def read_file_async(file_path: Path) -> list[str]:
    """
    Asynchronously read a file and return its lines.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        List of lines from the file
    """
    try:
        async with aiofiles.open(file_path, encoding='utf-8', errors='ignore') as f:
            content = await f.read()
            return content.splitlines()
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []


async def write_file_async(file_path: Path, content: str) -> None:
    """
    Asynchronously write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write
    """
    try:
        async with aiofiles.open(file_path, mode='w', encoding='utf-8', errors='ignore') as f:
            await f.write(content)
    except (OSError, UnicodeEncodeError) as e:
        logger.error(f"Error writing {file_path}: {e}")


async def load_crash_logs_async(crashlog_list: list[Path]) -> dict[str, list[str]]:
    """
    Asynchronously load all crash logs into memory.
    
    Args:
        crashlog_list: List of crash log paths
        
    Returns:
        Dictionary mapping log names to their content lines
    """
    cache: dict[str, list[str]] = {}
    
    async def load_single_log(file_path: Path) -> tuple[str, list[str]]:
        """Load a single log file."""
        lines = await read_file_async(file_path)
        return file_path.name, lines
        
    # Load all logs concurrently
    tasks = [load_single_log(log_path) for log_path in crashlog_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Failed to load log: {result}")
        else:
            name, lines = result
            cache[name] = lines
            
    return cache


async def batch_file_operations(operations: list[tuple[str, Path, Any]]) -> None:
    """
    Execute multiple file operations concurrently.
    
    Args:
        operations: List of (operation_type, path, data) tuples
                   where operation_type is 'read', 'write', 'move', etc.
    """
    async def execute_operation(op_type: str, path: Path, data: Any) -> None:
        """Execute a single file operation."""
        if op_type == 'read':
            return await read_file_async(path)
        if op_type == 'write':
            return await write_file_async(path, data)
        if op_type == 'move' and isinstance(data, Path):
            # Use asyncio's thread pool for blocking operations
            await asyncio.to_thread(path.rename, data)
            return None
        if op_type == 'copy' and isinstance(data, Path):
            import shutil
            await asyncio.to_thread(shutil.copy2, path, data)
            return None
        return None
            
    tasks = [execute_operation(op_type, path, data) for op_type, path, data in operations]
    await asyncio.gather(*tasks, return_exceptions=True)