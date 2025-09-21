# uv Package Caching Guide for Local Development

## Overview

uv provides intelligent caching that makes dependency installation 10-100x faster than traditional tools like pip or Poetry. This guide covers practical caching usage for single-developer local development.

## How uv Caching Works

### Cache Location

uv stores all downloaded packages in a global cache:
- **Windows**: `%LOCALAPPDATA%\uv\cache` (e.g., `C:\Users\YourName\AppData\Local\uv\cache`)
- **macOS/Linux**: `~/.cache/uv`

This cache is shared across all your Python projects, so installing PySide6 once caches it for all projects.

## Setting Up for Optimal Performance

### First-Time Project Setup

```bash
# Clone the project
git clone https://github.com/your-username/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4

# Install uv (if not already installed)
# Windows PowerShell:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Do a complete install to populate cache
uv sync --all-extras

# First install: ~45 seconds
# Future installs: ~2 seconds
```

### Speed Optimizations

Add these to your environment variables for faster operations:

**Windows (System Properties → Environment Variables):**
```
UV_LINK_MODE=hardlink
UV_CONCURRENT_DOWNLOADS=10
```

**macOS/Linux (add to ~/.bashrc or ~/.zshrc):**
```bash
export UV_LINK_MODE=hardlink
export UV_CONCURRENT_DOWNLOADS=10
```

## Daily Development Workflow

### Common Commands

```bash
# Install/sync dependencies (uses cache, very fast)
uv sync

# Run the application
uv run python CLASSIC_Interface.py

# Add a new package
uv add requests  # Caches for future use

# Remove a package
uv remove requests

# Update all dependencies
uv lock --upgrade
uv sync
```

### Working Offline

Once packages are cached, you can work without internet:

```bash
# Work offline using only cached packages
export UV_OFFLINE=true  # or set UV_OFFLINE=true on Windows
uv sync
```

## Managing Cache Storage

### Check Cache Size

```bash
# View cache statistics
uv cache status

# Windows: Check folder size manually
# Open File Explorer and navigate to %LOCALAPPDATA%\uv\cache

# macOS/Linux: Check size
du -sh ~/.cache/uv
```

### Clean Up Cache (Monthly Maintenance)

```bash
# Remove packages not used in 30 days
uv cache prune --days 30

# Or completely clear cache if needed (rarely necessary)
uv cache clean
```

## Troubleshooting

### Problem: Package Won't Install

```bash
# Clear cache for specific package and retry
uv cache clean pyside6
uv add --refresh pyside6
```

### Problem: Strange Errors After Update

```bash
# Force fresh environment
rm -rf .venv  # Windows: rmdir /s .venv
uv sync --refresh
```

### Problem: Cache Using Too Much Space

The cache typically uses 1-3GB. To reduce:

```bash
# Remove old packages
uv cache prune --days 14

# Or clear everything and start fresh
uv cache clean
```

## Performance You Can Expect

After initial setup with cache populated:

| Operation | Time with Cache | Without Cache |
|-----------|----------------|---------------|
| Create virtual environment | ~1 second | 12+ seconds |
| Install all dependencies | ~2 seconds | 45+ seconds |
| Add single package | <1 second | 8+ seconds |
| Switch Python versions | ~3 seconds | 15+ seconds |

## Tips for Best Performance

1. **Keep uv Updated**
   ```bash
   # Update uv itself periodically
   pip install --upgrade uv
   ```

2. **Use Lock Files**
   ```bash
   # Always commit uv.lock to git
   git add uv.lock
   git commit -m "Update dependencies"
   ```

3. **Batch Operations**
   ```bash
   # Add multiple packages at once (more efficient)
   uv add pytest ruff mypy

   # Instead of one at a time
   ```

4. **Set Up Your IDE**
   - Point to `.venv/Scripts/python.exe` (Windows)
   - Or `.venv/bin/python` (macOS/Linux)
   - The virtual environment is recreated almost instantly thanks to cache

## Quick Reference

### Essential Commands
```bash
uv sync                  # Install dependencies
uv run python script.py  # Run Python scripts
uv add package          # Add dependency
uv remove package       # Remove dependency
uv lock --upgrade       # Update all packages
uv cache status         # Check cache info
uv cache prune          # Clean old cache entries
```

### Environment Variables (Optional)
```bash
UV_LINK_MODE=hardlink           # Faster on same drive
UV_CONCURRENT_DOWNLOADS=10      # Parallel downloads
UV_CACHE_DIR=D:\uv-cache       # Custom cache location
UV_OFFLINE=true                # Work offline
```

## Summary

With uv's caching:
- **First install**: ~45 seconds to download and cache everything
- **Every install after**: ~2 seconds using cache
- **Storage used**: 1-3GB for typical projects
- **Maintenance**: Run `uv cache prune` monthly

The cache works automatically - you don't need to think about it. Just enjoy the speed!
