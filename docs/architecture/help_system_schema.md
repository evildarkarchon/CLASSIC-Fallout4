# Context-Sensitive Help System Schema

## YAML Structure

The help system uses a YAML file to define help topics organized by category and context.

### File Location
- `CLASSIC Data/Help/GUI_Help.yaml`

### Schema Definition

```yaml
# Root structure
help:
  # Category name (e.g., "main", "backups", "results", "settings")
  <category>:
    # Topic ID (e.g., "scan_crash_logs", "backup_xse", "delete_report")
    <topic_id>:
      title: "Help Topic Title"
      content: |
        Multi-line help content in Markdown format.

        Supports:
        - **Bold** and *italic* text
        - Lists (bulleted and numbered)
        - Code blocks
        - Links

      # Optional fields
      shortcut: "Ctrl+S"  # Keyboard shortcut (if applicable)
      related:            # Related topics
        - category: "results"
          topic: "view_report"
        - category: "settings"
          topic: "auto_switch"
```

### Example Content

```yaml
help:
  main:
    scan_crash_logs:
      title: "Scan Crash Logs"
      shortcut: "Ctrl+L"
      content: |
        # Scan Crash Logs

        Analyzes crash logs from your game directory and generates detailed reports.

        ## What it does:
        1. **Finds crash logs** in your game's XSE folder (e.g., My Games/Fallout4/F4SE)
        2. **Copies logs** to the Crash Logs folder for processing
        3. **Analyzes** each log for common issues
        4. **Generates** markdown reports in the Reports folder

        ## Requirements:
        - Game root path configured in Settings
        - At least one crash log present

        ## Results:
        After scanning, view the results in the **Results** tab.

      related:
        - category: "results"
          topic: "view_report"
        - category: "settings"
          topic: "game_paths"

    scan_game_files:
      title: "Scan Game Files"
      shortcut: "Ctrl+G"
      content: |
        # Scan Game Files

        Performs integrity checks on your game installation.

        ## What it scans:
        - Plugin files (.esp, .esm, .esl)
        - Texture files (.dds)
        - Game executables

        ## Note:
        Full integrity checking is coming in future updates.

      related:
        - category: "settings"
          topic: "game_paths"

  backups:
    backup_overview:
      title: "File Backup System"
      content: |
        # File Backup System

        Create backups of important game files before making changes.

        ## Supported Files:

        ### Script Extender (XSE)
        - F4SE for Fallout 4
        - SKSE for Skyrim

        ### Graphics
        - ReShade files
        - Vulkan runtime
        - ENB files

        ## Operations:
        - **Backup**: Create a backup of the files
        - **Restore**: Restore files from backup
        - **Remove**: Delete backup files

        Backups are stored in the `Backups/` folder.

      related:
        - category: "backups"
          topic: "backup_xse"
        - category: "backups"
          topic: "backup_reshade"

    backup_xse:
      title: "Script Extender Backup"
      content: |
        # Script Extender Backup

        Backs up your Script Extender files (F4SE/SKSE).

        ## Files Backed Up:
        - f4se_loader.exe / skse_loader.exe
        - f4se_steam_loader.dll / skse_steam_loader.dll
        - All DLL files in f4se/skse folders

        ## Use Cases:
        - Before updating Script Extender
        - Before game updates
        - When troubleshooting issues

      related:
        - category: "backups"
          topic: "backup_overview"

  results:
    view_report:
      title: "View Report"
      content: |
        # View Report

        Display detailed crash analysis reports.

        ## Report Contents:
        - **Summary**: Overview of the crash
        - **Probable Cause**: Most likely reason for the crash
        - **Stack Trace**: Technical details
        - **Plugins**: Loaded mods when crash occurred
        - **Recommendations**: Suggested fixes

        ## Actions:
        - **Copy to Clipboard**: Copy entire report
        - **Delete**: Remove report from disk
        - **Zoom**: Adjust text size for readability

      related:
        - category: "main"
          topic: "scan_crash_logs"
        - category: "results"
          topic: "delete_report"

    delete_report:
      title: "Delete Report"
      content: |
        # Delete Report

        Permanently delete a crash report from disk.

        ## Warning:
        This action cannot be undone!

        ## Confirmation:
        You will be asked to confirm before deletion.

      related:
        - category: "results"
          topic: "view_report"

  settings:
    game_paths:
      title: "Game Paths Configuration"
      content: |
        # Game Paths Configuration

        Configure paths to your game installation.

        ## Required Paths:

        ### Game Root
        The main game installation folder (e.g., `C:/Steam/steamapps/common/Fallout 4`)

        ### Documents Root
        Your My Games folder (e.g., `C:/Users/YourName/Documents`)

        ## Optional Paths:

        ### INI Folder
        Custom location for .ini files (usually auto-detected)

        ### Mods Folder
        Custom mod manager folder (e.g., Mod Organizer 2 mods)

        ### Custom Scan Folder
        Additional folder to scan for crash logs

      related:
        - category: "main"
          topic: "scan_crash_logs"
        - category: "main"
          topic: "scan_game_files"

    auto_switch:
      title: "Auto-Switch to Results Tab"
      content: |
        # Auto-Switch to Results Tab

        Automatically switch to the Results tab after a successful scan.

        ## Behavior:
        - **Enabled** (default): After scanning, the Results tab opens automatically
        - **Disabled**: Stay on current tab after scanning

        ## Use Cases:
        - Enable if you want immediate access to results
        - Disable if you prefer to manually switch tabs

      related:
        - category: "results"
          topic: "view_report"
```

## Help Dialog UI Specification

### Dialog Layout
```
┌─────────────────────────────────────────┐
│ Help: <Topic Title>                  [X]│
├─────────────────────────────────────────┤
│                                         │
│  [Markdown rendered content]            │
│                                         │
│  ┌────────────────────────────────┐    │
│  │ Multi-line help text with      │    │
│  │ Markdown formatting:           │    │
│  │                                │    │
│  │ - **Bold** text                │    │
│  │ - *Italic* text                │    │
│  │ - Lists                        │    │
│  │ - Code blocks                  │    │
│  └────────────────────────────────┘    │
│                                         │
│ Related Topics:                         │
│  • View Report                          │
│  • Game Paths Configuration             │
│                                         │
├─────────────────────────────────────────┤
│                            [Close]      │
└─────────────────────────────────────────┘
```

### Features
- **Markdown rendering**: Rich text formatting
- **Related topics**: Clickable links to related help
- **Keyboard shortcuts**: Display shortcuts if available
- **Scrollable content**: For long help topics
- **Responsive sizing**: Adjusts to content

## Integration Points

### UI Elements
Each UI element can trigger help by:
```rust
// Button with help support
on_help_clicked => {
    show_help("main", "scan_crash_logs");
}
```

### Context Detection
The help system detects current context:
- Current tab (Main, Backups, Results)
- Selected UI element
- Current operation state

### Keyboard Shortcut
- `F1` key opens context-sensitive help
- Shows help for currently focused element or tab

## Implementation Plan

1. **YAML File Creation**
   - Create `CLASSIC Data/Help/GUI_Help.yaml`
   - Populate with initial help topics

2. **Rust Helper Module**
   - `rust/ui-applications/classic-ui-shared/src/help.rs`
   - Load and parse YAML
   - Lookup help topics by category/ID
   - Format content for display

3. **UI Dialog Component** (TUI/CLI or future GUI)
   - Help content display
   - Related topics links
   - Responsive layout

4. **Keyboard Integration**
   - Global F1 handler
   - Context detection logic
   - Focus tracking for element-specific help

5. **Property Bindings**
   - Add help-related properties to MainWindow
   - Wire up callbacks for showing/hiding help
   - Handle related topic navigation
