# Multi-Game and Multi-Version Support Implementation Plan

## Executive Summary
This document outlines the implementation plan for adding comprehensive multi-game and multi-version support to CLASSIC. The refactoring will eliminate the current VR mode hack by treating VR versions as separate games, improve data organization, and provide a clean architecture for supporting multiple Bethesda games and their various versions.

## Current State Analysis

### Current Structure
```
CLASSIC Data/
├── databases/
│   ├── CLASSIC Fallout4.yaml      # Mixed flat/VR data
│   ├── CLASSIC Skyrim.yaml        # Mixed flat/VR data
│   └── CLASSIC Main.yaml          # Global settings with VR Mode toggle
├── CLASSIC Fallout4 Local.yaml    # Local game paths
└── [other assets]
```

### Current Issues
1. **VR Mode Toggle**: Single boolean flag mixes concerns between flat and VR versions
2. **Data Mixing**: VR and flat game data stored in same YAML files with conditional sections
3. **Version Coupling**: No clean separation between version-specific and shared data
4. **Special Cases**: Buffout 4 fork info stored in VR section but works with both versions
5. **Limited Extensibility**: Adding new games or versions requires significant refactoring

## Proposed Architecture

### New Directory Structure
```
CLASSIC Data/
├── games/
│   ├── Fallout4/
│   │   ├── shared/
│   │   │   ├── formids.db              # FormID database shared across versions
│   │   │   ├── mods_common.yaml        # Mods that work across all versions
│   │   │   └── patterns.yaml           # Common crash patterns
│   │   ├── versions/
│   │   │   ├── standard/
│   │   │   │   ├── config.yaml         # Version-specific configuration
│   │   │   │   ├── mods.yaml           # Version-specific mods
│   │   │   │   ├── hashes.yaml         # File integrity hashes
│   │   │   │   └── xse_plugins.yaml    # F4SE plugins
│   │   │   ├── vr/
│   │   │   │   ├── config.yaml
│   │   │   │   ├── mods.yaml
│   │   │   │   ├── hashes.yaml
│   │   │   │   └── xse_plugins.yaml    # F4SEVR plugins
│   │   │   └── nextgen/                # Future-proofing for next-gen update
│   │   │       └── [version files]
│   │   └── game_config.yaml            # Game-level configuration
│   │
│   ├── SkyrimSE/
│   │   ├── shared/
│   │   │   └── [shared data files]
│   │   ├── versions/
│   │   │   ├── standard/
│   │   │   │   └── [version files]
│   │   │   ├── vr/
│   │   │   │   └── [version files]
│   │   │   └── anniversary/
│   │   │       └── [version files]
│   │   └── game_config.yaml
│   │
│   └── Starfield/                      # Future game support
│       └── [game structure]
│
├── global/
│   ├── settings.yaml                   # User settings (replaces CLASSIC Settings.yaml)
│   ├── ignore_list.yaml                # Global ignore list
│   └── config.yaml                     # CLASSIC application config
│
└── [graphics, sounds, etc.]            # Unchanged asset directories
```

## Implementation Phases

### Phase 1: Data Model Design (Week 1)
1. Design new YAML schemas for each configuration type
2. Create Python dataclasses for type-safe configuration
3. Define migration mappings from old to new structure
4. Document special cases (Buffout 4 fork handling)

### Phase 2: Migration System (Week 1-2)
1. Create backup system for existing data
2. Implement migration script to convert old YAML structure
3. Build validation system for migrated data
4. Create rollback mechanism

### Phase 3: Core Refactoring (Week 2-3)
1. Replace VR Mode boolean with game version selection
2. Update YamlSettingsCache to handle new directory structure
3. Refactor game detection logic
4. Update path resolution for multi-version support

### Phase 4: Game-Specific Handlers (Week 3-4)
1. Create abstract GameHandler base class
2. Implement Fallout4Handler with version detection
3. Implement SkyrimSEHandler with version detection
4. Add special case handling (Buffout 4 fork logic)

### Phase 5: UI Updates (Week 4-5)
1. Replace VR Mode checkbox with version dropdown
2. Add game selection if multiple games detected
3. Update settings dialog for new structure
4. Implement version-specific UI elements

### Phase 6: Testing & Validation (Week 5-6)
1. Unit tests for migration system
2. Integration tests for each game/version combination
3. Regression testing for existing functionality
4. Performance testing with new data structure

## Technical Details

### New Configuration Classes
```python
@dataclass
class GameVersion:
    name: str               # "standard", "vr", "anniversary"
    display_name: str       # "Fallout 4", "Fallout 4 VR"
    xse_name: str          # "F4SE", "F4SEVR"
    xse_version: str       # Required XSE version
    game_exe: str          # "Fallout4.exe", "Fallout4VR.exe"
    
@dataclass
class GameConfig:
    game_id: str           # "Fallout4", "SkyrimSE"
    display_name: str      # "Fallout 4", "Skyrim Special Edition"
    versions: List[GameVersion]
    default_version: str   # Default version to use
    
@dataclass
class ModEntry:
    name: str
    file: str
    version: Optional[str]
    versions_supported: List[str]  # ["standard", "vr"]
    special_handling: Optional[Dict]  # For cases like Buffout 4 fork
```

### Migration Algorithm
```python
def migrate_yaml_structure():
    # 1. Backup existing data
    backup_current_data()
    
    # 2. Parse old structure
    old_data = load_old_yaml_files()
    
    # 3. Transform to new structure
    new_data = transform_data_structure(old_data)
    
    # 4. Handle special cases
    handle_buffout4_fork_case(new_data)
    
    # 5. Validate transformed data
    validate_new_structure(new_data)
    
    # 6. Write new structure
    write_new_yaml_files(new_data)
    
    # 7. Update settings
    migrate_user_settings()
```

### Special Case: Buffout 4 Fork
The current Buffout 4 fork presents a special case:
- Currently stored in VR section but works with both versions
- Solution: Store in `shared/mods_common.yaml` with version compatibility flags
- Add special handling logic in ModEntry for cross-version compatibility

## Benefits

### Immediate Benefits
1. **Clean Separation**: VR and flat versions properly separated
2. **Better Organization**: Version-specific vs shared data clearly delineated
3. **Easier Maintenance**: Adding new versions doesn't affect existing ones
4. **Type Safety**: Dataclasses provide better IDE support and validation

### Long-term Benefits
1. **Scalability**: Easy to add new games (Starfield, Elder Scrolls VI)
2. **Version Support**: Can handle game updates (Anniversary, Next-Gen)
3. **Modular Architecture**: Each game can have custom handling logic
4. **Better Testing**: Isolated components easier to test

## Risk Mitigation

### Risks and Mitigations
1. **Data Loss Risk**: Full backup system before migration
2. **Compatibility Break**: Provide compatibility mode for transition period
3. **User Confusion**: Clear migration messages and documentation
4. **Performance Impact**: Benchmark and optimize new structure
5. **Bug Introduction**: Comprehensive test suite before release

## Testing Strategy

### Test Coverage Areas
1. **Migration Testing**: Verify all data migrates correctly
2. **Version Detection**: Test each game version detection
3. **Path Resolution**: Verify paths work for all versions
4. **Special Cases**: Test Buffout 4 fork and similar edge cases
5. **UI Testing**: Verify UI updates work correctly
6. **Regression Testing**: Ensure existing features still work

## Success Criteria

### Measurable Outcomes
1. All existing YAML data successfully migrated
2. VR Mode toggle eliminated from codebase
3. Support for at least 4 game versions (FO4, FO4VR, SSE, SSEVR)
4. No regression in existing functionality
5. Performance within 5% of current implementation
6. 90% test coverage for new code

## Timeline

### 6-Week Implementation Schedule
- **Week 1**: Data model design and migration system
- **Week 2**: Core refactoring begins
- **Week 3**: Game-specific handlers implementation
- **Week 4**: UI updates and integration
- **Week 5**: Testing and bug fixes
- **Week 6**: Documentation and release preparation

## Appendix: YAML Schema Examples

### Game Configuration (game_config.yaml)
```yaml
game:
  id: Fallout4
  display_name: "Fallout 4"
  registry_key: "HKLM\\SOFTWARE\\Bethesda Softworks\\Fallout4"
  versions:
    - id: standard
      display_name: "Fallout 4"
      exe_name: "Fallout4.exe"
      xse_name: "F4SE"
      default: true
    - id: vr
      display_name: "Fallout 4 VR"
      exe_name: "Fallout4VR.exe"
      xse_name: "F4SEVR"
    - id: nextgen
      display_name: "Fallout 4 (Next-Gen)"
      exe_name: "Fallout4.exe"
      xse_name: "F4SE"
      min_version: "1.10.980"
```

### Version-Specific Mods (versions/standard/mods.yaml)
```yaml
mods:
  crash_generators:
    - name: "Buffout 4"
      file: "Buffout4.dll"
      version: "1.28.6"
      url: "https://www.nexusmods.com/fallout4/mods/47359"
      
  xse_plugins:
    - name: "Address Library"
      file: "f4se/plugins/version-*.bin"
      required: true
      
  problematic_mods:
    - name: "Unlimited Survival Mode"
      file: "UnlimitedSurvivalMode.esp"
      issue: "Causes crashes in workshop mode"
```

### Shared Mods (shared/mods_common.yaml)
```yaml
shared_mods:
  utilities:
    - name: "Buffout 4 NG Fork"
      file: "Buffout4.dll"
      versions_supported: ["standard", "vr"]
      special_note: "Fork that supports both flat and VR"
      check_logic: "custom_buffout_fork_check"
```