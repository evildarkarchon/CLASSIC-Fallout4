# CLASSIC-Fallout4 Project Overview

## Purpose
CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a Python desktop application that analyzes crash logs from Bethesda games, primarily Fallout 4 and Skyrim. It helps users identify the causes of game crashes by analyzing Buffout 4 and Crash Logger output files.

## Key Features
- Analyzes crash logs to identify problematic mods, settings, and errors
- Provides three interfaces: GUI (PySide6/Qt), TUI (Textual), and CLI
- Performs game file integrity checking
- Manages mod file backups and restoration
- Monitors Papyrus logs in real-time
- Includes ~250 different diagnostic checks
- Supports FormID database lookups for identifying mod conflicts

## Tech Stack
- **Language**: Python 3.12+
- **GUI Framework**: PySide6 (Qt bindings)
- **TUI Framework**: Textual (rich terminal UI)
- **Build System**: PyInstaller for Windows executables
- **Package Management**: Poetry
- **Testing**: pytest with pytest-asyncio, pytest-xdist
- **Async**: Heavy use of asyncio for performance
- **Configuration**: YAML files for settings and mod databases
- **Linting**: Ruff
- **Type Checking**: mypy, pyright

## Architecture Highlights
- **Async-First Design**: Core implementations are async with sync adapters for compatibility
- **Orchestrator Pattern**: Centralized coordination of log scanning operations
- **Message Handler System**: Abstracted output for GUI, TUI, and CLI modes
- **One-Class-Per-File**: Recently refactored for better maintainability
- **AsyncBridge Singleton**: Manages async operations in sync contexts efficiently
- **Performance Optimized**: Connection pooling, batch operations, concurrent I/O

## Entry Points
- `CLASSIC_Interface.py` - GUI application (main)
- `CLASSIC_TUI.py` - Terminal UI application
- `CLASSIC_ScanLogs.py` - CLI interface
- `CLASSIC_ScanGame.py` - Game integrity checker
