# Multi-Game Support Implementation Plan for CLASSIC

## Phase 1: Architecture Refactoring

### 1.1 Game Definition System

Create a new game enumeration and registry system to replace the current string-based approach:

```python
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Literal
from pathlib import Path


class SupportedGame(Enum):
    """Enumeration of all supported games."""
    FALLOUT4 = auto()
    FALLOUT4_VR = auto()
    SKYRIM_SE = auto()
    SKYRIM_VR = auto()  # Future support
    STARFIELD = auto()  # Future support


@dataclass
class GameDefinition:
    """Complete definition of a supported game."""
    game_id: SupportedGame
    display_name: str
    short_name: str
    steam_id: int
    exe_name: str
    xse_acronym: str
    xse_full_name: str
    crashgen_acronym: str
    crashgen_name: str
    registry_keys: list[str]
    ini_files: list[str]
    yaml_config_file: str
    is_vr: bool = False
    parent_game: Optional[SupportedGame] = None  # For VR variants
```

### 1.2 Refactor GlobalRegistry

Update the GlobalRegistry to use the new game system:

```python
class GlobalRegistry:
    class Keys(Enum):
        CURRENT_GAME: str = "current_game"  # SupportedGame enum value
        GAME_DEFINITION: str = "game_definition"  # GameDefinition instance
        # Remove VR key - no longer needed

    @classmethod
    def get_current_game(cls) -> Optional[SupportedGame]:
        """Get the currently selected game."""
        return cls.get(cls.Keys.CURRENT_GAME)

    @classmethod
    def get_game_definition(cls) -> Optional[GameDefinition]:
        """Get the complete definition of the current game."""
        return cls.get(cls.Keys.GAME_DEFINITION)

    @classmethod
    def is_vr_game(cls) -> bool:
        """Check if the current game is a VR variant."""
        game_def = cls.get_game_definition()
        return game_def.is_vr if game_def else False
```

## Phase 2: Game Manager Implementation

### 2.1 Create GameManager Class

```python
from typing import Dict, Optional
from ruamel.yaml import YAML
from pathlib import Path


class GameManager:
    """Centralized manager for all game-specific operations."""

    _game_definitions: Dict[SupportedGame, GameDefinition] = {}
    _current_game: Optional[SupportedGame] = None

    @classmethod
    def initialize(cls) -> None:
        """Initialize all game definitions."""
        cls._register_fallout4()
        cls._register_fallout4_vr()
        cls._register_skyrim_se()
        # Load user's selected game from settings
        cls._load_selected_game()

    @classmethod
    def _register_fallout4(cls) -> None:
        """Register Fallout 4 base game."""
        cls._game_definitions[SupportedGame.FALLOUT4] = GameDefinition(
            game_id=SupportedGame.FALLOUT4,
            display_name="Fallout 4",
            short_name="FO4",
            steam_id=377160,
            exe_name="Fallout4.exe",
            xse_acronym="F4SE",
            xse_full_name="Fallout 4 Script Extender",
            crashgen_acronym="BO4",
            crashgen_name="Buffout 4",
            registry_keys=[
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Bethesda Softworks\Fallout4",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4"
            ],
            ini_files=["Fallout4.ini", "Fallout4Prefs.ini", "Fallout4Custom.ini"],
            yaml_config_file="CLASSIC Fallout4.yaml",
            is_vr=False
        )

    @classmethod
    def _register_fallout4_vr(cls) -> None:
        """Register Fallout 4 VR as separate game."""
        cls._game_definitions[SupportedGame.FALLOUT4_VR] = GameDefinition(
            game_id=SupportedGame.FALLOUT4_VR,
            display_name="Fallout 4 VR",
            short_name="FO4VR",
            steam_id=611660,
            exe_name="Fallout4VR.exe",
            xse_acronym="F4SEVR",
            xse_full_name="Fallout 4 Script Extender VR",
            crashgen_acronym="BO4VR",
            crashgen_name="Buffout 4 VR",
            registry_keys=[
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Bethesda Softworks\Fallout4VR",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4VR"
            ],
            ini_files=["Fallout4VR.ini", "Fallout4VRPrefs.ini", "Fallout4VRCustom.ini"],
            yaml_config_file="CLASSIC Fallout4VR.yaml",
            is_vr=True,
            parent_game=SupportedGame.FALLOUT4
        )

    @classmethod
    def _register_skyrim_se(cls) -> None:
        """Register Skyrim Special Edition."""
        cls._game_definitions[SupportedGame.SKYRIM_SE] = GameDefinition(
            game_id=SupportedGame.SKYRIM_SE,
            display_name="Skyrim Special Edition",
            short_name="SSE",
            steam_id=489830,
            exe_name="SkyrimSE.exe",
            xse_acronym="SKSE",
            xse_full_name="Skyrim Script Extender",
            crashgen_acronym="CSE",
            crashgen_name="Crash Logger SSE",
            registry_keys=[
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Bethesda Softworks\Skyrim Special Edition",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition"
            ],
            ini_files=["Skyrim.ini", "SkyrimPrefs.ini", "SkyrimCustom.ini"],
            yaml_config_file="CLASSIC SkyrimSE.yaml",
            is_vr=False
        )

    @classmethod
    def switch_game(cls, game: SupportedGame) -> bool:
        """Switch to a different game."""
        if game not in cls._game_definitions:
            return False

        cls._current_game = game
        game_def = cls._game_definitions[game]

        # Update GlobalRegistry
        GlobalRegistry.register(GlobalRegistry.Keys.CURRENT_GAME, game)
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_DEFINITION, game_def)

        # Save to settings
        cls._save_selected_game(game)

        # Reload game-specific configurations
        cls._load_game_config(game_def)

        return True
```

## Phase 3: Configuration Migration

### 3.1 Updated YamlSettingsCache Integration

Extend the existing YamlSettingsCache to support multi-game configurations:

```python
from ruamel.yaml import YAML
from pathlib import Path
from typing import Optional, Any, Dict
from enum import Enum


class YAML(Enum):
    """Extended YAML store enumeration for multi-game support."""
    Settings = "settings"
    Main = "main"
    Fallout4 = "fallout4"
    Fallout4VR = "fallout4vr"
    SkyrimSE = "skyrimse"

    @classmethod
    def for_game(cls, game: SupportedGame) -> 'YAML':
        """Get the YAML store for a specific game."""
        game_yaml_map = {
            SupportedGame.FALLOUT4: cls.Fallout4,
            SupportedGame.FALLOUT4_VR: cls.Fallout4VR,
            SupportedGame.SKYRIM_SE: cls.SkyrimSE,
        }
        return game_yaml_map.get(game, cls.Fallout4)


class YamlSettingsCache:
    """Extended cache with multi-game support."""

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """Get the path for a given YAML store."""
        if yaml_store in self.path_cache:
            return self.path_cache[yaml_store]

        path_map = {
            YAML.Settings: Path("CLASSIC Settings.yaml"),
            YAML.Main: Path("CLASSIC Data/databases/CLASSIC Main.yaml"),
            YAML.Fallout4: Path("CLASSIC Data/databases/CLASSIC Fallout4.yaml"),
            YAML.Fallout4VR: Path("CLASSIC Data/databases/CLASSIC Fallout4VR.yaml"),
            YAML.SkyrimSE: Path("CLASSIC Data/databases/CLASSIC SkyrimSE.yaml"),
        }

        path = path_map.get(yaml_store, Path("CLASSIC Settings.yaml"))
        self.path_cache[yaml_store] = path
        return path

    def load_yaml_with_comments(self, file_path: Path) -> Any:
        """Load YAML while preserving comments and formatting."""
        if not file_path.exists():
            return {}

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.width = 4096  # Prevent line wrapping
        yaml.indent(mapping=2, sequence=4, offset=2)

        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.load(file)

    def save_yaml_with_comments(self, file_path: Path, data: Any) -> None:
        """Save YAML while preserving comments and formatting."""
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.width = 4096
        yaml.indent(mapping=2, sequence=4, offset=2)

        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file)
```

### 3.2 YAML Configuration Structure

Create separate YAML files for each game:

**CLASSIC Fallout4VR.yaml** (new file):

```yaml
GameVR_Info:
  Main_Root_Name: Fallout 4 VR
  Main_Docs_Name: Fallout4VR
  Main_SteamID: 611660
  EXE_HashedOLD: 00000
  EXE_HashedNEW: 00000

  CRASHGEN_Acronym: BO4VR
  CRASHGEN_LogName: Buffout 4 VR
  CRASHGEN_DLL_File: buffout4vr.dll
  CRASHGEN_LatestVer: Buffout 4 VR v1.0.0

  XSE_Acronym: F4SEVR
  XSE_FullName: Fallout 4 Script Extender VR
  XSE_Ver_Latest: 0.6.20

  Game_Plugins_Path: Data
  Game_INI_Files:
    - Fallout4VR.ini
    - Fallout4VRPrefs.ini
    - Fallout4VRCustom.ini

# VR-specific crash patterns and checks can go here
```

**CLASSIC SkyrimSE.yaml** (new file):

```yaml
Game_Info:
  Main_Root_Name: Skyrim Special Edition
  Main_Docs_Name: Skyrim Special Edition
  Main_SteamID: 489830

  CRASHGEN_Acronym: CSE
  CRASHGEN_LogName: Crash Logger SSE
  CRASHGEN_DLL_File: CrashLoggerSSE.dll
  CRASHGEN_LatestVer: Crash Logger SSE v1.14.1

  XSE_Acronym: SKSE
  XSE_FullName: Skyrim Script Extender
  XSE_Ver_Latest: 2.2.6

  Game_Plugins_Path: Data
  Game_INI_Files:
    - Skyrim.ini
    - SkyrimPrefs.ini
    - SkyrimCustom.ini

Crashlog_Error_Check:
  "HIGH | Access Violation": "EXCEPTION_ACCESS_VIOLATION"
  "HIGH | Stack Overflow": "EXCEPTION_STACK_OVERFLOW"
  # Skyrim-specific patterns...

Crashlog_Stack_Check:
  "HIGH | FormID Issue":
    - "required:FormID"
    - "optional:TESObjectREFR"
  # Skyrim-specific patterns...
```

### 3.2 Update Settings Structure

Modify the main settings YAML:

```yaml
CLASSIC_Settings:
  # CHANGED: Now stores the SupportedGame enum value
  Managed Game: FALLOUT4  # Options: FALLOUT4 | FALLOUT4_VR | SKYRIM_SE

  # REMOVED: VR Mode no longer needed
  # VR Mode: false

  Update Check: true
  FCX Mode: true
  # ... rest of settings remain the same
```

## Phase 4: Code Refactoring

### 4.1 Update GamePath Module

```python
from ClassicLib.YamlSettingsCache import yaml_settings, YamlSettingsCache


def game_path_find() -> Optional[Path]:
    """Find the game installation path for the current game."""
    game_def = GlobalRegistry.get_game_definition()
    if not game_def:
        return None

    # Get the appropriate YAML store for this game
    yaml_store = YAML.for_game(game_def.game_id)

    # Try registry keys for this specific game
    for reg_key in game_def.registry_keys:
        path = _game_path_find_registry(reg_key)
        if path:
            return path

    # Try Steam
    return _game_path_find_steam(game_def.steam_id)


def game_generate_paths() -> None:
    """Generate all paths for the current game."""
    game_def = GlobalRegistry.get_game_definition()
    if not game_def:
        return

    # Get the appropriate YAML store for this game
    yaml_store = YAML.for_game(game_def.game_id)

    # Read root path from game-specific YAML
    root_path = yaml_settings(str, yaml_store, "Root_Folder_Game")

    # Generate paths based on game definition
    data_path = Path(root_path) / "Data"
    exe_path = Path(root_path) / game_def.exe_name

    # Store in game-specific YAML
    yaml_settings(str, yaml_store, "Game_Folder_Data", str(data_path))
    yaml_settings(str, yaml_store, "Game_File_EXE", str(exe_path))

    # Handle VR-specific paths if needed
    if game_def.is_vr:
        address_lib_path = Path(root_path) / "Data" / f"F4SE\\Plugins\\{game_def.short_name}_AddressLibrary.bin"
        yaml_settings(str, yaml_store, "Game_File_AddressLib", str(address_lib_path))
```

### 4.2 Update UI Components (PySide6)

```python
from PySide6.QtWidgets import QComboBox, QLabel, QHBoxLayout
from typing import Optional


class GameSelectorWidget(QWidget):
    """Widget for selecting the current game."""

    game_changed = Signal(SupportedGame)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._load_games()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)

        label = QLabel("Select Game:")
        self.game_combo = QComboBox()

        layout.addWidget(label)
        layout.addWidget(self.game_combo)

        self.game_combo.currentIndexChanged.connect(self._on_game_changed)

    def _load_games(self) -> None:
        """Load all available games into the combo box."""
        for game in SupportedGame:
            game_def = GameManager.get_definition(game)
            if game_def:
                self.game_combo.addItem(game_def.display_name, game)

        # Set current game
        current_game = GlobalRegistry.get_current_game()
        if current_game:
            index = self.game_combo.findData(current_game)
            self.game_combo.setCurrentIndex(index)

    def _on_game_changed(self, index: int) -> None:
        """Handle game selection change."""
        game = self.game_combo.itemData(index)
        if game and GameManager.switch_game(game):
            self.game_changed.emit(game)
```

## Phase 5: Testing Strategy

### 5.1 Unit Tests

```python
def test_game_manager_initialization() -> None:
    """Test that all games are properly registered."""
    GameManager.initialize()

    assert GameManager.get_definition(SupportedGame.FALLOUT4) is not None
    assert GameManager.get_definition(SupportedGame.FALLOUT4_VR) is not None
    assert GameManager.get_definition(SupportedGame.SKYRIM_SE) is not None


def test_game_switching() -> None:
    """Test switching between games."""
    GameManager.initialize()

    # Switch to Fallout 4 VR
    success = GameManager.switch_game(SupportedGame.FALLOUT4_VR)
    assert success
    assert GlobalRegistry.get_current_game() == SupportedGame.FALLOUT4_VR
    assert GlobalRegistry.is_vr_game() is True

    # Switch to Skyrim SE
    success = GameManager.switch_game(SupportedGame.SKYRIM_SE)
    assert success
    assert GlobalRegistry.get_current_game() == SupportedGame.SKYRIM_SE
    assert GlobalRegistry.is_vr_game() is False
```

## Phase 6: Migration Path

### 6.1 Settings Migration with ruamel.yaml

Create a migration script that preserves comments and formatting:

```python
from ruamel.yaml import YAML
from pathlib import Path
from typing import Any


def migrate_settings_v7_to_v8() -> None:
    """Migrate from v7 (VR Mode) to v8 (separate games) preserving YAML formatting."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)

    settings_path = Path("CLASSIC Settings.yaml")

    # Load existing settings with comments preserved
    with open(settings_path, 'r', encoding='utf-8') as file:
        settings_data = yaml.load(file)

    # Get old values
    old_game = settings_data.get('CLASSIC_Settings', {}).get('Managed Game', 'Fallout 4')
    old_vr_mode = settings_data.get('CLASSIC_Settings', {}).get('VR Mode', False)

    # Determine new game selection
    if old_game == "Fallout 4" and old_vr_mode:
        new_game = "FALLOUT4_VR"
    elif old_game == "Fallout 4":
        new_game = "FALLOUT4"
    elif old_game == "Skyrim SE":
        new_game = "SKYRIM_SE"
    else:
        new_game = "FALLOUT4"  # Default

    # Update settings structure
    settings_data['CLASSIC_Settings']['Managed Game'] = new_game

    # Remove VR Mode key while preserving other settings
    if 'VR Mode' in settings_data['CLASSIC_Settings']:
        del settings_data['CLASSIC_Settings']['VR Mode']

    # Add comment about the change
    from ruamel.yaml.comments import CommentedMap
    if isinstance(settings_data['CLASSIC_Settings'], CommentedMap):
        settings_data['CLASSIC_Settings'].yaml_set_comment_before_after_key(
            'Managed Game',
            before='Now uses separate game entries instead of VR Mode flag'
        )

    # Save with formatting preserved
    with open(settings_path, 'w', encoding='utf-8') as file:
        yaml.dump(settings_data, file)

    # Migrate game-specific settings if needed
    if old_vr_mode and old_game == "Fallout 4":
        migrate_fallout4_to_vr_settings()


def migrate_fallout4_to_vr_settings() -> None:
    """Copy Fallout 4 settings to new Fallout 4 VR configuration."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    fo4_path = Path("CLASSIC Data/databases/CLASSIC Fallout4.yaml")
    fo4vr_path = Path("CLASSIC Data/databases/CLASSIC Fallout4VR.yaml")

    if fo4_path.exists() and not fo4vr_path.exists():
        with open(fo4_path, 'r', encoding='utf-8') as file:
            fo4_data = yaml.load(file)

        # Transform data for VR version
        if 'GameVR_Info' in fo4_data:
            # Move VR info to main section
            vr_info = fo4_data.pop('GameVR_Info')
            fo4_data['Game_Info'] = vr_info

        # Update specific VR values
        if 'Game_Info' in fo4_data:
            fo4_data['Game_Info']['Main_Root_Name'] = 'Fallout 4 VR'
            fo4_data['Game_Info']['Main_Docs_Name'] = 'Fallout4VR'
            fo4_data['Game_Info']['Main_SteamID'] = 611660
            fo4_data['Game_Info']['XSE_Acronym'] = 'F4SEVR'
            fo4_data['Game_Info']['CRASHGEN_Acronym'] = 'BO4VR'

        # Save as new VR configuration
        with open(fo4vr_path, 'w', encoding='utf-8') as file:
            yaml.dump(fo4_data, file)
```

### 6.2 Backward Compatibility Layer

Provide a compatibility layer for old code:

```python
class BackwardCompatibility:
    """Compatibility layer for code still using old VR Mode system."""

    @staticmethod
    def get_vr_mode() -> bool:
        """Get VR mode status for backward compatibility."""
        game_def = GlobalRegistry.get_game_definition()
        return game_def.is_vr if game_def else False

    @staticmethod
    def set_vr_mode(enabled: bool) -> None:
        """Set VR mode for backward compatibility."""
        current_game = GlobalRegistry.get_current_game()

        if current_game == SupportedGame.FALLOUT4 and enabled:
            # Switch to Fallout 4 VR
            GameManager.switch_game(SupportedGame.FALLOUT4_VR)
        elif current_game == SupportedGame.FALLOUT4_VR and not enabled:
            # Switch to base Fallout 4
            GameManager.switch_game(SupportedGame.FALLOUT4)
        # Other games ignore VR mode setting


# Monkey-patch GlobalRegistry for compatibility
GlobalRegistry.get_vr = BackwardCompatibility.get_vr_mode
```

## Phase 7: Async Support Integration

### 7.1 Game-Specific Async Scanning

Integrate multi-game support with existing async scanning infrastructure:

```python
from typing import Optional, Callable, Awaitable
import asyncio


class AsyncGameScanner:
    """Async scanner with multi-game support."""

    # Game-specific scan configurations
    _scan_configs: Dict[SupportedGame, Dict[str, Any]] = {
        SupportedGame.FALLOUT4: {
            'crashlog_pattern': 'Buffout 4 crash*.log',
            'xse_log': 'f4se.log',
            'enable_fcx': True,
        },
        SupportedGame.FALLOUT4_VR: {
            'crashlog_pattern': 'Buffout 4 crash*.log',
            'xse_log': 'f4sevr.log',
            'enable_fcx': True,
        },
        SupportedGame.SKYRIM_SE: {
            'crashlog_pattern': 'Crash*.log',
            'xse_log': 'skse64.log',
            'enable_fcx': False,  # FCX not applicable for Skyrim
        }
    }

    @classmethod
    async def scan_game_async(cls) -> Dict[str, Any]:
        """Perform async scanning for current game."""
        game = GlobalRegistry.get_current_game()
        if not game:
            return {"error": "No game selected"}

        config = cls._scan_configs.get(game, {})

        # Run game-specific scans in parallel
        tasks = []

        if config.get('enable_fcx'):
            tasks.append(cls._scan_fcx_async(game))

        tasks.append(cls._scan_crashlogs_async(game, config['crashlog_pattern']))
        tasks.append(cls._scan_xse_async(game, config['xse_log']))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            'game': game.name,
            'fcx_results': results[0] if config.get('enable_fcx') else None,
            'crashlog_results': results[-2],
            'xse_results': results[-1],
        }

    @staticmethod
    async def _scan_fcx_async(game: SupportedGame) -> Dict[str, Any]:
        """FCX scanning specific to game."""
        # Implementation specific to each game's file structure
        pass
```

### 7.2 Update Existing Async Wrappers

Update the existing async wrappers to be game-aware:

```python
def check_log_errors_async_wrapper(folder_path: Path | str) -> str:
    """Async log error checking with game context."""
    game_def = GlobalRegistry.get_game_definition()
    if not game_def:
        return "No game selected"

    # Use game-specific error patterns
    yaml_store = YAML.for_game(game_def.game_id)
    error_patterns = yaml_settings(dict, yaml_store, "Crashlog_Error_Check")

    # Run async scan with game context
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        _check_log_errors_async(folder_path, error_patterns, game_def)
    )
```

## Phase 8: Testing & Documentation

## Implementation Order

1. **Week 1**: Implement GameDefinition and SupportedGame enum
2. **Week 2**: Create GameManager and refactor GlobalRegistry
3. **Week 3**: Extend YamlSettingsCache for multi-game support
4. **Week 4**: Create new YAML configuration files with ruamel.yaml
5. **Week 5**: Update GamePath module and async integration
6. **Week 6**: Implement UI components for game selection
7. **Week 7**: Create migration scripts with comment preservation
8. **Week 8**: Testing, documentation and release preparation

## Key ruamel.yaml Integration Points

The implementation properly uses **ruamel.yaml** throughout:

1. **Comment Preservation**: All YAML operations preserve comments and formatting
2. **Round-trip Editing**: Settings can be modified without losing structure
3. **YamlSettingsCache Integration**: Extends existing cache for multi-game support
4. **Type Safety**: Proper type hints with Python 3.12+ style annotations
5. **Async Compatibility**: Works with existing async scanning infrastructure

### Example Usage with ruamel.yaml:

```python
from ruamel.yaml import YAML
from ClassicLib.YamlSettingsCache import yaml_settings, YAML as YAMLStore

# Reading game-specific settings
current_game = GlobalRegistry.get_current_game()
yaml_store = YAMLStore.for_game(current_game)
crashgen_name = yaml_settings(str, yaml_store, "Game_Info.CRASHGEN_LogName")

# Writing settings while preserving comments
yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 4096

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.load(f)

config['Game_Info']['XSE_Ver_Latest'] = '0.6.21'

with open(config_path, 'w', encoding='utf-8') as f:
    yaml.dump(config, f)
```