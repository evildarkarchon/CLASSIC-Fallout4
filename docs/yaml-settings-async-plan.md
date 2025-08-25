# YamlSettingsCache Async Conversion Implementation Plan

## Overview
Complete refactoring of YamlSettingsCache to an async-first architecture with sync adapters for backward compatibility. This plan prioritizes performance, modern Python 3.12+ features, and clean separation between async core and sync adapters.

## Phase 1: Core Async Implementation

### 1.1 Create AsyncYamlSettingsCore
**Location:** `ClassicLib/AsyncYamlSettingsCore.py`

```python
# Key features:
- Pure async implementation using aiofiles
- asyncio.Lock for thread-safe cache operations
- Async TTL-based cache management
- Support for concurrent YAML operations
```

**Core Structure:**
```python
import asyncio
from pathlib import Path
from collections.abc import Mapping
from typing import ClassVar, TypeVar

class AsyncYamlSettingsCore:
    """Async-first YAML settings management core."""

    # Class-level locks for thread safety
    _cache_locks: ClassVar[dict[Path, asyncio.Lock]] = {}
    _global_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    # Static stores remain unchanged
    STATIC_YAML_STORES: ClassVar[set[YAML]] = {YAML.Main, YAML.Game}
    CACHE_TTL: ClassVar[float] = 5.0

    def __init__(self):
        self.cache: dict[Path, Mapping[str, Any]] = {}
        self.file_mod_times: dict[Path, float] = {}
        self.path_cache: dict[YAML, Path] = {}
        self.settings_cache: dict[tuple[YAML, str, type], Any] = {}
        self.last_check_time: dict[Path, float] = {}
```

### 1.2 Async Method Signatures

```python
async def get_path_for_store(self, yaml_store: YAML) -> Path:
    """Get path for YAML store (remains mostly sync as it's path resolution)."""

async def load_yaml(self, yaml_path: Path) -> Mapping[str, Any]:
    """Async YAML loading with caching."""

async def get_setting[T](
    self,
    _type: type[T],
    yaml_store: YAML,
    key_path: str,
    new_value: T | None = None
) -> T | None:
    """Async get/set for YAML settings."""

async def _check_file_modification(self, yaml_path: Path) -> bool:
    """Async file modification checking."""

async def _load_yaml_file(self, yaml_path: Path) -> Mapping[str, Any]:
    """Async YAML file loading with aiofiles."""

async def _write_yaml_file(self, yaml_path: Path, data: Mapping[str, Any]) -> None:
    """Async YAML file writing."""
```

## Phase 2: File I/O Integration

### 2.1 Leverage Existing FileIOCore
```python
from ClassicLib.FileIOCore import FileIOCore

class AsyncYamlSettingsCore:
    def __init__(self):
        self.io_core = FileIOCore()
        # ... other init

    async def _load_yaml_file(self, yaml_path: Path) -> Mapping[str, Any]:
        """Use FileIOCore for consistent async I/O."""
        content = await self.io_core.read_file(yaml_path)

        # Use ruamel.yaml in executor for CPU-bound parsing
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._parse_yaml_content,
            content
        )
```

### 2.2 Concurrent Operations Support
```python
async def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, Mapping[str, Any]]:
    """Load multiple YAML stores concurrently."""
    tasks = [self.load_yaml(self.get_path_for_store(store)) for store in stores]
    results = await asyncio.gather(*tasks)
    return dict(zip(stores, results))

async def batch_get_settings(
    self,
    requests: list[tuple[type, YAML, str]]
) -> list[Any]:
    """Batch get multiple settings concurrently."""
    tasks = [self.get_setting(t, store, path) for t, store, path in requests]
    return await asyncio.gather(*tasks)
```

## Phase 3: Sync Adapter Implementation

### 3.1 YamlSettingsCache Sync Adapter
**Location:** `ClassicLib/YamlSettingsCache.py` (modified)

```python
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.AsyncYamlSettingsCore import AsyncYamlSettingsCore
from ClassicLib.Meta import SingletonMeta

class YamlSettingsCache(metaclass=SingletonMeta):
    """Sync adapter for AsyncYamlSettingsCore maintaining backward compatibility."""

    def __init__(self):
        self._async_core = AsyncYamlSettingsCore()
        self._bridge = AsyncBridge.get_instance()

        # Mirror async core's attributes for compatibility
        self._sync_cache_proxy()

    def _sync_cache_proxy(self):
        """Create property proxies to async core's cache attributes."""
        # This ensures existing code accessing .cache directly still works

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """Sync adapter for get_path_for_store."""
        return self._bridge.run_async(
            self._async_core.get_path_for_store(yaml_store)
        )

    def load_yaml(self, yaml_path: Path) -> dict[str, Any]:
        """Sync adapter for load_yaml."""
        return self._bridge.run_async(
            self._async_core.load_yaml(yaml_path)
        )

    def get_setting(self, _type, yaml_store, key_path, new_value=None):
        """Sync adapter for get_setting."""
        return self._bridge.run_async(
            self._async_core.get_setting(_type, yaml_store, key_path, new_value)
        )
```

### 3.2 Module-Level Functions Update
```python
# Keep existing yaml_cache singleton
yaml_cache = YamlSettingsCache()

# Update yaml_settings to use sync adapter
def yaml_settings[T](
    _type: type[T],
    yaml_store: YAML,
    key_path: str,
    new_value: T | None = None
) -> T | None:
    """Sync wrapper maintaining existing API."""
    setting = yaml_cache.get_setting(_type, yaml_store, key_path, new_value)
    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None
    return setting

# Add async versions for new code
async def yaml_settings_async[T](
    _type: type[T],
    yaml_store: YAML,
    key_path: str,
    new_value: T | None = None
) -> T | None:
    """Async version for async contexts."""
    # Direct use of async core
    from ClassicLib import GlobalRegistry
    async_core = GlobalRegistry.get(GlobalRegistry.Keys.ASYNC_YAML_CORE)
    setting = await async_core.get_setting(_type, yaml_store, key_path, new_value)
    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None
    return setting
```

## Phase 4: Performance Optimizations

### 4.1 Lock Granularity
```python
class AsyncYamlSettingsCore:
    async def _get_file_lock(self, path: Path) -> asyncio.Lock:
        """Get or create per-file lock for fine-grained locking."""
        async with self._global_lock:
            if path not in self._cache_locks:
                self._cache_locks[path] = asyncio.Lock()
            return self._cache_locks[path]

    async def load_yaml(self, yaml_path: Path) -> Mapping[str, Any]:
        """Use per-file locking for better concurrency."""
        file_lock = await self._get_file_lock(yaml_path)
        async with file_lock:
            # Load logic here
            pass
```

### 4.2 Optimized Cache Invalidation
```python
class AsyncYamlSettingsCore:
    async def _setup_file_watcher(self):
        """Optional: Use watchdog for immediate cache invalidation."""
        # Could integrate with watchdog for real-time updates
        # instead of TTL-based checking for dynamic files
```

### 4.3 Batch Operations
```python
async def prefetch_all_settings(self) -> None:
    """Prefetch all common settings at startup."""
    common_stores = [YAML.Main, YAML.Settings, YAML.Game]
    await self.load_multiple_stores(common_stores)
```

## Phase 5: Migration Strategy

### 5.1 Gradual Migration Path
1. **Week 1-2:** Implement AsyncYamlSettingsCore
2. **Week 2-3:** Create sync adapter maintaining full backward compatibility
3. **Week 3-4:** Test extensively with existing codebase
4. **Week 4+:** Gradually migrate performance-critical paths to use async directly

### 5.2 Testing Strategy
```python
# tests/test_async_yaml_settings.py
import pytest
import asyncio

class TestAsyncYamlSettings:
    @pytest.mark.asyncio
    async def test_concurrent_loads(self):
        """Test concurrent YAML loading."""

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test TTL-based cache invalidation."""

    @pytest.mark.asyncio
    async def test_static_vs_dynamic(self):
        """Test different caching strategies."""
```

### 5.3 Backward Compatibility Tests
```python
def test_sync_adapter_compatibility():
    """Ensure sync adapter maintains exact API compatibility."""
    # Test all existing usage patterns still work
```

## Phase 6: Advanced Features

### 6.1 Async Context Manager
```python
class AsyncYamlSettingsCore:
    async def __aenter__(self):
        """Support async context manager for batch operations."""
        await self.prefetch_all_settings()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context exit."""
        # Could flush any pending writes
```

### 6.2 Performance Monitoring
```python
class AsyncYamlSettingsCore:
    def __init__(self):
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'file_reads': 0,
            'file_writes': 0
        }

    async def get_metrics(self) -> dict[str, int]:
        """Get performance metrics."""
        return self._metrics.copy()
```

## Implementation Checklist

- [ ] Create AsyncYamlSettingsCore.py with full async implementation
- [ ] Integrate with FileIOCore for consistent async I/O
- [ ] Implement per-file locking for better concurrency
- [ ] Create sync adapter in existing YamlSettingsCache.py
- [ ] Add async versions of module-level functions
- [ ] Write comprehensive async tests
- [ ] Test backward compatibility thoroughly
- [ ] Update documentation with async usage examples
- [ ] Performance benchmark async vs sync operations
- [ ] Add metrics/monitoring capabilities
- [ ] Consider watchdog integration for real-time updates
- [ ] Gradual migration of critical paths to async

## Key Benefits

1. **Performance:** Concurrent YAML operations, better I/O utilization
2. **Scalability:** Handles multiple simultaneous settings requests efficiently
3. **Compatibility:** Full backward compatibility through sync adapters
4. **Modern:** Uses Python 3.12+ features and PEP 484 type hints
5. **Maintainable:** Clear separation between async core and sync adapters

## Example Usage

### Async Usage
```python
async def configure_application():
    from ClassicLib.AsyncYamlSettingsCore import AsyncYamlSettingsCore

    core = AsyncYamlSettingsCore()

    # Load multiple settings concurrently
    settings = await asyncio.gather(
        core.get_setting(bool, YAML.Settings, "CLASSIC_Settings.VR Mode"),
        core.get_setting(str, YAML.Game, "Game_Info.XSE_Acronym"),
        core.get_setting(Path, YAML.Settings, "CLASSIC_Settings.MODS Folder Path")
    )

    return settings
```

### Sync Usage (unchanged)
```python
def configure_application_sync():
    # Existing code works without changes
    vr_mode = yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.VR Mode")
    xse_acronym = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    mods_path = classic_settings(Path, "MODS Folder Path")

    return vr_mode, xse_acronym, mods_path
```

## Notes

- AsyncBridge ensures efficient sync-to-async execution without event loop overhead
- Static YAML files remain cached permanently for optimal performance
- Dynamic files continue using TTL-based invalidation
- All existing code continues working through sync adapters
- New async code can leverage full concurrent capabilities
