# CLASSIC TUI User Guide

**Version:** 0.1.0
**Platform:** Windows, Linux, macOS
**Target Users:** Terminal enthusiasts, SSH users, server administrators

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Main Screen](#main-screen)
5. [Keyboard Shortcuts](#keyboard-shortcuts)
6. [Features](#features)
7. [Settings](#settings)
8. [Troubleshooting](#troubleshooting)
9. [Terminal Compatibility](#terminal-compatibility)

---

## Introduction

CLASSIC TUI is a Terminal User Interface for analyzing Fallout 4 and Skyrim crash logs. Built with Ratatui and Rust, it
provides:

- **🎨 Modern TUI**: Beautiful terminal interface with mouse support
- **⚡ High performance**: 60 FPS rendering, <100MB memory
- **🔄 Real-time updates**: Live Papyrus log monitoring
- **⌨️ Keyboard-driven**: Efficient workflow without touching the mouse
- **🖥️ SSH-friendly**: Works great over remote connections

### When to Use TUI

- **Remote servers**: Analyze crash logs over SSH
- **Terminal workflows**: Integration with tmux/screen
- **Keyboard power users**: Faster than GUI for experienced users
- **Headless environments**: No GUI required
- **Resource-constrained**: Lightweight compared to GUI

---

## Installation

### Method 1: Download Pre-built Binary (Recommended)

1. Download `ClassicLib-rs/ui-applications/classic-tui.exe` from the [releases page](https://github.com/evildarkarchon/CLASSIC-Fallout4/releases)
2. Place in a directory of your choice
3. (Optional) Add to PATH for system-wide access

### Method 2: Install via Cargo

```bash
cargo install --git https://github.com/evildarkarchon/CLASSIC-Fallout4 ClassicLib-rs/ui-applications/classic-tui
```

### Verification

```bash
ClassicLib-rs/ui-applications/classic-tui --version
# Output: ClassicLib-rs/ui-applications/classic-tui 0.1.0
```

---

## Quick Start

### Launch TUI

```bash
ClassicLib-rs/ui-applications/classic-tui
```

### First-Time Setup

1. Launch CLASSIC TUI
2. Set **Staging Mods Folder** (Tab to navigate, Enter to edit)
3. (Optional) Set **Custom Scan Folder**
4. Press **F5** or **R** to start crash log scan
5. View results in the output viewer

---

## Main Screen

```
┌──────────────────────────────────────────────────────────────────┐
│ CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker      │
│ Terminal User Interface v0.1.0                                   │
└──────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│ STAGING MODS FOLDER                                              │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ C:\MO2\mods                                         [Browse] │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ CUSTOM SCAN FOLDER (OPTIONAL)                                    │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ D:\AdditionalLogs                                   [Browse] │ │
│ └──────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────┤
│ [Crash Logs Scan (F5)]  [Game Files Scan (F6)]  [Papyrus (F7)] │
├──────────────────────────────────────────────────────────────────┤
│ [ ] Check for Updates                                            │
├══════════════════════════════════════════════════════════════════┤
│                      OUTPUT VIEWER                               │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ Initializing scan...                                       │   │
│ │   ✓ Configuration loaded                                   │   │
│ │   ✓ Found 47 crash logs                                    │   │
│ │                                                            │   │
│ │ Scanning: crash-2024-01-15-14-23-45.log                   │   │
│ │ Progress: [████████████████░░░░░░░] 65% (30/47)          │   │
│ │                                                            │   │
│ │ (Scroll: ↑↓ | Search: / | Clear: Ctrl+L)                  │   │
│ └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
│ F1 Help │ F5 Crash Scan │ F6 Game Scan │ F7 Papyrus │ Q Quit │
└──────────────────────────────────────────────────────────────────┘
```

### Screen Components

1. **Title Bar**: Application name and version
2. **Folder Selectors**: Configure scan directories
    - **Green border**: Valid path (exists and is directory)
    - **Red border**: Invalid path
    - **Yellow border**: Currently focused
3. **Action Buttons**: Start scans or monitoring
4. **Options**: Toggleable settings (Update check)
5. **Output Viewer**: Scrollable log output
6. **Status Bar**: Keyboard shortcuts

---

## Keyboard Shortcuts

### Global Shortcuts

| Key         | Action                         |
|-------------|--------------------------------|
| `Q`         | Quit application               |
| `Ctrl+C`    | Quit application (alternative) |
| `F1`        | Show help screen               |
| `Ctrl+O`    | Open settings screen           |
| `Tab`       | Navigate to next widget        |
| `Shift+Tab` | Navigate to previous widget    |

### Scan Operations

| Key        | Action                 |
|------------|------------------------|
| `F5` / `R` | Start Crash Logs Scan  |
| `F6` / `G` | Start Game Files Scan  |
| `F7` / `P` | Toggle Papyrus Monitor |

### Output Viewer

| Key         | Action               |
|-------------|----------------------|
| `↑`         | Scroll up one line   |
| `↓`         | Scroll down one line |
| `Page Up`   | Scroll up one page   |
| `Page Down` | Scroll down one page |
| `Home`      | Scroll to top        |
| `End`       | Scroll to bottom     |
| `/`         | Open search          |
| `Ctrl+L`    | Clear output         |

### Folder Selector (When Focused)

| Key      | Action                  |
|----------|-------------------------|
| `Enter`  | Edit path (opens input) |
| `Ctrl+B` | Browse for folder       |
| `Esc`    | Cancel editing          |

### Settings Screen

| Key     | Action            |
|---------|-------------------|
| `Space` | Toggle checkbox   |
| `Enter` | Confirm and save  |
| `Esc`   | Cancel and return |

---

## Features

### 1. Crash Log Scanning

**How to Use:**

1. Set staging mods folder
2. Press `F5` or `R`
3. View real-time progress in output viewer
4. Review suspects list when complete

**Output:**

```
Scanning crash logs...
[████████████████████████████████] 47/47 (100%) - 2.3s

Results:
  Scanned: 47 logs
  Patterns matched: 234
  FormIDs resolved: 1,842
  Suspects identified: 12

Top suspects:
  1. SomePlugin.esp (18 occurrences)
  2. AnotherMod.esl (12 occurrences)
```

### 2. Game Files Scanning

**How to Use:**

1. Press `F6` or `G`
2. Wait for scan to complete
3. Review file integrity results

**Purpose**: Verify game files for corruption or missing entries

### 3. Papyrus Monitor

**How to Use:**

1. Press `F7` or `P` to toggle
2. View real-time Papyrus log entries
3. Press `F7` or `P` again to stop

**Features:**

- Real-time log streaming
- Automatic scrolling
- Stack trace parsing
- Error highlighting

**Output:**

```
[Papyrus Monitor Active]
[2024-01-15 14:23:45] [INFO] Script initialized: MyScript
[2024-01-15 14:23:46] [WARN] Property not found: MyProperty
[2024-01-15 14:23:47] [ERROR] Stack dump:
  Frame 0: MyScript.OnInit()
  Frame 1: ObjectReference.OnCellAttach()
```

### 4. Folder Selection

**Staging Mods Folder:**

- Required for Mod Organizer 2 users
- Points to MO2's mods directory
- Used for mod-specific analysis

**Custom Scan Folder:**

- Optional additional crash logs directory
- Useful for archived logs
- Scanned in addition to default location

**Path Validation:**

- **Green**: Path exists and is valid
- **Red**: Path doesn't exist or is invalid
- **Yellow**: Currently editing

### 5. Search

**How to Use:**

1. Press `/` in output viewer
2. Type search query
3. Press `Enter` to search
4. Use `N` for next match, `Shift+N` for previous

**Features:**

- Case-insensitive search
- Regex support (advanced)
- Highlight matches

### 6. Settings Management

**Access:** Press `Ctrl+O`

**Available Settings:**

- FCX Mode
- Show FormID Values
- Statistical Logging
- Move Unsolved Logs
- Simplify Logs
- Update Check

**Persistence:** The TUI, GUI, CLI, Node, and Python interfaces share the canonical nested `CLASSIC Settings.yaml` store at the CLASSIC root. TUI path and presentation saves are explicit all-or-nothing updates that preserve unknown entries and refuse revision conflicts. `Ctrl+O` presents degraded reads, required migrations, and the explicit verified import for a former TUI `state.json`.

---

## Settings

### Settings Screen Layout

```
┌──────────────────────────────────────┐
│ CLASSIC Settings                     │
├──────────────────────────────────────┤
│                                      │
│ [X] FCX Mode                         │
│ [ ] Show FormID Values               │
│ [X] Statistical Logging              │
│ [ ] Move Unsolved Logs               │
│ [ ] Simplify Logs                    │
│ [X] Check for Updates                │
│                                      │
├──────────────────────────────────────┤
│ [ Save (Enter) ]  [ Cancel (Esc) ]  │
└──────────────────────────────────────┘
```

### Setting Descriptions

| Setting                 | Description                          | Default |
|-------------------------|--------------------------------------|---------|
| **FCX Mode**            | Enable enhanced FormID analysis      | Off     |
| **Show FormID Values**  | Display hex FormID values in output  | Off     |
| **Statistical Logging** | Generate detailed statistics         | On      |
| **Move Unsolved Logs**  | Move unsolved crashes to subfolder   | Off     |
| **Simplify Logs**       | Reduce output detail (may lose info) | Off     |
| **Check for Updates**   | Check for CLASSIC updates on startup | On      |

---

## Troubleshooting

### Issue: TUI doesn't display correctly

**Symptoms:**

- Garbled text
- Missing borders
- Wrong colors

**Solutions:**

1. **Check terminal compatibility:**
   ```bash
   echo $TERM
   # Should show: xterm-256color, screen-256color, etc.
   ```

2. **Set 256-color mode:**
   ```bash
   export TERM=xterm-256color
   ClassicLib-rs/ui-applications/classic-tui
   ```

3. **Try different terminal:**
    - Windows: Windows Terminal (recommended), ConEmu, Alacritty
    - Linux: GNOME Terminal, Konsole, Alacritty
    - macOS: iTerm2, Alacritty

### Issue: Keyboard shortcuts not working

**Possible Causes:**

1. **Terminal intercepts keys:**
    - Some terminals capture F-keys for own use
    - Check terminal settings to disable intercepting

2. **SSH session:**
    - F-keys might not transmit over SSH
    - Use letter alternatives: `R`, `G`, `P` instead of F5, F6, F7

3. **tmux/screen:**
    - Add to `.tmux.conf`:
      ```
      set-window-option -g xterm-keys on
      ```

### Issue: Slow rendering or flickering

**Solutions:**

1. **Reduce terminal font size:**
    - Smaller terminal = less text to render
    - Recommended: 120x40 or smaller

2. **Disable transparency:**
    - Terminal transparency causes re-renders
    - Use solid background color

3. **Check system resources:**
   ```bash
   # Check CPU usage
   top
   # Should be low (<5%) when idle
   ```

### Issue: Output viewer not scrolling

**Check:**

1. Focus is on output viewer (Tab to navigate)
2. There is content to scroll
3. Try `Home`/`End` to verify scrolling works

### Issue: Path validation shows red despite valid path

**Solutions:**

1. **Check path format:**
    - Windows: `C:\Users\Name\Documents`
    - Linux/macOS: `/home/user/documents`

2. **Verify path exists:**
   ```bash
   # Windows
   dir "C:\MO2\mods"

   # Linux/macOS
   ls -la /path/to/folder
   ```

3. **Check permissions:**
    - Ensure read access to the directory

---

## Terminal Compatibility

### Fully Supported

✅ **Windows:**

- Windows Terminal (Recommended)
- ConEmu
- Alacritty
- Cmder

✅ **Linux:**

- GNOME Terminal
- Konsole
- Alacritty
- kitty
- Terminator

✅ **macOS:**

- iTerm2 (Recommended)
- Alacritty
- Terminal.app

### Partially Supported

⚠️ **Windows:**

- PowerShell (basic colors only)
- CMD (limited Unicode support)

### Not Supported

❌ **All Platforms:**

- Windows XP/Vista CMD
- Very old terminal emulators
- Terminals without ANSI support

### Terminal Feature Requirements

| Feature           | Required For                  |
|-------------------|-------------------------------|
| 256-color support | Full color scheme             |
| Unicode support   | Box-drawing characters        |
| Mouse support     | Click interactions (optional) |
| Alt screen buffer | Clean exit without scroll     |

### Testing Your Terminal

Run this test to verify compatibility:

```bash
# Test colors
printf "\e[31mRed\e[0m \e[32mGreen\e[0m \e[34mBlue\e[0m\n"

# Test Unicode
echo "┌─┐"
echo "│X│"
echo "└─┘"

# Test cursor movement
printf "\e[2J\e[H"
echo "Cursor at top-left"
```

---

## Performance Tips

### 1. Terminal Size

**Recommended:** 120 columns × 40 rows

```bash
# Check current size
tput cols && tput lines

# Resize (if supported)
printf '\e[8;40;120t'
```

**Why:** Smaller terminals render faster

### 2. Font Selection

**Recommended Fonts:**

- Fira Code
- JetBrains Mono
- Cascadia Code
- Consolas (Windows)

**Features:**

- Monospaced (required)
- Good Unicode coverage
- Ligatures (optional, looks nice)

### 3. Color Scheme

**Recommended:** Dark backgrounds

- Lighter on eyes
- Better contrast
- Faster rendering (depends on terminal)

### 4. SSH Performance

**For remote sessions:**

```bash
# Enable compression
ssh -C user@host ClassicLib-rs/ui-applications/classic-tui

# Use multiplexing
ssh -o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h:%p user@host
```

---

## Advanced Usage

### Running in tmux/screen

**tmux:**

```bash
# Create session
tmux new -s classic

# Launch CLASSIC
ClassicLib-rs/ui-applications/classic-tui

# Detach: Ctrl+B, D
# Reattach: tmux attach -t classic
```

**screen:**

```bash
# Create session
screen -S classic

# Launch CLASSIC
ClassicLib-rs/ui-applications/classic-tui

# Detach: Ctrl+A, D
# Reattach: screen -r classic
```

### SSH X11 Forwarding

Not needed! CLASSIC TUI works over plain SSH without X11.

```bash
# Just SSH normally
ssh user@server
ClassicLib-rs/ui-applications/classic-tui  # Works great!
```

### Automation

CLASSIC TUI is interactive, but you can script initial setup:

```bash
# Configure via YAML before launching TUI.
# Put the file at the resolved CLASSIC root (the directory containing CLASSIC Data).
cat > "<CLASSIC root>/CLASSIC Settings.yaml" <<EOF
schema_version: "1.0"
CLASSIC_Settings:
  FCX Mode: true
  Show Statistics: true
  MODS Folder Path: "/path/to/mods"
EOF

ClassicLib-rs/ui-applications/classic-tui
```

---

## Getting Help

### Help Screen

Press `F1` in CLASSIC TUI to view built-in help with:

- Keyboard shortcuts
- Feature descriptions
- Quick tips

### Online Resources

- **Documentation**: https://github.com/evildarkarchon/CLASSIC-Fallout4/tree/main/docs
- **Issues**: https://github.com/evildarkarchon/CLASSIC-Fallout4/issues
- **Discord**: [CLASSIC Community](https://discord.gg/...)

---

## Changelog

### v0.1.0 (2025-10-10)

- Initial Rust TUI implementation
- 60 FPS rendering with Ratatui
- <100MB memory usage
- Full keyboard navigation
- Real-time Papyrus monitoring
- Cross-platform terminal support

---

**Enjoy your terminal experience!** ⌨️
