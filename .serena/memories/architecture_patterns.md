# Architecture Patterns in CLASSIC-Fallout4

## Core Architecture Pattern: Async-First Orchestrator

### Orchestrator Design
The project uses a centralized orchestrator pattern for managing complex operations:

```
OrchestratorCore (async-first)
    ├── FormIDAnalyzer (specialized analyzer)
    ├── RecordScanner (specialized analyzer)
    ├── PluginAnalyzer (specialized analyzer)
    └── MessageHandler (output abstraction)
```

- **OrchestratorCore** (`ClassicLib/ScanLog/OrchestratorCore.py`) - Central async coordinator
- **AsyncScanOrchestrator** - High-level wrapper for orchestration
- **Specialized Analyzers** - Domain-specific processing components

### AsyncBridge Singleton Pattern
Critical for managing async operations in sync contexts:

```python
# Singleton instance manages persistent event loop
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_coroutine)
```

- Prevents event loop conflicts
- Optimized for performance
- Thread-safe implementation
- Replaces deprecated AsyncCore module

## Modular File Organization Pattern

### One-Class-Per-File Structure
Recent refactoring organized code into modular components:

```
ClassicLib/
├── MessageHandler/
│   ├── handler.py        # Main MessageHandler class
│   ├── enums.py         # MessageType, MessageTarget
│   ├── models.py        # Message data class
│   └── __init__.py      # Re-exports for compatibility
```

### Backward Compatibility Pattern
All refactored modules maintain compatibility:

```python
# In __init__.py
from .handler import MessageHandler
from .enums import MessageType, MessageTarget

# Deprecated path still works
__all__ = ['MessageHandler', 'MessageType', 'MessageTarget']

# With deprecation warning
import warnings
warnings.warn("Import from submodule", DeprecationWarning)
```

## Performance Optimization Patterns

### Batch Operations
```python
# YamlSettingsCache batch loading
requests = [
    (str, YAML.Settings, "key1"),
    (bool, YAML.Settings, "key2"),
]
values = yaml_cache.batch_get_settings(requests)
```

### Connection Pooling
```python
# AsyncDatabasePool for FormID lookups
async with AsyncDatabasePool() as pool:
    results = await pool.execute_many(queries)
```

### Concurrent I/O
```python
# File generation with asyncio.gather
results = await asyncio.gather(
    generate_file1(),
    generate_file2(),
    generate_file3()
)
```

## Message Handler Pattern

### Abstracted Output System
```
MessageHandler
    ├── GUI Mode → Qt Dialogs
    ├── TUI Mode → Textual Widgets
    └── CLI Mode → Console Output
```

- Single interface for all output
- Mode detection at initialization
- Progress tracking support
- Thread-safe operations

## Fragment Composition Pattern

### Report Generation
```python
# ReportFragment for composable reports
fragment = ReportFragment(title="Section")
fragment.add_line("Content")
fragment.add_subsection(child_fragment)

# Compose final report
report = ReportComposer.compose(fragments)
```

- Immutable report building
- Hierarchical composition
- Lazy evaluation
- Memory efficient

## Testing Patterns

### Test Organization Structure
```
tests/
├── async_tests/      # Async infrastructure
├── core/            # Core functionality
├── scanning/        # Log scanning
├── game/           # Game operations
└── (no root tests)  # Enforced rule
```

### Test Isolation Pattern
```python
# Production data is READ-ONLY
def test_settings(tmp_path):
    # Use temporary files
    test_file = tmp_path / "test.yaml"

    # Or use TEST enum
    yaml_settings(str, YAML.TEST, "key", "value")

    # NEVER: yaml_settings(str, YAML.Settings, ...)
```

## Async-First Development Pattern

### Core Implementation
```python
# Core is always async
class ScanGameCore:
    async def process(self):
        return await self._async_operation()

# Sync adapter for compatibility
class ScanGame:
    def __init__(self):
        self.core = ScanGameCore()
        self.bridge = AsyncBridge.get_instance()

    def process(self):
        return self.bridge.run_async(self.core.process())
```

## TUI Architecture Pattern

### Screen-Widget-Handler Separation
```
TUI/
├── screens/         # Full-screen interfaces
├── widgets/         # Reusable components
└── handlers/        # Business logic
```

- Screens manage navigation
- Widgets handle UI rendering
- Handlers contain business logic
- Clean separation of concerns

## Setup Coordination Pattern

### Initialization Pipeline
```python
SetupCoordinator
    ├── FileGeneration (async)
    ├── GameIntegrity (validation)
    ├── BackupManager (safety)
    ├── DocumentsChecker (config)
    └── PathValidator (cleanup)
```

- Modular setup components
- Async file generation
- Error recovery
- Progress reporting

## Key Design Principles

1. **Async-First**: Core implementations are async, sync adapters for compatibility
2. **Modular**: One class per file, logical organization
3. **Backward Compatible**: API stability with deprecation paths
4. **Performance Optimized**: Batching, pooling, concurrent operations
5. **Test Isolated**: Production data is read-only in tests
6. **Type Safe**: Complete type annotations throughout
7. **Message Abstracted**: Single interface for all output modes
