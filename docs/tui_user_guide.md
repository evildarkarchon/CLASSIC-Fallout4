# CLASSIC TUI User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Main Interface](#main-interface)
5. [Keyboard Shortcuts](#keyboard-shortcuts)
6. [Running Scans](#running-scans)
7. [Managing Output](#managing-output)
8. [Settings Configuration](#settings-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

## Introduction

CLASSIC TUI (Terminal User Interface) provides a powerful, keyboard-driven interface for analyzing crash logs and checking game file integrity for Bethesda games (Fallout 4 and Skyrim). The TUI offers all the functionality of the GUI version in a lightweight, terminal-based package.

### Key Features
- Fast keyboard navigation
- Real-time log analysis
- Color-coded output for easy reading
- Search and export capabilities
- Persistent settings
- Status monitoring

## Installation

### Prerequisites
- Python 3.12 or higher
- Terminal with color support
- Windows, macOS, or Linux

### Installing CLASSIC TUI

```bash
# Clone the repository
git clone https://github.com/yourusername/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4

# Install dependencies
poetry install

# Run the TUI
python CLASSIC_TUI.py
```

## Getting Started

### First Launch

When you first launch CLASSIC TUI, you'll see the main screen with:
- Folder configuration fields
- Scan operation buttons
- Settings checkbox
- Output viewer

### Initial Configuration

1. **Press `Ctrl+O`** to open the Settings screen
2. Configure your folder paths:
   - **Staging Mods Folder**: Where your mod files are located
   - **Custom Scan Folder**: Alternative location for crash logs
3. Set your preferences:
   - **Auto-scroll**: Automatically follow new output
   - **Show timestamps**: Add timestamps to output lines
   - **Check for updates**: Enable update notifications
4. **Click Save** or press `Enter` to save your settings

## Main Interface

### Layout

```
┌─────────────────────────────────────────────────┐
│ CLASSIC - Crash Log Auto Scanner                │
├─────────────────────────────────────────────────┤
│ MAIN OPTIONS                                    │
│                                                 │
│ STAGING MODS FOLDER                            │
│ [____________________________] [Browse]        │
│                                                 │
│ CUSTOM SCAN FOLDER                             │
│ [____________________________] [Browse]        │
│                                                 │
│ [Crash Logs Scan] [Game Files Scan] [Papyrus] │
│                                                 │
│ ☑ Check for Updates                            │
│                                                 │
│ ┌─OUTPUT────────────────────────────────────┐ │
│ │                                           │ │
│ │ Output appears here...                    │ │
│ │                                           │ │
│ └───────────────────────────────────────────┘ │
│                                                 │
│ Status: Ready | Last Scan: Never | Folder: -   │
└─────────────────────────────────────────────────┘
```

### Components

1. **Folder Selectors**: Input fields for specifying scan directories
2. **Scan Buttons**: Launch different types of scans
3. **Settings Checkbox**: Quick access to common settings
4. **Output Viewer**: Displays scan results with color coding
5. **Status Bar**: Shows current operation status and information

## Keyboard Shortcuts

### Essential Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `F1` | Help | Open help documentation |
| `Q` | Quit | Exit the application |
| `Tab` | Next | Navigate to next element |
| `Shift+Tab` | Previous | Navigate to previous element |
| `Enter` | Activate | Activate button/submit input |
| `ESC` | Cancel | Close dialogs/cancel operations |

### Scan Operations

| Key | Action | Description |
|-----|--------|-------------|
| `F5` or `R` | Crash Scan | Run crash logs analysis |
| `F6` or `G` | Game Scan | Check game file integrity |
| `F7` or `P` | Papyrus Monitor | Toggle Papyrus log monitoring |

### Output Management

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+L` | Clear | Clear output viewer |
| `/` | Search | Search within output |
| `ESC` | Exit Search | Close search mode |

### Settings & Navigation

| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+O` | Settings | Open settings screen |
| `Ctrl+C` | Force Quit | Force exit application |

## Running Scans

### Crash Logs Scan

The crash logs scan analyzes crash dumps to identify problematic mods and issues.

#### To run a crash scan:
1. Press `F5` or click "Crash Logs Scan"
2. The scanner will:
   - Search configured folders for crash logs
   - Parse crash dumps and stack traces
   - Identify FormIDs and resolve to mods
   - Detect common crash patterns
   - Generate analysis report

#### Output includes:
- **Red text**: Critical errors and crash causes
- **Yellow text**: Warnings and potential issues
- **Green text**: Successfully identified mods
- **Blue text**: Informational messages

### Game Files Scan

The game files scan verifies the integrity of your game installation.

#### To run a game scan:
1. Press `F6` or click "Game Files Scan"
2. The scanner will:
   - Check game executable and libraries
   - Verify INI file settings
   - Validate mod file structure
   - Check for missing dependencies
   - Report file conflicts

#### Results show:
- File integrity status
- Missing or corrupted files
- Configuration issues
- Recommended fixes

### Papyrus Monitor

The Papyrus monitor watches script logs in real-time for issues.

#### To use Papyrus monitoring:
1. Press `F7` to start monitoring
2. The monitor will:
   - Watch Papyrus log files
   - Highlight script errors
   - Track performance issues
   - Alert on stack dumps
3. Press `F7` again to stop monitoring

## Managing Output

### Viewing Results

The output viewer displays all scan results with:
- Color-coded messages for easy identification
- Timestamps for each entry (if enabled)
- Automatic scrolling to follow new content
- Searchable content

### Searching Output

To search within the output:
1. Press `/` to open search
2. Type your search term
3. Press `Enter` to find matches
4. Press `Enter` again to jump to next match
5. Press `ESC` to exit search mode

### Automatic Output Saving

Scan results are automatically saved during the scanning process:
- Results are saved to timestamped files in the output directory
- No manual intervention required
- Each scan creates its own output file for reference

### Clearing Output

To clear the display:
- Press `Ctrl+L` to clear all output
- Useful before starting a new scan

## Settings Configuration

### Accessing Settings

Press `Ctrl+O` to open the Settings screen with three sections:

### Folder Configuration
- **Staging Mods Folder**: Primary mod directory
- **Custom Scan Folder**: Alternative scan location

### Display Settings
- **Auto-scroll output**: Follow new output automatically
- **Show timestamps**: Add time to each output line
- **Max output lines**: Limit output buffer size (default: 10000)

### General Settings
- **Check for updates**: Enable update notifications
- **Game**: Select target game (Fallout4/Skyrim/SkyrimSE)

### Saving Settings

1. Make your changes
2. Click "Save" or press `Enter`
3. Settings are saved to YAML configuration
4. Changes take effect immediately

## Troubleshooting

### Common Issues

#### Scanner Not Finding Logs
- Verify folder paths are correct
- Check folder permissions
- Ensure logs exist in specified location
- Use absolute paths instead of relative

#### Slow Performance
- Reduce max lines in output viewer
- Clear output before starting new scan
- Close other applications
- Check disk I/O performance

#### Output Not Updating
- Check auto-scroll is enabled
- Clear output and retry
- Verify scan is running (check status bar)
- Look for error messages in red

#### Keyboard Shortcuts Not Working
- Ensure correct window has focus
- Check no modal dialogs are open
- Try alternative shortcuts
- Restart the application

### Error Messages

| Error | Solution |
|-------|----------|
| Permission Denied | Run with appropriate permissions |
| Path Not Found | Verify folder exists |
| Memory Error | Clear output, reduce max lines |
| No Logs Found | Check folder configuration |

## Advanced Features

### Status Bar Information

The status bar provides real-time information:
- **Status**: Current operation (Ready/Scanning/Error)
- **Last Scan**: Timestamp of last completed scan
- **Folder**: Active scan directory

### Confirmation Dialogs

Important operations show confirmation dialogs:
- Prevent accidental data loss
- Clear action descriptions
- Keyboard navigation support
- ESC to cancel, Enter to confirm

### Performance Optimization

For best performance:
1. Set reasonable max lines (5000-10000)
2. Clear output between scans
3. Disable auto-scroll for large outputs
4. Use search instead of manual scrolling

### Multi-Game Support

CLASSIC TUI supports multiple games:
1. Open Settings (`Ctrl+O`)
2. Select game from dropdown
3. Save settings
4. Scanner adjusts for selected game

### Automatic Export Formats

Automatically saved output files include:
- Full scan results
- Timestamps for each entry
- Color codes removed for readability
- Structured format for sharing

## Tips & Tricks

### Efficient Workflow
1. Configure folders once in Settings
2. Use keyboard shortcuts for all operations
3. Clear output before each scan
4. Results are automatically saved during scans
5. Use search to find specific errors

### Reading Output
- Focus on red entries first (critical errors)
- Yellow warnings may indicate issues
- Green shows successful operations
- Blue provides context information

### Performance Tips
- Run one scan at a time
- Close help/settings when not needed
- Use focused scans on specific folders
- Monitor status bar for progress

### Keyboard Navigation
- Tab moves forward through elements
- Shift+Tab moves backward
- Arrow keys navigate within elements
- Enter activates focused element
- ESC is universal cancel/close

## Getting Help

### In-Application Help
- Press `F1` for built-in documentation
- Navigate tabs for different topics
- Search help content with `/`

### Online Resources
- GitHub repository documentation
- Community forums
- Discord support channel
- Video tutorials

### Reporting Issues
When reporting issues, include:
1. CLASSIC version
2. Operating system
3. Error messages (red text)
4. Steps to reproduce
5. Saved output file

## Conclusion

CLASSIC TUI provides a powerful, efficient interface for crash log analysis. Master the keyboard shortcuts for maximum productivity, and use the status bar to monitor operations. All scan results are automatically saved for your reference, and your settings persist between sessions.

For additional help, press `F1` within the application or visit the project repository.