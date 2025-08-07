# Multi-Game & Multi-Version Support Implementation Plan

## Overview

Transform the crash log analyzer from a single-game, single-version tool into a flexible multi-game, multi-version
platform while maintaining backwards compatibility and improving code organization.

## Phase 1: Core Architecture Refactoring

### 1.1 Game Configuration System

```python
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


class GameType(Enum):
    FALLOUT4 = auto()
    SKYRIM_SE = auto()
    SKYRIM_VR = auto()
    FALLOUT4_VR = auto()


@dataclass
class GameVersion:
    """Represents a specific version of a game"""
    version_string: str  # e.g., "1.10.163.0"
    display_name: str  # e.g., "Fallout 4 v1.10.163 (Current)"
    is_current: bool = False
    is_legacy: bool = False
    parent_game: GameType | None = None  # For VR versions

@dataclass
class GameConfig:
    """Configuration for a specific game"""
    game_type: GameType
    display_name: str
    versions: list[GameVersion]
    executable_names: list[str]  # e.g., ["Fallout4.exe", "Fallout4VR.exe"]
    plugin_extensions: list[str]  # e.g., [".esm", ".esp", ".esl"]
    crash_log_patterns: list[str]  # Regex patterns to identify logs
    data_directory: Path
```

### 1.2 Abstract Base Classes

```python
from abc import ABC, abstractmethod
from typing import Any, Protocol


class CrashLogParser(ABC):
    """Abstract base parser for all game crash logs"""

    def __init__(self, game_config: GameConfig):
        self.game_config = game_config

    @abstractmethod
    def parse(self, log_content: str) -> dict[str, Any]:
        """Parse crash log content into structured data"""
        pass

    @abstractmethod
    def extract_version(self, log_content: str) -> str | None:
        """Extract game version from log"""
        pass

    @abstractmethod
    def validate_format(self, log_content: str) -> bool:
        """Check if log format is valid for this parser"""
        pass


class IssueDetector(ABC):
    """Abstract base for issue detection logic"""

    @abstractmethod
    def detect(self, parsed_data: dict[str, Any]) -> list[Issue]:
        """Detect issues from parsed crash data"""
        pass


class Issue(Protocol):
    """Protocol for issues across different games"""
    severity: str
    category: str
    description: str
    solution: str | None
```

## Phase 2: Data Structure Reorganization

### 2.1 Directory Structure

```
data/
├── games/
│   ├── fallout4/
│   │   ├── config.json
│   │   ├── versions/
│   │   │   ├── 1.10.163/
│   │   │   │   ├── issues.json
│   │   │   │   ├── patterns.json
│   │   │   │   └── offsets.json
│   │   │   └── 1.10.984/
│   │   │       └── ...
│   │   └── shared/
│   │       ├── common_issues.json
│   │       └── plugin_data.json
│   ├── fallout4_vr/
│   │   ├── config.json
│   │   └── versions/
│   │       └── 1.2.72/
│   │           └── ...
│   ├── skyrim_se/
│   │   ├── config.json
│   │   └── versions/
│   │       ├── 1.6.1179/
│   │       └── 1.5.97/
│   └── skyrim_vr/
│       └── ...
└── shared/
    ├── common_patterns.json
    └── hardware_issues.json
```

### 2.2 Configuration Schema

```python
from typing import TypedDict


class GameConfigSchema(TypedDict):
    """JSON schema for game configuration"""
    id: str
    display_name: str
    parent_game: str | None  # For VR versions
    versions: list[dict[str, Any]]
    executable_patterns: list[str]
    log_identifiers: dict[str, str]  # Patterns to identify game from log
    supported_features: list[str]  # e.g., ["stack_analysis", "plugin_sorting"]
```

## Phase 3: Parser Implementation

### 3.1 Fallout 4 Parser (Refactored)

```python
class Fallout4Parser(CrashLogParser):
    """Parser for Fallout 4 crash logs"""

    def parse(self, log_content: str) -> dict[str, Any]:
        result = {
            'game': self.game_config.game_type,
            'version': self.extract_version(log_content),
            'crash_address': None,
            'probable_callstack': [],
            'registers': {},
            'stack': [],
            'modules': [],
            'plugins': []
        }

        # Existing parsing logic, refactored
        # ...

        return result

    def extract_version(self, log_content: str) -> str | None:
        import re
        pattern = r'Fallout 4 v([\d.]+)'
        if match := re.search(pattern, log_content):
            return match.group(1)
        return None
```

### 3.2 Skyrim SE Parser

```python
class SkyrimSEParser(CrashLogParser):
    """Parser for Skyrim Special Edition crash logs"""

    def parse(self, log_content: str) -> dict[str, Any]:
        result = {
            'game': self.game_config.game_type,
            'version': self.extract_version(log_content),
            'crash_address': None,
            'probable_callstack': [],
            'registers': {},
            'stack': [],
            'modules': [],
            'plugins': []
        }

        # Parse Skyrim-specific format
        # Handle Light/Regular/Total plugin counts
        # Parse different FormID format

        return result

    def extract_version(self, log_content: str) -> str | None:
        import re
        pattern = r'Skyrim SSE v([\d.]+)'
        if match := re.search(pattern, log_content):
            return match.group(1)
        return None
```

## Phase 4: Game Manager

```python
class GameManager:
    """Manages game configurations and parser selection"""

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.games: dict[GameType, GameConfig] = {}
        self.parsers: dict[GameType, type[CrashLogParser]] = {}
        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load all game configurations from data files"""
        # Load from JSON files
        pass

    def register_parser(self, game_type: GameType,
                        parser_class: type[CrashLogParser]) -> None:
        """Register a parser for a game type"""
        self.parsers[game_type] = parser_class

    def detect_game(self, log_content: str) -> GameType | None:
        """Auto-detect game from log content"""
        for game_type, config in self.games.items():
            parser = self.parsers[game_type](config)
            if parser.validate_format(log_content):
                return game_type
        return None

    def get_parser(self, game_type: GameType) -> CrashLogParser:
        """Get appropriate parser for game type"""
        if game_type not in self.parsers:
            raise ValueError(f"No parser registered for {game_type}")
        return self.parsers[game_type](self.games[game_type])

    def get_available_games(self) -> list[tuple[GameType, str]]:
        """Get list of available games for UI"""
        return [(gt, gc.display_name)
                for gt, gc in self.games.items()]
```

## Phase 5: GUI Updates (PySide6)

### 5.1 Main Window Modifications

```python
from PySide6.QtWidgets import QComboBox, QLabel
from PySide6.QtCore import Signal


class GameSelector(QWidget):
    """Widget for game selection"""

    game_changed = Signal(GameType)

    def __init__(self, game_manager: GameManager):
        super().__init__()
        self.game_manager = game_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout()

        # Game dropdown
        self.game_label = QLabel("Game:")
        self.game_combo = QComboBox()

        for game_type, display_name in self.game_manager.get_available_games():
            self.game_combo.addItem(display_name, game_type)

        # Version info (auto-detected or manual)
        self.version_label = QLabel("Version:")
        self.version_combo = QComboBox()
        self.version_combo.setEditable(False)

        layout.addWidget(self.game_label)
        layout.addWidget(self.game_combo)
        layout.addWidget(self.version_label)
        layout.addWidget(self.version_combo)

        self.setLayout(layout)

        # Connect signals
        self.game_combo.currentIndexChanged.connect(self._on_game_changed)

    def _on_game_changed(self) -> None:
        """Handle game selection change"""
        game_type = self.game_combo.currentData()
        if game_type:
            self.game_changed.emit(game_type)
            self._update_versions(game_type)

    def _update_versions(self, game_type: GameType) -> None:
        """Update version dropdown for selected game"""
        self.version_combo.clear()
        config = self.game_manager.games[game_type]
        for version in config.versions:
            label = version.display_name
            if version.is_current:
                label += " (Current)"
            self.version_combo.addItem(label, version.version_string)
```

### 5.2 Main Application Updates

```python
class CrashLogAnalyzerApp(QMainWindow):
    """Updated main application with multi-game support"""

    def __init__(self):
        super().__init__()
        self.game_manager = GameManager(Path("data/games"))
        self.current_game: GameType | None = None
        self.current_parser: CrashLogParser | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Add game selector to toolbar
        self.game_selector = GameSelector(self.game_manager)
        self.game_selector.game_changed.connect(self._on_game_changed)

        # ... rest of UI setup

    def _on_game_changed(self, game_type: GameType) -> None:
        """Handle game change"""
        self.current_game = game_type
        self.current_parser = self.game_manager.get_parser(game_type)

        # Update UI elements based on game
        self._update_ui_for_game(game_type)

        # Clear current analysis if any
        self._clear_analysis()

    def analyze_log(self, log_path: Path) -> None:
        """Analyze crash log with auto-detection"""
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Auto-detect game if not selected
        if not self.current_game:
            detected_game = self.game_manager.detect_game(content)
            if detected_game:
                self.game_selector.set_game(detected_game)
            else:
                QMessageBox.warning(self, "Unknown Game",
                                    "Could not detect game from log file")
                return

        # Parse with appropriate parser
        parsed_data = self.current_parser.parse(content)

        # Detect issues
        issues = self._detect_issues(parsed_data)

        # Display results
        self._display_results(parsed_data, issues)
```

## Phase 6: Migration Strategy

### 6.1 Backwards Compatibility

```python
class LegacyDataMigrator:
    """Migrate existing data to new structure"""

    @staticmethod
    def migrate_fo4_data(old_path: Path, new_path: Path) -> None:
        """Migrate existing Fallout 4 data"""
        # Read old autoscan.txt and convert to new format
        # Split VR-specific data into separate files
        # Convert offset databases
        pass

    @staticmethod
    def create_game_configs() -> None:
        """Create initial game configuration files"""
        configs = {
            'fallout4': {
                'id': 'fallout4',
                'display_name': 'Fallout 4',
                'versions': [
                    {'version': '1.10.163.0', 'is_current': True},
                    {'version': '1.10.984.0', 'is_legacy': True}
                ],
                # ... more config
            },
            'skyrim_se': {
                'id': 'skyrim_se',
                'display_name': 'Skyrim Special Edition',
                'versions': [
                    {'version': '1.6.1179', 'is_current': True},
                    {'version': '1.5.97', 'is_legacy': True}
                ],
                # ... more config
            }
        }
        # Save to JSON files
```

## Phase 7: Testing Strategy

### 7.1 Unit Tests

```python
import pytest
from pathlib import Path


class TestGameManager:
    def test_game_detection(self, sample_logs: dict[str, str]):
        """Test automatic game detection"""
        manager = GameManager(Path("test_data"))

        assert manager.detect_game(sample_logs['fo4']) == GameType.FALLOUT4
        assert manager.detect_game(sample_logs['sse']) == GameType.SKYRIM_SE

    def test_parser_selection(self):
        """Test correct parser selection"""
        manager = GameManager(Path("test_data"))

        parser = manager.get_parser(GameType.SKYRIM_SE)
        assert isinstance(parser, SkyrimSEParser)


class TestParsers:
    def test_skyrim_plugin_parsing(self):
        """Test Skyrim's Light/Regular/Total plugin format"""
        parser = SkyrimSEParser(mock_config)
        result = parser.parse(SAMPLE_SSE_LOG)

        assert 'plugins' in result
        assert result['plugins']['light_count'] == 215
        assert result['plugins']['regular_count'] == 103
```

## Phase 8: Implementation Timeline

### Week 1-2: Core Architecture

- Implement GameConfig and GameManager classes
- Create abstract base classes
- Set up new directory structure

### Week 3-4: Parser Refactoring

- Refactor existing Fallout 4 parser
- Implement Skyrim SE parser
- Add game detection logic

### Week 5: GUI Updates

- Add game selector widget
- Update main window
- Implement dynamic UI updates

### Week 6: Data Migration

- Migrate existing FO4 data
- Create Skyrim SE data files
- Test backwards compatibility

### Week 7: Testing & Polish

- Comprehensive testing
- Bug fixes
- Documentation updates

## Key Benefits

1. **Modularity**: Each game has its own parser and configuration
2. **Extensibility**: Easy to add new games or versions
3. **Maintainability**: Clear separation of concerns
4. **User Experience**: Auto-detection and clear game selection
5. **Code Quality**: Type hints and modern Python features

## Potential Challenges & Solutions

1. **Data Duplication**: Use inheritance for shared patterns
2. **Version Detection**: Implement fallback manual selection
3. **Performance**: Lazy load game-specific data
4. **UI Complexity**: Progressive disclosure of advanced options