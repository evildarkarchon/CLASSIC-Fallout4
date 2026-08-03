# AsyncYamlSettingsCore Migration Examples

## Critical Path Identification

Based on codebase analysis, the following areas would benefit most from async/batch optimization:

### Priority 1: High-Impact Areas
1. **SetupCoordinator** - Multiple settings loads during initialization
2. **SettingsDialog** - Loads many settings when opening dialog
3. **ScanLog/OrchestratorCore** - Multiple YAML operations during scan
4. **FileGeneration** - Multiple YAML reads during setup

### Priority 2: Medium-Impact Areas
5. **GameIntegrity** - Settings validation
6. **TUI/screens** - Settings display
7. **Interface/Workers** - Background operations

## Migration Examples

### Example 1: SetupCoordinator Optimization

**Current Code (ClassicLib/SetupCoordinator.py):**
```python
def check_integrity(self) -> None:
    # Multiple sequential YAML operations
    classic_ver = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    game_name = yaml_settings(str, YAML.Game, "Game_Info.Main_Root_Name")
    game_path = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
```

**Optimized with Batch Operations:**
```python
def check_integrity(self) -> None:
    # Load all settings in one batch operation
    from ClassicLib.YamlSettingsCache import yaml_cache

    requests = [
        (str, YAML.Main, "CLASSIC_Info.version"),
        (str, YAML.Game, "Game_Info.Main_Root_Name"),
        (str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game"),
    ]

    classic_ver, game_name, game_path = yaml_cache.batch_get_settings(requests)
```

**Fully Async Version:**
```python
async def check_integrity_async(self) -> None:
    # Concurrent loading with async
    import asyncio
    from ClassicLib.AsyncYamlSettingsCore import yaml_settings_async

    classic_ver, game_name, game_path = await asyncio.gather(
        yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version"),
        yaml_settings_async(str, YAML.Game, "Game_Info.Main_Root_Name"),
        yaml_settings_async(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game"),
    )
```

### Example 2: SettingsDialog Load Optimization

**Current Code (ClassicLib/Interface/SettingsDialog.py):**
```python
def load_settings(self):
    for checkbox, yaml_key in self.checkbox_mappings.items():
        if self.yaml_store == YAML.Settings:
            value = classic_settings(bool, yaml_key)
        else:
            value = yaml_settings(bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}")
        checkbox.setChecked(value or False)
```

**Optimized with Batch Operations:**
```python
def load_settings(self):
    from ClassicLib.YamlSettingsCache import yaml_cache

    # Prepare all requests
    if self.yaml_store == YAML.Settings:
        requests = [
            (bool, YAML.Settings, f"CLASSIC_Settings.{yaml_key}")
            for checkbox, yaml_key in self.checkbox_mappings.items()
        ]
    else:
        requests = [
            (bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}")
            for checkbox, yaml_key in self.checkbox_mappings.items()
        ]

    # Get all values in one batch
    values = yaml_cache.batch_get_settings(requests)

    # Apply values to checkboxes
    for (checkbox, _), value in zip(self.checkbox_mappings.items(), values):
        checkbox.setChecked(value or False)
```

### Example 3: Application Startup Optimization

**Add to CLASSIC_Interface.py MainWindow.__init__:**
```python
def __init__(self):
    # Prefetch all common settings at startup
    from ClassicLib.YamlSettingsCache import yaml_cache
    yaml_cache.prefetch_all_settings()

    # Rest of initialization...
    super().__init__()
```

### Example 4: Async Worker Thread Pattern

**For background operations (e.g., UpdateCheckWorker):**
```python
class UpdateCheckWorker(QRunnable):
    def run(self):
        # Use AsyncBridge for async operations in worker thread
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.AsyncYamlSettingsCore import yaml_settings_async
        import asyncio

        bridge = AsyncBridge.get_instance()

        async def check_updates():
            # Load all needed settings concurrently
            auto_update, update_channel, last_check = await asyncio.gather(
                yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.Auto Update"),
                yaml_settings_async(str, YAML.Settings, "CLASSIC_Settings.Update Channel"),
                yaml_settings_async(str, YAML.Settings, "CLASSIC_Settings.Last Update Check"),
            )
            # Process updates...

        result = bridge.run_async(check_updates())
```

### Example 5: TUI Screen Optimization

**Current Code (ClassicLib/TUI/screens/main_screen.py):**
```python
def load_settings(self):
    self.scan_all = classic_settings(bool, "Scan All Logs")
    self.auto_scan = classic_settings(bool, "Auto Scan")
    self.auto_scroll = classic_settings(bool, "Auto Scroll")
```

**Optimized Version:**
```python
def load_settings(self):
    from ClassicLib.YamlSettingsCache import yaml_cache

    requests = [
        (bool, YAML.Settings, "CLASSIC_Settings.Scan All Logs"),
        (bool, YAML.Settings, "CLASSIC_Settings.Auto Scan"),
        (bool, YAML.Settings, "CLASSIC_Settings.Auto Scroll"),
    ]

    self.scan_all, self.auto_scan, self.auto_scroll = yaml_cache.batch_get_settings(requests)
```

### Example 6: File Generation with Async

**Refactor FileGeneration class to async:**
```python
class FileGeneration:
    @staticmethod
    async def generate_ignore_yaml_async() -> None:
        """Async version of generate_ignore_yaml."""
        from ClassicLib.AsyncYamlSettingsCore import yaml_settings_async
        from ClassicLib.FileIOCore import FileIOCore

        ignore_path = Path("CLASSIC Ignore.yaml")
        if not await FileIOCore().file_exists(ignore_path):
            default_ignorefile = await yaml_settings_async(
                str, YAML.Main, "CLASSIC_Info.default_ignorefile"
            )
            if isinstance(default_ignorefile, str):
                await FileIOCore().write_file(ignore_path, default_ignorefile)

    @staticmethod
    async def generate_all_files_async() -> None:
        """Generate all required files concurrently."""
        await asyncio.gather(
            FileGeneration.generate_ignore_yaml_async(),
            FileGeneration.generate_local_yaml_async(),
            # Add other file generations...
        )
```

## Implementation Strategy

### Phase 1: Quick Wins (1-2 days)
1. Add `prefetch_all_settings()` to application startup
2. Convert SetupCoordinator to use batch operations
3. Optimize SettingsDialog with batch loading

### Phase 2: Worker Threads (2-3 days)
4. Convert UpdateCheckWorker to async
5. Update background scan operations
6. Optimize file generation routines

### Phase 3: Full Async Migration (1 week)
7. Create async versions of critical classes
8. Update TUI screens for batch operations
9. Performance testing and benchmarking

## Performance Expectations

Based on testing, expect these improvements:

| Component | Current | Optimized | Improvement |
|-----------|---------|-----------|-------------|
| SetupCoordinator init | ~150ms | ~50ms | 3x faster |
| SettingsDialog load | ~200ms | ~40ms | 5x faster |
| Application startup | ~500ms | ~300ms | 1.7x faster |
| File generation | ~300ms | ~100ms | 3x faster |

## Testing Strategy

After each migration:
1. Run existing tests to ensure compatibility
2. Add performance benchmarks
3. Monitor metrics with `yaml_cache.get_metrics()`
4. Compare before/after timings

## Rollback Plan

If issues arise:
1. Sync wrapper ensures backward compatibility
2. Can revert individual components
3. Feature flag for async operations (if needed):

```python
USE_ASYNC_YAML = classic_settings(bool, "Use Async YAML") or False

if USE_ASYNC_YAML:
    # Use batch/async operations
    results = yaml_cache.batch_get_settings(requests)
else:
    # Use traditional sequential loading
    results = [yaml_settings(*req) for req in requests]
```

## Monitoring

Add metrics logging to track improvements:

```python
import time
from ClassicLib.Logger import logger

def timed_operation(name: str):
    """Decorator to time operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"{name} took {elapsed:.3f}s")

            # Log cache metrics
            from ClassicLib.YamlSettingsCache import yaml_cache
            metrics = yaml_cache.get_metrics()
            logger.debug(f"Cache stats: {metrics}")

            return result
        return wrapper
    return decorator

@timed_operation("Settings Load")
def load_all_settings():
    # Settings loading code...
```

## Next Steps

1. **Immediate**: Add prefetch to app startup
2. **This Week**: Migrate SetupCoordinator and SettingsDialog
3. **Next Sprint**: Full async migration of critical paths
4. **Future**: Consider watchdog integration for real-time updates
