# CLASSIC CLI User Guide

**Version:** 8.0.0
**Platform:** Windows, Linux, macOS
**Target Users:** Power users, scripters, automation enthusiasts

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Command-Line Options](#command-line-options)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [Output Format](#output-format)
8. [Performance Tips](#performance-tips)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

CLASSIC CLI is a high-performance command-line interface for analyzing Fallout 4 and Skyrim crash logs. Built in Rust,
it offers:

- **🚀 Fast startup**: <500ms cold start (vs 2-3s Python)
- **⚡ High performance**: 10-150x faster crash log analysis
- **🔄 Scriptable**: Perfect for automation and batch processing
- **📦 Single binary**: No dependencies, just run the executable

### When to Use CLI vs TUI vs GUI

- **CLI**: Automation, scripting, CI/CD, batch processing
- **TUI**: Interactive terminal use, SSH sessions, server environments
- **GUI**: Visual exploration, first-time users, settings management

---

## Installation

### Method 1: Download Pre-built Binary (Recommended)

1. Download `rust/ui-applications/classic-cli.exe` from the [releases page](https://github.com/evildarkarchon/CLASSIC-Fallout4/releases)
2. Place in a directory of your choice
3. (Optional) Add to PATH for system-wide access

### Method 2: Install via Cargo

```bash
cargo install --git https://github.com/evildarkarchon/CLASSIC-Fallout4 rust/ui-applications/classic-cli
```

### Verification

```bash
rust/ui-applications/classic-cli --version
# Output: rust/ui-applications/classic-cli 8.0.0
```

---

## Quick Start

### Basic Scan (Default Settings)

```bash
rust/ui-applications/classic-cli
```

This will:

1. Load configuration from `CLASSIC Settings.yaml`
2. Scan default crash logs directory
3. Display results and save reports

### First-Time Setup

On first run, CLASSIC will:

- Create `CLASSIC Settings.yaml` with default settings
- Auto-detect your game installation
- Scan for crash logs in the default location

---

## Command-Line Options

### General Options

```bash
rust/ui-applications/classic-cli [OPTIONS]
```

| Option              | Type | Description                                  | Default |
|---------------------|------|----------------------------------------------|---------|
| `--fcx-mode`        | flag | Enable FCX mode for enhanced FormID analysis | `false` |
| `--show-fid-values` | flag | Show FormID hexadecimal values in output     | `false` |
| `--stat-logging`    | flag | Enable statistical logging                   | `false` |
| `--move-unsolved`   | flag | Move unsolved logs to separate folder        | `false` |
| `--simplify-logs`   | flag | Simplify log output (may remove info)        | `false` |

### Path Options

| Option               | Argument | Description                               |
|----------------------|----------|-------------------------------------------|
| `--ini-path`         | `<PATH>` | Path to INI folder                        |
| `--scan-path`        | `<PATH>` | Path to custom scan directory             |
| `--mods-folder-path` | `<PATH>` | Path to mods folder (for Mod Organizer 2) |

### Help and Version

```bash
rust/ui-applications/classic-cli --help       # Show all options
rust/ui-applications/classic-cli --version    # Show version
```

---

## Configuration

### Configuration File Location

**Windows:**

```
C:\Users\<YourName>\Documents\My Games\Fallout4\CLASSIC Settings.yaml
```

**Linux/macOS:**

```
~/.local/share/CLASSIC/CLASSIC Settings.yaml
```

### Configuration Priority

Settings are applied in this order (later overrides earlier):

1. Default values
2. Configuration file (`CLASSIC Settings.yaml`)
3. Command-line arguments (highest priority)

### Sample Configuration

```yaml
fcx_mode: false
show_formid_values: false
stat_logging: true
move_unsolved_logs: false
simplify_logs: false
update_check: true

paths:
  ini_folder: "C:\\Users\\Name\\Documents\\My Games\\Fallout4"
  scan_custom: null
  mods_folder: "C:\\MO2\\mods"
  game_root: "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Fallout 4"
```

### Editing Configuration

**Option 1: Manual Edit**

```bash
notepad "C:\Users\Name\Documents\My Games\Fallout4\CLASSIC Settings.yaml"
```

**Option 2: CLI Override (Temporary)**

```bash
rust/ui-applications/classic-cli --fcx-mode --show-fid-values
```

This won't modify the YAML file; settings apply only to this run.

---

## Usage Examples

### Example 1: Basic Scan with Default Settings

```bash
rust/ui-applications/classic-cli
```

**Output:**

```
CLASSIC v8.0.0 - Crash Log Auto Scanner
========================================

Initializing scan...
  ✓ Loaded configuration from CLASSIC Settings.yaml
  ✓ Found 47 crash logs in scan directory
  ✓ FormID database loaded (125,347 entries)

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
  3. ProblemMod.esp (8 occurrences)

Reports saved to: C:\...\Crash Logs\Reports\
```

### Example 2: Custom Scan Directory

```bash
rust/ui-applications/classic-cli --scan-path "D:\Additional Crash Logs"
```

### Example 3: Full Analysis with All Options

```bash
rust/ui-applications/classic-cli \
  --fcx-mode \
  --show-fid-values \
  --stat-logging \
  --move-unsolved \
  --mods-folder-path "C:\MO2\mods"
```

### Example 4: Batch Processing (PowerShell)

```powershell
# Scan multiple log directories
$dirs = @(
    "C:\Logs\Set1",
    "C:\Logs\Set2",
    "C:\Logs\Set3"
)

foreach ($dir in $dirs) {
    Write-Host "Scanning: $dir"
    rust/ui-applications/classic-cli --scan-path $dir --stat-logging
}
```

### Example 5: CI/CD Integration

```bash
#!/bin/bash
# Run CLASSIC scan and check for errors

rust/ui-applications/classic-cli --stat-logging --fcx-mode
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "CLASSIC scan failed with exit code $EXIT_CODE"
    exit 1
fi

echo "CLASSIC scan completed successfully"
```

### Example 6: Generate Statistics Report

```bash
rust/ui-applications/classic-cli --stat-logging > scan_results.txt
```

---

## Output Format

### Console Output Structure

```
CLASSIC v8.0.0 - Crash Log Auto Scanner
========================================

[INITIALIZATION PHASE]
  ✓ Configuration loaded
  ✓ Crash logs found: N
  ✓ Database loaded: N entries

[SCANNING PHASE]
  Progress bar with:
  - Current file count / Total files
  - Percentage
  - Elapsed time

[RESULTS PHASE]
  Statistics:
  - Scanned logs count
  - Patterns matched count
  - FormIDs resolved count
  - Suspects identified count

  Top Suspects:
  - Ranked list of problematic plugins
  - Occurrence counts

  Report Location:
  - Path to generated reports
```

### Exit Codes

| Code | Meaning                                          |
|------|--------------------------------------------------|
| `0`  | Success - scan completed without errors          |
| `1`  | Error - configuration error or file access issue |
| `2`  | Error - no crash logs found                      |
| `3`  | Error - database loading failed                  |

### Report Files

CLASSIC generates these files in the crash logs directory:

```
Crash Logs/
├── Reports/
│   ├── CLASSIC_Analysis_YYYY-MM-DD_HH-MM-SS.txt
│   ├── Suspects_Summary.txt
│   └── FormID_Analysis.txt (if --show-fid-values)
└── Unsolved/ (if --move-unsolved)
    └── [unsolved crash logs]
```

---

## Performance Tips

### 1. Use SSD for Crash Logs

**Impact**: 2-3x faster scan times

Place crash logs on an SSD rather than HDD for optimal I/O performance.

### 2. Batch Processing with Parallelization

CLASSIC automatically uses all CPU cores. For batch processing:

```bash
# Good: Sequential processing (CLASSIC handles parallelization)
rust/ui-applications/classic-cli --scan-path "Logs1"
rust/ui-applications/classic-cli --scan-path "Logs2"

# Not needed: Manual parallelization
# CLASSIC already parallelizes within each scan
```

### 3. Disable Unnecessary Features

```bash
# Faster scan (minimal output)
rust/ui-applications/classic-cli --simplify-logs

# Full analysis (more time)
rust/ui-applications/classic-cli --fcx-mode --show-fid-values --stat-logging
```

### 4. Regular Database Updates

Keep your FormID database updated for faster lookups:

- Database is automatically maintained
- Rebuilds on game updates

---

## Troubleshooting

### Issue: "No crash logs found"

**Cause**: Incorrect scan directory or no crash logs present

**Solutions:**

1. Verify crash logs directory:
   ```bash
   rust/ui-applications/classic-cli --scan-path "C:\Users\Name\Documents\My Games\Fallout4\F4SE"
   ```

2. Check if crash logs exist:
   ```bash
   dir "C:\Users\Name\Documents\My Games\Fallout4\F4SE\crash-*.log"
   ```

### Issue: "Failed to load configuration"

**Cause**: Corrupted or invalid YAML file

**Solutions:**

1. Delete configuration and let CLASSIC recreate it:
   ```bash
   del "CLASSIC Settings.yaml"
   rust/ui-applications/classic-cli  # Creates new config
   ```

2. Validate YAML syntax online: https://www.yamllint.com/

### Issue: "Database loading failed"

**Cause**: Missing or corrupted FormID database

**Solutions:**

1. CLASSIC will auto-rebuild the database
2. Ensure game is installed correctly
3. Check game root path in configuration

### Issue: Slow performance

**Possible Causes & Solutions:**

1. **HDD instead of SSD**
    - Move crash logs to SSD
    - Or adjust expectations (HDD is slower)

2. **Antivirus interference**
    - Add CLASSIC to antivirus exclusions
    - Temporarily disable real-time scanning

3. **Thousands of crash logs**
    - Normal for large scans
    - Consider archiving old logs

### Issue: "Permission denied" errors

**Cause**: Insufficient file system permissions

**Solutions:**

1. Run as administrator (Windows):
   ```bash
   # Right-click CMD/PowerShell → "Run as administrator"
   rust/ui-applications/classic-cli
   ```

2. Check folder permissions:
    - Ensure read access to crash logs directory
    - Ensure write access to reports directory

### Issue: CLI arguments not working

**Check:**

1. Syntax is correct:
   ```bash
   # Correct
   rust/ui-applications/classic-cli --fcx-mode

   # Incorrect (missing dashes)
   rust/ui-applications/classic-cli fcx-mode
   ```

2. Boolean flags don't need values:
   ```bash
   # Correct
   rust/ui-applications/classic-cli --fcx-mode

   # Incorrect
   rust/ui-applications/classic-cli --fcx-mode true
   ```

3. Paths with spaces need quotes:
   ```bash
   # Correct
   rust/ui-applications/classic-cli --scan-path "C:\My Logs"

   # Incorrect (will fail)
   rust/ui-applications/classic-cli --scan-path C:\My Logs
   ```

---

## Advanced Usage

### Scripting with CLASSIC

**PowerShell Example:**

```powershell
# Monitor new crashes and analyze automatically
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = "C:\...\Fallout4\F4SE"
$watcher.Filter = "crash-*.log"
$watcher.EnableRaisingEvents = $true

Register-ObjectEvent $watcher "Created" -Action {
    Write-Host "New crash detected, analyzing..."
    rust/ui-applications/classic-cli --fcx-mode
}
```

**Bash Example:**

```bash
#!/bin/bash
# Daily crash log analysis cron job

SCAN_DIR="/mnt/games/Fallout4/crashes"
ARCHIVE_DIR="/mnt/archives/crash_reports"

# Run scan
rust/ui-applications/classic-cli --scan-path "$SCAN_DIR" --stat-logging > daily_report.txt

# Archive reports
DATE=$(date +%Y-%m-%d)
mkdir -p "$ARCHIVE_DIR/$DATE"
cp -r "$SCAN_DIR/Reports" "$ARCHIVE_DIR/$DATE/"
```

---

## Getting Help

- **Documentation**: https://github.com/evildarkarchon/CLASSIC-Fallout4/tree/main/docs
- **Issues**: https://github.com/evildarkarchon/CLASSIC-Fallout4/issues
- **Discord**: [CLASSIC Community](https://discord.gg/...)

---

## Changelog

### v8.0.0 (2025-10-10)

- Initial Rust CLI implementation
- <500ms startup time
- 10-150x performance improvements
- Single-binary distribution
- Full feature parity with Python version

---

**Happy crash log hunting!** 🚀
