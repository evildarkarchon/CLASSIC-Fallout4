# CLASSIC-Fallout4 Codebase Structure

## Root Directory Organization
```
CLASSIC-Fallout4/
├── CLASSIC_Interface.py      # Main GUI entry point (PySide6)
├── CLASSIC_TUI.py            # Terminal UI entry point (Textual)
├── CLASSIC_ScanLogs.py       # CLI entry point & core scanner
├── CLASSIC_ScanGame.py       # Game integrity checker
├── ClassicLib/               # Core library (modular architecture)
├── tests/                    # Test suite (organized by component)
├── CLASSIC Data/             # Configuration & databases
├── docs/                     # Documentation
├── Release/                  # Built executables
├── pyproject.toml           # Poetry configuration
├── pytest.ini               # Test configuration
└── CLAUDE.md                # AI assistant guidance

## ClassicLib Core Structure

### Async Infrastructure
```
ClassicLib/
├── AsyncBridge.py           # Singleton for sync/async bridging
├── FileIOCore.py           # Unified async file operations
├── AsyncYamlSettings/      # Async YAML configuration
│   ├── core.py
│   ├── cache.py
│   └── validators.py
└── PerformanceMonitor.py   # Performance tracking utilities
```

### Scanning Components
```
ClassicLib/ScanLog/
├── OrchestratorCore.py     # Central async orchestrator
├── AsyncScanOrchestrator.py # High-level orchestration
├── fragments/              # Report composition
│   ├── report_fragment.py
│   ├── report_composer.py
│   └── mod_detection.py
├── models/                 # Data models
│   ├── scan_config.py
│   ├── scan_statistics.py
│   └── scan_result.py
├── pipeline/              # Processing pipeline
│   ├── async_crash_log_pipeline.py
│   └── async_performance_monitor.py
└── analyzers/             # Specialized analyzers
    ├── FormIDAnalyzer.py
    ├── RecordScanner.py
    └── PluginAnalyzer.py
```

### UI Components
```
ClassicLib/Interface/
├── Settings/              # Settings dialog
│   ├── dialog.py
│   ├── path_manager.py
│   └── tab_creators.py
└── Widgets/              # Reusable widgets
    ├── report_list.py
    ├── markdown_viewer.py
    └── report_metadata.py

ClassicLib/TUI/
├── app.py                # Main TUI application
├── screens/              # Full-screen interfaces
│   ├── main_screen.py
│   ├── help_screen.py
│   └── settings_screen.py
├── widgets/              # TUI components
│   └── dialogs/
└── handlers/            # Business logic
    └── papyrus/
```

### Utilities
```
ClassicLib/Utils/
├── path_utils.py        # Path operations
├── string_utils.py      # String manipulation
├── file_utils.py        # File operations
├── logging_utils.py     # Logging utilities
├── version_utils.py     # Version handling
└── web_utils.py        # Web operations
```

### Message System
```
ClassicLib/MessageHandler/
├── handler.py          # Main handler class
├── enums.py           # MessageType, MessageTarget
├── models.py          # Message data model
├── cli_progress.py    # CLI progress bar
└── progress_context.py # Progress tracking
```

## Test Suite Organization
```
tests/
├── conftest.py           # Shared fixtures
├── test_data/           # Mock data & samples
├── async_tests/         # Async infrastructure tests
├── core/               # Core functionality tests
├── scanning/           # Scanner tests
├── game/              # Game operations tests
├── settings/          # Settings management tests
├── performance/       # Performance benchmarks
├── concurrency/       # Thread safety tests
├── backup/           # Backup operations tests
├── io/              # File I/O tests
├── mods/            # Mod detection tests
├── utils/           # Utility function tests
├── gui/             # GUI component tests
└── tui/             # TUI component tests
```

## Configuration & Data
```
CLASSIC Data/
├── Databases/
│   ├── FormIDs.db       # FormID lookup database
│   └── Mods.yaml        # Mod detection database
├── Settings/
│   └── CLASSIC_Settings.yaml  # Main configuration
└── Templates/           # Report templates
```

## Key Architectural Notes

1. **No files in test root** - All tests must be in subdirectories
2. **300-line test limit** - Test files must stay under 300 lines
3. **550-line code limit** - Source files must stay under 550 lines
4. **One class per file** - Modular organization pattern
5. **Async-first cores** - Core implementations are async
6. **Sync adapters** - Backward compatibility wrappers

## Import Paths
```python
# New modular imports (preferred)
from ClassicLib.MessageHandler.handler import MessageHandler
from ClassicLib.ScanLog.models.scan_config import ScanConfig

# Legacy imports (still work with deprecation)
from ClassicLib.MessageHandler import MessageHandler
from ClassicLib.ScanLog.models import ScanConfig
```

## Entry Point Flow
```
User → Entry Point → SetupCoordinator → Core Components
         ↓                                    ↓
    MessageHandler ← Output ← Orchestrator ← Analyzers
```
