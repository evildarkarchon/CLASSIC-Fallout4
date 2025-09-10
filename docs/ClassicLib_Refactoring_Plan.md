# ClassicLib Code Organization Refactoring Plan

## Executive Summary

This document outlines a comprehensive plan to bring the ClassicLib codebase into compliance with the project's code organization standards as defined in CLAUDE.md:
- **500-line soft limit** per file (consider refactoring)
- **550-line hard limit** per file (must refactor)
- **One primary class per file** (with exceptions for small, tightly related helper classes)

## Current State Analysis

### Critical Violations (Files > 550 lines)

| File | Lines | Classes | Priority |
|------|-------|---------|----------|
| MessageHandler.py | 851 | 6 | CRITICAL |
| ScanGame/ScanGameCore.py | 824 | 1 | CRITICAL |
| AsyncYamlSettingsCore.py | 585 | 1 | CRITICAL |
| Util.py | 572 | 0 (functions only) | CRITICAL |w
| FileIOCore.py | 551 | 1 | CRITICAL |

### High Priority Violations (Files > 500 lines)

| File | Lines | Classes | Priority |
|------|-------|---------|----------|
| Interface/SettingsDialog.py | 534 | 1 | HIGH |
| Interface/ResultsViewerWidgets.py | 506 | 3 | HIGH |

### Multiple Class Violations

| File | Classes | Primary Issue |
|------|---------|---------------|
| MessageHandler.py | 6 | MessageType, MessageTarget, Message, CLIProgressBar, ProgressContext, MessageHandler |
| AsyncCore/error_handler.py | 5 | Multiple error and handler classes |
| ScanLog/ReportFragment.py | 4 | Multiple report fragment types |
| AsyncCore/sync_adapter.py | 4 | Multiple adapter classes |
| AsyncCore/resource_manager.py | 4 | Multiple resource management classes |
| AsyncCore/base.py | 4 | Multiple base classes |
| Interface/ResultsViewerWidgets.py | 3 | ReportListWidget, MarkdownViewer, ReportMetadataWidget |
| TUI/widgets/confirmation_dialog.py | 3 | Multiple dialog types |
| ScanLog/models.py | 3 | Multiple data models |
| Interface/Workers.py | 3 | Multiple worker classes |
| Interface/ThreadManager.py | 3 | Multiple thread management classes |

## Refactoring Strategy

### Phase 1: Critical File Size Violations (Week 1)

#### 1.1 MessageHandler.py (851 lines, 6 classes)
**Refactor into:**
- `MessageHandler/enums.py` - MessageType, MessageTarget (~25 lines)
- `MessageHandler/models.py` - Message class (~20 lines)
- `MessageHandler/cli_progress.py` - CLIProgressBar class (~75 lines)
- `MessageHandler/progress_context.py` - ProgressContext class (~100 lines)
- `MessageHandler/handler.py` - MessageHandler class (~500 lines)
- `MessageHandler/__init__.py` - Re-export for backwards compatibility

**Benefits:**
- Clear separation of concerns
- Each file has a single responsibility
- Maintains API compatibility through __init__.py

#### 1.2 ScanGame/ScanGameCore.py (824 lines)
**Refactor into:**
- `ScanGame/core.py` - Core scanning logic (~400 lines)
- `ScanGame/validators.py` - Validation methods (~200 lines)
- `ScanGame/processors.py` - Processing methods (~224 lines)

#### 1.3 AsyncYamlSettingsCore.py (585 lines)
**Refactor into:**
- `AsyncYamlSettings/core.py` - Main async settings class (~350 lines)
- `AsyncYamlSettings/cache.py` - Caching logic (~150 lines)
- `AsyncYamlSettings/validators.py` - Validation logic (~85 lines)

#### 1.4 Util.py (572 lines, functions only)
**Refactor into:**
- `Utils/path_utils.py` - Path-related utilities (~150 lines)
- `Utils/string_utils.py` - String manipulation utilities (~100 lines)
- `Utils/file_utils.py` - File operation utilities (~150 lines)
- `Utils/game_utils.py` - Game-specific utilities (~172 lines)
- `Utils/__init__.py` - Re-export all functions

#### 1.5 FileIOCore.py (551 lines)
**Refactor into:**
- `FileIO/core.py` - Main FileIOCore class (~400 lines)
- `FileIO/encoding.py` - Encoding detection and handling (~151 lines)

### Phase 2: High Priority Violations (Week 2)

#### 2.1 Interface/SettingsDialog.py (534 lines)
**Refactor into:**
- `Interface/Settings/dialog.py` - Main dialog (~350 lines)
- `Interface/Settings/validators.py` - Input validators (~100 lines)
- `Interface/Settings/widgets.py` - Custom widgets (~84 lines)

#### 2.2 Interface/ResultsViewerWidgets.py (506 lines, 3 classes)
**Refactor into:**
- `Interface/Widgets/report_list.py` - ReportListWidget (~175 lines)
- `Interface/Widgets/markdown_viewer.py` - MarkdownViewer (~187 lines)
- `Interface/Widgets/report_metadata.py` - ReportMetadataWidget (~144 lines)

### Phase 3: Multiple Class Violations (Week 3)

#### 3.1 ScanLog Module
**Files with multiple classes:**
- ReportFragment.py (4 classes)
- models.py (3 classes)
- AsyncPipeline.py (2 classes)
- ScanLogInfo.py (2 classes)
- ReportComposition.py (2 classes)

**Refactor each to single-class files with descriptive names**

### Phase 4: Interface Module Cleanup (Week 4)

**Files needing separation:**
- Workers.py (3 classes) → Separate worker files
- ThreadManager.py (3 classes) → Separate manager files
- Papyrus.py (2 classes) → Split monitor and handler

### Phase 5: TUI Module Organization (Week 4)

**Files needing attention:**
- widgets/confirmation_dialog.py (3 classes) → Separate dialog types
- handlers/papyrus_handler.py (2 classes) → Split handler and helper

## Implementation Guidelines

### 1. Maintain Backwards Compatibility
- Use `__init__.py` files to re-export refactored components
- Add deprecation warnings for moved items
- Document new locations in docstrings

### 2. Testing Strategy
- Create tests for each refactored module before moving code
- Ensure all existing tests pass after refactoring
- Add integration tests to verify compatibility

### 3. Migration Path
```python
# Example __init__.py for backwards compatibility
from .handler import MessageHandler
from .enums import MessageType, MessageTarget
from .models import Message
from .cli_progress import CLIProgressBar
from .progress_context import ProgressContext

# Deprecation warnings
import warnings

def __getattr__(name):
    if name in ['MessageHandler', 'MessageType', 'MessageTarget',
                'Message', 'CLIProgressBar', 'ProgressContext']:
        warnings.warn(
            f"Importing {name} from MessageHandler is deprecated. "
            f"Import from MessageHandler.{name.lower()} instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['MessageHandler', 'MessageType', 'MessageTarget',
           'Message', 'CLIProgressBar', 'ProgressContext']
```

### 4. Documentation Updates
- Update all imports in documentation
- Create migration guide for external users
- Update CLAUDE.md with new structure

## Success Metrics

### Compliance Targets
- **100%** of files under 550 lines
- **95%** of files under 500 lines
- **100%** compliance with one-class-per-file rule (with documented exceptions)

### Code Quality Improvements
- Improved module cohesion
- Reduced coupling between components
- Better testability
- Clearer code navigation

## Risk Mitigation

### Potential Risks
1. **Breaking existing code** - Mitigated by compatibility layer
2. **Import path changes** - Mitigated by __init__.py re-exports
3. **Test failures** - Mitigated by incremental refactoring
4. **Performance impacts** - Mitigated by profiling critical paths

### Rollback Strategy
- Each phase is independently revertible
- Git branches for each major refactoring
- Comprehensive test suite before merging

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | Phase 1 | Critical file size violations resolved |
| 2 | Phase 2 | High priority violations resolved |
| 3 | Phase 3 | Multiple class violations resolved |
| 4 | Phase 4-5 | Interface and TUI cleanup |

## Exceptions and Special Cases

### Acceptable Multi-Class Files
These files may contain multiple small, tightly related classes:
- Enum definitions with related data classes
- Exception hierarchies in a single module
- Small TypedDict definitions with their parent class

### Files Approaching Limits
Monitor these files for future refactoring needs:
- ScanLog/OrchestratorCore.py (495 lines)
- Interface/TabSetupMixin.py (487 lines)
- AsyncCore/resource_manager.py (480 lines)
- Interface/ResultsViewerMixin.py (479 lines)
- ScanGame/Config.py (472 lines)
- Update.py (469 lines)

## Conclusion

This refactoring plan will bring ClassicLib into full compliance with project standards while maintaining backwards compatibility and improving overall code quality. The phased approach allows for incremental improvements with minimal disruption to ongoing development.

## Appendix: File-by-File Refactoring Details

### Detailed Breakdown for MessageHandler.py

**Current Structure:**
```python
# Lines 1-138: Imports and setup
# Lines 139-150: MessageType enum (12 lines)
# Lines 151-160: MessageTarget enum (10 lines)
# Lines 161-171: Message class (11 lines)
# Lines 172-245: CLIProgressBar class (74 lines)
# Lines 246-340: ProgressContext class (95 lines)
# Lines 341-851: MessageHandler class (511 lines)
```

**Proposed Structure:**
- Each class becomes its own file
- MessageHandler class may need further splitting if still over 500 lines
- Consider extracting GUI-specific code to separate mixin

### Detailed Breakdown for ScanGameCore.py

**Analysis needed to identify logical boundaries:**
- Initialization and setup methods
- Validation methods
- Processing methods
- Output/reporting methods
- Utility methods

**Proposed extraction pattern:**
- Keep core orchestration in main file
- Extract validation to validators module
- Extract processing algorithms to processors module
- Extract utility functions to utils module

---

*This document should be reviewed and updated as refactoring progresses. Each phase completion should be documented with actual results and any deviations from the plan.*
