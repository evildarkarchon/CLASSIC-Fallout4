# CLASSIC Slint GUI

Pure Rust desktop GUI for CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) using the Slint framework with Microsoft Fluent Design System.

## Status: Phase 1 Complete ✅

Phase 1 (Project Setup & Fluent Design Foundation) has been successfully completed!

### Completed Features

- ✅ Complete project structure with modular organization
- ✅ Slint 1.13 framework integration (winit backend + Skia renderer)
- ✅ Comprehensive Fluent Design dark theme system
- ✅ Base Fluent components (FluentButton, FluentCard, FluentTabBar)
- ✅ Main window with 4-tab structure
- ✅ Window geometry persistence (saves size/position between sessions)
- ✅ Version injection from Cargo.toml
- ✅ Successful compilation with zero errors

### Architecture

**UI Framework**: Slint 1.13
- **Backend**: winit (native window management)
- **Renderer**: Skia (GPU-accelerated with software fallback)
- **Design System**: Microsoft Fluent Design (Windows 11 dark theme)

**Business Logic**: Uses existing `-core` crates for 10-150x performance
- `classic-shared` - Foundation (runtime, errors)
- `classic-yaml-core` - YAML operations
- `classic-database-core` - SQLite with connection pooling
- `classic-file-io-core` - File I/O, encoding detection, DDS parsing
- `classic-scanlog-core` - Log parsing, FormID analysis
- `classic-config-core` - Configuration management

## Building

```bash
# Build the GUI
cargo build -p classic-gui-slint

# Run the GUI
cargo run -p classic-gui-slint --bin classic-gui
```

## Fluent Design System

The GUI implements Microsoft's Fluent Design System with:

### Color Palette (WCAG AA Compliant)
- **Background**: #202020 (solid base)
- **Layers**: #2b2b2b, #323232, #3a3a3a (elevation)
- **Text**: #ffffff (primary, 15.09:1 contrast), #a0a0a0 (secondary, 5.85:1 contrast)
- **Accent**: #60cdff (Fluent blue)
- **Semantic**: Success (#2ded8a), Warning (#faa919), Error (#ed2d2d)

### Typography
- **Font Family**: Segoe UI Variable (Windows 11 standard)
- **Sizes**: 12px (small) → 14px (body) → 16-24px (headings)
- **Weights**: 400 (regular), 600 (semibold), 700 (bold)

### Spacing System (8px base unit)
- **xs**: 4px, **sm**: 8px, **md**: 16px, **lg**: 24px, **xl**: 32px

### Animations
- **Fast**: 150ms, **Normal**: 250ms, **Slow**: 350ms
- **Easing**: ease-in-out for smooth transitions

## Project Structure

```
classic-gui-slint/
├── src/
│   ├── main.rs              # Entry point with version injection
│   ├── geometry.rs          # Window geometry persistence
│   ├── handlers/            # Event handlers (future phases)
│   ├── models/              # Data models for UI bindings (future phases)
│   ├── async_bridge.rs      # Tokio/Slint integration (future phases)
│   └── styles/              # Style constants (future phases)
├── ui/
│   ├── main.slint           # Main window with tab structure
│   ├── styles/
│   │   └── fluent_dark.slint    # Complete Fluent Design theme
│   ├── components/
│   │   ├── fluent_button.slint  # Fluent-styled button
│   │   ├── fluent_card.slint    # Elevated card component
│   │   └── fluent_tab_bar.slint # Modern tab bar with accent underline
│   └── tabs/
│       ├── main_tab.slint       # Main options (Phase 2)
│       ├── backups_tab.slint    # File backup (Phase 4)
│       ├── articles_tab.slint   # Resources/links (Phase 5)
│       └── results_tab.slint    # Results viewer (Phase 6-7)
├── assets/
│   └── CLASSIC.ico          # Application icon
├── build.rs                 # Slint compilation script
├── Cargo.toml              # Dependencies and configuration
└── README.md               # This file
```

## Next Steps: Phase 2

Phase 2 will implement the Main Tab UI with:
- Folder selection components (Staging Mods, Custom Scan)
- Main scan buttons (Crash Logs, Game Files)
- Utility buttons (About, Help, Settings, etc.)
- Papyrus monitoring toggle (START/STOP with semantic colors)
- Complete Fluent styling with proper interactive states

## Performance Targets

| Operation | Target Time |
|-----------|-------------|
| UI Responsiveness | 120 FPS |
| Startup Time | 200-500ms |
| Memory Usage | 50-75 MB |
| Crash Log Scan | 200-300ms |
| Game File Scan | 500-1000ms |

## Features

### Completed (Phase 1)
- Modern Fluent Design dark theme
- Window geometry persistence
- Four-tab structure with smooth animations
- Type-safe Slint UI with Rust backend
- GPU-accelerated rendering

### Coming Soon
- Phase 2: Main tab functionality
- Phase 3: Scan operations integration
- Phase 4: Backup operations
- Phase 5: Articles/resources tab
- Phase 6-7: Results viewer with markdown rendering
- Phase 8: Settings and dialogs
- Phase 9-10: Polish, testing, and release
