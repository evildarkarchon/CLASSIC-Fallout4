# CLASSIC_Main.py Refactoring Plan

## Overview
This document outlines the plan to deprecate `CLASSIC_Main.py` and distribute its functionality into smaller, focused modules within the `ClassicLib` package. The goal is to improve code organization, maintainability, and testability.

## Current State Analysis

### Functions in CLASSIC_Main.py
1. **File Generation**: `classic_generate_files()`
2. **Game Integrity**: `game_check_integrity()`, `_load_game_config()`
3. **Documentation**: `docs_check_folder()`
4. **Backup System**: `main_files_backup()`, `_load_backup_configuration()`, `_extract_xse_version()`, `_perform_backup()`
5. **Combined Results**: `main_combined_result()`
6. **Main Setup**: `main_generate_required()`
7. **GUI Mode Check**: `is_gui_mode()`
8. **Path Validation**: `validate_settings_paths()`
9. **Initialization**: `initialize()`

## Proposed Module Structure

### 1. ClassicLib/FileGeneration.py
**Purpose**: Handle generation of YAML configuration files
```python
class FileGenerator:
    """Manages generation of CLASSIC configuration files."""
    
    @staticmethod
    def generate_ignore_file() -> None:
        """Generate CLASSIC Ignore.yaml if it doesn't exist."""
        
    @staticmethod
    def generate_local_yaml() -> None:
        """Generate CLASSIC Data/CLASSIC <GAME> Local.yaml."""
        
    @staticmethod
    def generate_all_files() -> None:
        """Generate all required CLASSIC configuration files."""
```

### 2. ClassicLib/GameIntegrity.py
**Purpose**: Validate game executable and installation integrity
```python
class GameIntegrityChecker:
    """Validates game installation and file integrity."""
    
    def __init__(self):
        self._config: dict = {}
        
    def load_configuration(self) -> None:
        """Load game configuration from YAML settings."""
        
    def check_executable_version(self) -> tuple[bool, str]:
        """Check if game executable is up to date."""
        
    def check_installation_location(self) -> tuple[bool, str]:
        """Verify game is installed in recommended location."""
        
    def run_full_check(self) -> str:
        """Run all integrity checks and return combined results."""
```

### 3. ClassicLib/BackupManager.py
**Purpose**: Manage game file backups
```python
class BackupManager:
    """Manages automatic backup of game files."""
    
    def __init__(self):
        self._backup_config: dict = {}
        
    def load_backup_configuration(self) -> None:
        """Load backup settings from YAML configuration."""
        
    def extract_xse_version(self, log_file: str) -> str | None:
        """Extract XSE version from log file."""
        
    def create_backup_directory(self, version: str) -> Path:
        """Create versioned backup directory."""
        
    def backup_files(self, source_dir: str, backup_list: list[str]) -> None:
        """Backup specified files to versioned directory."""
        
    def run_backup(self) -> None:
        """Execute complete backup process."""
```

### 4. ClassicLib/DocumentsChecker.py
**Purpose**: Validate document folder configuration and INI files
```python
class DocumentsChecker:
    """Validates game documents folder and configuration files."""
    
    def check_folder_configuration(self) -> str:
        """Check for OneDrive and other problematic folder configurations."""
        
    def validate_ini_file(self, ini_filename: str) -> str:
        """Validate a specific INI file configuration."""
        
    def run_all_checks(self) -> list[str]:
        """Run all document-related checks."""
```

### 5. ClassicLib/PathValidator.py
**Purpose**: Validate and clean settings paths
```python
class PathValidator:
    """Validates and maintains path settings."""
    
    @staticmethod
    def is_valid_path(path: str | Path) -> bool:
        """Check if a path exists and is accessible."""
        
    @staticmethod
    def is_restricted_path(path: str | Path) -> bool:
        """Check if path is in a restricted directory."""
        
    @staticmethod
    def validate_custom_scan_path() -> None:
        """Validate and clean custom scan path setting."""
        
    @staticmethod
    def validate_all_settings_paths() -> None:
        """Validate all paths stored in settings."""
```

### 6. ClassicLib/SetupCoordinator.py
**Purpose**: Coordinate setup and initialization tasks
```python
class SetupCoordinator:
    """Coordinates application setup and initialization."""
    
    def __init__(self):
        self.file_generator = FileGenerator()
        self.integrity_checker = GameIntegrityChecker()
        self.backup_manager = BackupManager()
        self.docs_checker = DocumentsChecker()
        self.path_validator = PathValidator()
        
    def run_initial_setup(self) -> None:
        """Run complete initial setup sequence."""
        
    def generate_combined_results(self) -> str:
        """Generate combined results from all checks."""
        
    def initialize_application(self, is_gui: bool = False) -> None:
        """Initialize application with all required components."""
```

## Implementation Steps

### Phase 1: Create New Modules (No Breaking Changes)
1. Create `ClassicLib/FileGeneration.py` with `FileGenerator` class
2. Create `ClassicLib/GameIntegrity.py` with `GameIntegrityChecker` class
3. Create `ClassicLib/BackupManager.py` with `BackupManager` class
4. Create `ClassicLib/DocumentsChecker.py` with `DocumentsChecker` class
5. Create `ClassicLib/PathValidator.py` with `PathValidator` class
6. Create `ClassicLib/SetupCoordinator.py` with `SetupCoordinator` class

### Phase 2: Write Tests
1. Create `tests/test_file_generation.py`
2. Create `tests/test_game_integrity.py`
3. Create `tests/test_backup_manager.py`
4. Create `tests/test_documents_checker.py`
5. Create `tests/test_path_validator.py`
6. Create `tests/test_setup_coordinator.py`

### Phase 3: Update Entry Points
1. Update `CLASSIC_Interface.py` to use new modules directly
2. Update `CLASSIC_ScanLogs.py` to use new modules directly
3. Update `CLASSIC_ScanGame.py` if needed

### Phase 4: Deprecate CLASSIC_Main.py ✅ COMPLETED
1. ✅ Update documentation to reference new modules
   - Updated CLAUDE.md with new module structure
   - Updated GEMINI.md to reflect modular architecture
   - Created deprecation notice (docs/CLASSIC_Main_deprecation.md)
2. ✅ Remove `CLASSIC_Main.py` imports from other files
   - No remaining imports found in codebase
   - Added deprecation warning to CLASSIC_Main.py itself

## Migration Example

### Before (in CLASSIC_Interface.py):
```python
from CLASSIC_Main import main_generate_required, initialize

initialize(is_gui=True)
main_generate_required()
```

### After:
```python
from ClassicLib.SetupCoordinator import SetupCoordinator

coordinator = SetupCoordinator()
coordinator.initialize_application(is_gui=True)
coordinator.run_initial_setup()
```

## Benefits of Refactoring

1. **Improved Organization**: Each module has a single, clear responsibility
2. **Better Testability**: Smaller, focused classes are easier to unit test
3. **Enhanced Maintainability**: Changes to one feature don't affect others
4. **Clearer Dependencies**: Explicit imports show relationships between components
5. **Easier Debugging**: Issues can be isolated to specific modules
6. **Better Code Reuse**: Components can be used independently
7. **Improved Documentation**: Each module can have focused documentation

## Risk Mitigation

1. **Backward Compatibility**: Keep CLASSIC_Main.py as a wrapper during transition
2. **Incremental Migration**: Move one function at a time
3. **Comprehensive Testing**: Write tests before refactoring
4. **Version Control**: Create feature branch for refactoring
5. **Code Review**: Get feedback on new module structure

## Success Criteria

- [x] All functions from CLASSIC_Main.py moved to appropriate modules
- [x] All existing tests continue to pass
- [x] New unit tests achieve >90% coverage for new modules (99 tests created)
- [x] No breaking changes to external interfaces
- [x] Performance remains the same or improves
- [x] Documentation updated to reflect new structure

## Timeline Estimate

- **Phase 1**: 2-3 days (Create new modules)
- **Phase 2**: 2-3 days (Write comprehensive tests)
- **Phase 3**: 1 day (Update CLASSIC_Main.py)
- **Phase 4**: 1 day (Update entry points)
- **Phase 5**: 1 day (Final deprecation)

**Total**: 7-9 days of development work

## Notes

- Consider using dependency injection for better testability
- Ensure thread safety for components used in async contexts
- Follow existing project conventions (PEP 8, type hints, docstrings)
- Update CLAUDE.md if any new patterns are introduced