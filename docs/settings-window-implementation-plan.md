# Settings Window Implementation Plan

## Overview
This document outlines the implementation plan for refactoring the CLASSIC application's settings from the main window's grid layout into a dedicated settings dialog window. This will improve UI organization and provide a centralized location for all application settings.

## Current State Analysis

### Settings Currently in Main Tab Grid Layout
The following settings are currently embedded in the main tab's grid layout in `TabSetupMixin.setup_checkboxes()`:

1. **Checkboxes** (7 items in 2-column grid): (change all-caps to title case)
   - FCX Mode - Enable extended file integrity checks
   - SIMPLIFY LOGS - Remove redundant lines from crash logs
   - UPDATE CHECK - Automatically check for CLASSIC updates
   - VR MODE - Prioritize settings for VR version of the game
   - SHOW FID VALUES - Look up FormID names (slower scans)
   - MOVE INVALID LOGS - Move incomplete/unscannable logs to a separate folder
   - AUDIO NOTIFICATIONS - Play sounds for scan completion/errors

2. **Update Source ComboBox**:
   - Options: Nexus, GitHub, Both
   - Currently placed below checkboxes with label

3. **INI Path Setting**:
   - Currently handled by "CHANGE INI PATH" button in bottom buttons section
   - **WILL BE REMOVED** - This is a power-user feature that can be dangerous
   - Users who need this can edit `CLASSIC Settings.yaml` directly

## Implementation Plan

### Phase 1: Create Settings Dialog Infrastructure

#### 1.1 Create New Settings Dialog Class
**File**: `ClassicLib/Interface/SettingsDialog.py`

```python
class SettingsDialog(QDialog):
    """
    Dedicated settings dialog for CLASSIC application configuration.
    Centralizes all application settings in a single modal dialog.
    """
    
    def __init__(self, parent=None):
        # Initialize dialog with proper modality
        # Set window title: "CLASSIC Settings"
        # Set minimum size: 600x500
        # Apply DARK_MODE stylesheet
```

#### 1.2 Dialog Layout Structure
- **Main Layout**: QVBoxLayout with tabs
- **Tab Widget**: QTabWidget with following tabs:
  - "General" - Main application settings
  - "Scanning" - Scan-related settings
  - "Updates" - Update checking settings

#### 1.3 Settings Categories (change all-caps to title case in the UI)

**General Tab**:
- AUDIO NOTIFICATIONS checkbox
- VR MODE checkbox

**Scanning Tab**:
- FCX MODE checkbox
- SIMPLIFY LOGS checkbox
- SHOW FID VALUES checkbox
- MOVE INVALID LOGS checkbox

**Updates Tab**:
- UPDATE CHECK checkbox
- Update Source ComboBox (Nexus/GitHub/Both)
- Check for Updates button (immediate check)

### Phase 2: Implement Settings Persistence

#### 2.1 Settings Manager
- Create methods to load all settings on dialog open
- Create methods to save all settings on dialog accept
- Handle YAML read/write through existing `YamlSettingsCache`

#### 2.2 Signal Handling
- Connect checkbox state changes to immediate save
- Connect ComboBox changes to immediate save
- Show confirmation for critical settings changes

### Phase 3: Refactor Main Window

#### 3.1 Remove Settings from Main Tab
**File**: `ClassicLib/Interface/TabSetupMixin.py`

Remove from `setup_main_tab()`:
- Remove call to `setup_checkboxes()`
- Remove checkbox grid layout
- Remove update source combo box
- Keep main action buttons and folder selections

Remove from `setup_bottom_buttons()`:
- Remove "CHANGE INI PATH" button
- Keep "OPEN SETTINGS" button (repurpose to open new dialog)

#### 3.2 Add Settings Dialog Launch
- Modify "OPEN SETTINGS" button to launch SettingsDialog
- Change button text to "SETTINGS" for clarity
- Update tooltip: "Open application settings dialog"

#### 3.3 Update Button Handler
```python
def open_settings(self):
    """Opens the settings dialog instead of YAML file."""
    dialog = SettingsDialog(self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Apply any settings that need immediate effect
        self.apply_settings_changes()
```

### Phase 4: Migration and Cleanup

#### 4.1 Remove Obsolete Code
- Remove `setup_checkboxes()` method from TabSetupMixin
- Remove checkbox creation helper if no longer needed elsewhere
- Clean up unused imports

#### 4.2 Create Settings Application Method
```python
def apply_settings_changes(self):
    """Apply settings that affect the UI immediately."""
    # Refresh UI elements based on new settings
    # Update button states if needed
    # Reload configuration that affects current session
```

### Phase 5: Testing Requirements

#### 5.1 Functional Tests
- Test all checkbox states persist correctly
- Test ComboBox selection persists
- Test dialog cancellation (no changes saved)
- Test dialog acceptance (all changes saved)

#### 5.2 UI Tests
- Verify dialog opens centered on parent
- Verify tab navigation works correctly
- Verify all tooltips are present
- Verify dark mode styling is applied
- Test keyboard navigation (Tab, Enter, Escape)

#### 5.3 Integration Tests
- Test settings affect application behavior
- Test FCX mode enables/disables correctly
- Test audio notifications trigger when enabled
- Test update checks respect source setting

### Phase 6: Additional Enhancements

#### 6.1 Settings Import/Export
- Add buttons to export settings to file
- Add button to import settings from file
- Use JSON format for portability

#### 6.2 Settings Reset
- Add "Reset to Defaults" button
- Show confirmation dialog before reset
- Reload dialog with default values

#### 6.3 Settings Validation
- Validate all settings are within acceptable ranges
- Show warnings for conflicting settings
- Prevent saving invalid configurations

## Implementation Order

1. **Create SettingsDialog class** with basic structure
2. **Implement General and Scanning tabs** with checkboxes
3. **Implement Updates tab** with ComboBox
4. **Add load/save functionality** for all settings
5. **Update main window** to launch dialog
6. **Remove old settings** from main tab
7. **Test all functionality**
8. **Add enhancements** (import/export, reset)

## File Changes Summary

### New Files
- `ClassicLib/Interface/SettingsDialog.py` - Main settings dialog implementation

### Modified Files
- `ClassicLib/Interface/TabSetupMixin.py` - Remove checkbox setup, update button handler
- `ClassicLib/Interface/FolderManagementMixin.py` - Remove `select_folder_ini()` method
- `CLASSIC_Interface.py` - Import SettingsDialog, update button connections

### Deleted Code Sections
- `TabSetupMixin.setup_checkboxes()` - Entire method
- Bottom button "CHANGE INI PATH" - From `setup_bottom_buttons()`
- Checkbox grid layout code - From main tab setup

## Benefits of This Refactoring

1. **Improved Organization**: All settings in one dedicated location
2. **Better UX**: Cleaner main window, focused on primary actions
3. **Scalability**: Easy to add new settings without cluttering main UI
4. **Maintainability**: Settings logic isolated in single module
5. **Consistency**: All settings follow same interaction pattern
6. **Professional**: Follows standard desktop application patterns

## Risk Mitigation

1. **Backward Compatibility**: Ensure existing YAML settings are preserved
2. **User Communication**: Add first-run hint about new settings location
3. **Testing**: Comprehensive testing before release
4. **Documentation**: Update user documentation with new screenshots
5. **Rollback Plan**: Keep old code in separate branch initially

## Estimated Implementation Time

- Phase 1-2: 2-3 hours (Dialog creation and persistence)
- Phase 3-4: 1-2 hours (Main window refactoring)
- Phase 5: 1-2 hours (Testing)
- Phase 6: 1-2 hours (Enhancements)
- **Total**: 5-9 hours of implementation

## Note on INI Folder Path

The INI Folder Path override functionality still exists in the codebase but is not exposed in the settings dialog. This is intentional:

1. **Why it's removed from UI**: Path manipulation can be dangerous and lead to configuration issues
2. **For power users**: The setting can still be manually edited in `CLASSIC Settings.yaml`
3. **How it works**: When set, it overrides the auto-detected documents folder path
4. **Use case**: Primarily for MO2 users with profile-specific INI locations

The backend functionality (`DocsPath.find_docs_path()`) remains unchanged and will continue to respect the override if manually configured.

## Notes for Implementation

1. Use `QDialog.exec()` for modal behavior
2. Implement `accept()` and `reject()` properly
3. Consider using `QDialogButtonBox` for OK/Cancel buttons
4. Ensure all settings have descriptive tooltips
5. Group related settings visually with separators or group boxes
6. Consider adding setting descriptions or help icons
7. Validate all user input before saving
8. Show progress/status when saving multiple settings
9. Consider adding search/filter for settings (future enhancement)
10. Ensure dialog respects system DPI settings for scaling