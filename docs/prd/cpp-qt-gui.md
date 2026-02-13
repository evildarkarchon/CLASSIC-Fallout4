# PRD: C++ Qt GUI for CLASSIC

**Version**: 1.0
**Date**: 2026-02-12
**Status**: Draft
**Goal**: Replace the PySide6 Python GUI with a native C++ Qt 6 Widgets GUI, consuming Rust business logic via CXX FFI, managed with vcpkg and CMake

---

## 1. Executive Summary

CLASSIC currently has three GUI implementations: PySide6 (Python, production), Textual TUI (Python, production), and Slint (Rust, v9.0.0). This PRD defines a fourth: a **native C++ Qt 6 Widgets** application that provides the same functionality as the PySide6 GUI while consuming the existing Rust business logic crates directly via CXX FFI bindings.

### Why C++ Qt?

- **Native performance**: No Python interpreter overhead, no GIL constraints
- **Qt maturity**: Decades of stability for desktop widget-based applications
- **Direct Rust integration**: CXX provides zero-overhead, type-safe FFI without an intermediate Python layer
- **Single binary deployment**: Qt + Rust compiled to one distributable package
- **Industry standard**: Qt is the dominant framework for cross-platform C++ desktop apps

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI Framework | Qt 6 Widgets (not QML) | Text-heavy crash log scanner, native desktop look, smaller footprint |
| Package Manager | vcpkg (manifest mode) | CMake-native, Microsoft-backed, excellent Windows support |
| Build System | CMake + Corrosion | Industry standard for C++; Corrosion imports Rust crates into CMake |
| Rust FFI | CXX crate | Compile-time type safety on both sides, rich type mapping, zero overhead |
| C++ Standard | C++20 | Consistent with existing classic-cli, enables ranges/concepts/format |
| Compiler | MSVC | Primary Qt/Windows target, best tooling, vcpkg default |
| Linking | Dynamic (`x64-windows`) | LGPL-compatible, faster builds, standard deployment |
| Qt Version | 6.10.x | Latest release, newest features and improvements |
| UI Layout | Qt Designer `.ui` files | Visual editing, separation of layout from logic, easier iteration than pure-code layouts |

### Architecture Overview

```
+---------------------+       +------------------------+       +-------------------+
|   C++ Qt Widgets    |  CXX  |  classic-cpp-bridge    |       |  Rust Business    |
|   GUI Application   | <---> |  (staticlib + headers) | <---> |  Logic Crates     |
|                     |       |  #[cxx::bridge]        |       |  (~20 crates)     |
+---------------------+       +------------------------+       +-------------------+
         |                              |                              |
    Qt6::Widgets                   Corrosion                    Cargo workspace
    Qt6::Network                 (CMake import)                  rust/Cargo.toml
         |                              |                              |
    vcpkg.json                   CMakeLists.txt                  build.rs
```

---

## 2. Current PySide6 GUI Architecture (Feature Parity Target)

The C++ Qt GUI must replicate all functionality of the existing PySide6 GUI. The PySide6 GUI is the reference for **layout, tabs, dialogs, and feature set**. However, for **markdown/report rendering**, the Slint GUI's clean minimalist style is the design reference (see §2.8). The Slint GUI may also be referenced for Rust API usage patterns. This section catalogs every component.

### 2.1 Window Structure

**Main Window** (650x580 initial, 550x580 minimum):
- Title: `"CLASSIC {version}"` from YAML settings
- Icon: `CLASSIC Data/graphics/CLASSIC.ico`
- Dark mode stylesheet (bg `#2b2b2b`, accent `#0078d4`, font "Segoe UI" 13px)
- Central `QTabWidget` with 4 tabs

### 2.2 Tab Layout

#### Tab 0: MAIN OPTIONS
- **Folder inputs**: "Staging Mods Folder" and "Custom Scan Folder" (QLineEdit + Browse button each)
- **Primary action buttons**: "SCAN CRASH LOGS" and "SCAN GAME FILES" (large, 48px height, bold 17px)
- **Bottom row 1**: ABOUT, HELP, SETTINGS, OPEN CRASH LOGS, CHECK UPDATES
- **Bottom row 2**: "START PAPYRUS MONITORING" (checkable toggle, green/red), EXIT

#### Tab 1: FILE BACKUP
- Instruction labels (BACKUP/RESTORE/REMOVE)
- 4 backup sections (XSE, ReShade, Vulkan, ENB), each with BACKUP/RESTORE/REMOVE buttons
- "OPEN CLASSIC BACKUPS" button at bottom

#### Tab 2: ARTICLES
- "USEFUL RESOURCES & LINKS" header
- 3x3 grid of buttons linking to external URLs (Nexus Mods, GitHub, etc.)

#### Tab 3: RESULTS
- Horizontal splitter (30%/70%)
- **Left panel**: `ReportListWidget` (custom QListWidget with search, status coloring) + button bar (Refresh, Delete, Open Folder)
- **Right panel**: `ReportMetadataWidget` (date/issues/size) + `MarkdownViewer` (QTextBrowser with custom CSS) + toolbar (Copy, zoom controls)

### 2.3 Dialogs

| Dialog | Purpose | Key Widgets |
|--------|---------|-------------|
| SettingsDialog | App configuration (modal) | QTabWidget with 4 sub-tabs: General, Scanning, Paths, Updates |
| CustomAboutDialog | Version/credits info | Icon + text + Close |
| CustomErrorDialog | Error display | Icon + message + QTextEdit details + Copy/OK |
| PapyrusMonitorDialog | Live Papyrus stats | QGridLayout stats + status indicators + Stop |
| ManualPathDialog | Path selection | QLineEdit + Browse + OK/Cancel |

### 2.4 Settings Sub-tabs

1. **General**: Game Version dropdown (populated from VersionRegistry)
2. **Scanning**: Checkboxes (FCX Mode, Simplify Logs, Show FID Values, Move Invalid Logs, Auto-Switch Results) + Max Concurrent Scans spinbox
3. **Paths**: INI Folder Path (LineEdit + Browse/Reset) + FormID Databases (QListWidget + Add/Remove)
4. **Updates**: Update Check checkbox + "Check for Updates Now" button

### 2.5 Custom Widgets

| Widget | Base Class | Purpose |
|--------|-----------|---------|
| ReportListWidget | QListWidget | Report list with search filter, status-based coloring (green=solved, red=unsolved, yellow=incomplete), timestamp extraction |
| MarkdownViewer | QTextBrowser | Renders markdown with Slint-style clean dark theme (see §2.8), zoom controls |
| ReportMetadataWidget | QGroupBox | Shows date, file size, issue count extracted from report content |

### 2.6 Threading Model

| Thread Type | Worker | Operations |
|-------------|--------|------------|
| CRASH_LOGS_SCAN | CrashLogsScanWorker | `OrchestratorCore::process_logs_batch()` |
| GAME_FILES_SCAN | GameFilesScanWorker | Game file scanning + combined results |
| UPDATE_CHECK | UpdateCheckWorker | `GithubClient::has_update()` |
| PAPYRUS_MONITOR | PapyrusMonitorWorker | 1-second polling loop |

Pattern: QThread + Worker Object (moveToThread), signals for progress/completion/error.

### 2.7 Cross-Cutting Concerns

- **SignalHub**: Central Qt signal routing (20+ signals for scan lifecycle, UI state, monitoring)
- **FeatureContext**: Dependency injection container (main_window, thread_manager, signal_hub, ui_widgets)
- **File watching**: QFileSystemWatcher on crash logs directory, paused during scans
- **Window geometry**: Saved/restored via YAML settings
- **Stylesheet**: Global dark mode with per-widget overrides

### 2.8 Markdown Rendering Style (Slint GUI Reference)

The markdown/report viewer must follow the **Slint GUI's clean minimalist rendering style**, not the PySide6 GUI's VS Code-like colored-box approach. The Slint GUI uses `pulldown-cmark` for parsing and renders blocks with a simple, restrained color palette.

#### Design Principles
- **Minimal color**: White/light text on dark backgrounds. No teal headers, no orange inline code, no colored semantic boxes
- **Block-level clarity**: Clear visual hierarchy through font size and weight, not color-coded containers
- **Clean separators**: Thin horizontal rules (`#555555`, 1px) between sections
- **Restrained backgrounds**: Only code blocks get a distinct background (`#2a2a2e`)

#### Element Styling Reference

| Element | Font Size | Weight | Background | Notes |
|---------|-----------|--------|------------|-------|
| H1 | 22px | 700 (bold) | none | Default text color, no border |
| H2 | 18px | 700 (bold) | none | Default text color, no border |
| H3 | 15px | 700 (bold) | none | Default text color, no border |
| Paragraph | 13px | 400 | none | Full inline bold/italic supported (unlike Slint) |
| Code block | 12px | 400 | `#2a2a2e` | Consolas, 4px border-radius, 8px padding |
| Inline code | 12px | 400 | `#2a2a2e` | Consolas, 3px border-radius, 2px 4px padding |
| Horizontal rule | — | — | `#555555` | 1px height |
| List item | 13px | 400 | none | Bullet markers: • (depth 1), ◦ (depth 2), ▪ (depth 3+); indent = depth × 16px |
| Blockquote | 13px | 400 | none | 3px left border bar (`#555555`), italic, 8px left spacing |

#### Differences from PySide6 (Do NOT replicate)
- ❌ Teal (`#4EC9B0`) colored headers
- ❌ Red-tinted suspect boxes (`#3c1414` background + `#f44336` border)
- ❌ Yellow-header found mod cards
- ❌ Blue-tinted info boxes
- ❌ Red-bordered error boxes
- ❌ Orange-brown inline code color (`#ce9178`)
- ❌ Alternating table row colors
- ❌ Custom regex preprocessing to wrap CLASSIC structures in `<div>` elements

#### Qt Improvements Over Slint
Since Qt's `QTextBrowser` supports full HTML/CSS inline formatting, the C++ GUI can improve on Slint's block-level-only limitation:
- ✅ Proper inline **bold** and *italic* within the same paragraph
- ✅ Inline `code` with monospace font and subtle background (not just backtick delimiters)
- ✅ Mixed formatting in list items

#### Markdown Parser
Use `pulldown-cmark` via the CXX bridge (already proven in the Slint GUI). The Rust side converts markdown to HTML, and the C++ side sets it on `QTextBrowser::setHtml()` wrapped in a minimal CSS stylesheet matching the table above. This avoids adding a C/C++ markdown library dependency.

---

## 3. Rust API Surface for C++ Bindings

### 3.1 Binding Scope

The C++ GUI needs access to the same Rust APIs currently consumed by the PySide6 GUI and Slint GUI. The CXX bridge crate will expose a curated subset organized by functional area.

### 3.2 Core APIs Required

#### Runtime & Infrastructure
```
classic-shared-core:
  get_runtime() -> &'static Runtime           // ONE RUNTIME RULE
  ClassicError enum (14 variants)              // Error hierarchy
  StringProcessor (intern, normalize, batch)   // String operations
  PathHandler (normalize, validate, join)      // Cached path ops
  PerformanceMetrics (record, query, clear)    // Perf monitoring
```

#### Configuration & Settings
```
classic-yaml-core:
  YamlOperations (load, save, get/set_setting) // YAML file I/O
  Batch get/set operations                     // Bulk settings
  Cache management                             // Clear, stats

classic-config-core:
  YamlDataCore (~30 fields from YAML DBs)      // Game config data
  YamlSource enum (path resolution)            // Config file locations
  PathConfig (game, docs, xse paths)           // Path settings
```

#### Crash Log Scanning (Primary Feature)
```
classic-scanlog-core:
  AnalysisConfig (game, vr_mode, 20+ fields)   // Scan configuration
  OrchestratorCore                              // Central coordinator
    .process_log(path) -> AnalysisResult        // Single log scan
    .process_logs_batch(paths) -> Vec<Result>    // Batch scanning
    .write_reports_batch(results, dir)          // Report output
  build_analysis_config_from_yaml()             // Config builder
  LogParser (segments, patterns, sections)      // Low-level parsing
  FormIDAnalyzerCore (extract, lookup, match)   // FormID analysis
  GpuDetector (GPU info extraction)             // Hardware detection
  PapyrusAnalyzer + PapyrusStats               // Papyrus monitoring
  detect_vr_log(), detect_mods_*               // Detection helpers
```

#### Database
```
classic-database-core:
  DatabasePool                                  // Connection pooling
    .initialize(db_paths)                       // Async init
    .get_entry(formid, plugin) -> Option<String> // Async lookup
    .get_entries_batch(entries) -> HashMap       // Async batch
    .close()                                    // Async cleanup
```

#### File I/O
```
classic-file-io-core:
  FileIOCore (read/write files, encoding detect) // Core file ops
  DDSAnalyzer (validate DDS textures)            // Texture validation
  BackupManager (create/restore/remove backups)  // Backup operations
  GameFilesManager (backup/restore/remove)       // Game file management
  LogCollector (collect crash logs)               // Log discovery
  calculate_similarity()                         // File comparison
```

#### Game Support
```
classic-version-registry-core:
  VersionRegistry (singleton, game versions)     // Version database
  GameVersion (parse, compare, distance)         // Version handling
  VersionInfo, CrashgenConfig, MatchResult       // Version types

classic-path-core:
  GamePathFinder (find/validate game path)       // Game detection
  DocsPathFinder (find/validate docs path)       // Docs detection
  DocumentsChecker (OneDrive, INI validation)    // Path checks

classic-xse-core:
  detect_xse_version(), is_xse_installed()       // XSE detection
  XseInfo, XseType                               // XSE types

classic-version-core:
  extract_pe_version(path)                       // PE file versions

classic-update-core:
  GithubClient (latest release, update check)    // GitHub API
```

#### Utilities
```
classic-registry-core:
  Global key-value store (get, set, clear)       // Runtime state
  Convenience: get_game(), is_vr_version(), etc. // Quick accessors

classic-constants-core:
  GameId, Fallout4Version, YamlFile enums        // Game constants

classic-message-core:
  Logger (info, warning, error, debug, trace)    // Logging
```

### 3.3 Binding Waves (Implementation Order)

| Wave | Crates | Enables |
|------|--------|---------|
| 1 - Foundation | classic-shared-core, classic-yaml-core, classic-config-core, classic-registry-core | Runtime init, settings load/save, config management |
| 2 - Scanning | classic-scanlog-core, classic-database-core | Crash log scanning (primary feature) |
| 3 - File I/O | classic-file-io-core, classic-scangame-core | Game file scanning, backups, log collection |
| 4 - Game Support | classic-path-core, classic-version-core, classic-xse-core, classic-version-registry-core, classic-constants-core | Game detection, version matching, XSE checks |
| 5 - Utilities | classic-update-core, classic-web-core, classic-message-core, classic-perf-core | Update checks, logging, performance monitoring |

---

## 4. Rust-C++ Interop Architecture

### 4.1 Approach: CXX + Corrosion

**CXX** (cxx.rs) is the primary FFI mechanism. A single `#[cxx::bridge]` Rust crate defines the entire C++ API surface.

**Why CXX over alternatives:**

| Approach | Verdict | Reason |
|----------|---------|--------|
| **CXX** | **Selected** | Compile-time safety both sides, rich types (String, Vec, Result, Box), zero overhead, mature (v1.0.194), used by KDE |
| cbindgen | Rejected | C-only types, manual memory management, no Result mapping, unsafe-heavy |
| autocxx | Rejected | Wrong direction (C++ -> Rust, not Rust -> C++), pre-1.0 |
| Plain C FFI | Rejected | Maximum manual effort, no type safety, error-prone |

**Corrosion** (corrosion-rs) imports the Rust staticlib into the CMake build system:
```cmake
FetchContent_Declare(Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.6
)
FetchContent_MakeAvailable(Corrosion)
corrosion_import_crate(MANIFEST_PATH rust/Cargo.toml CRATES classic-cpp-bridge)
target_link_libraries(ClassicGui PRIVATE classic-cpp-bridge)
```

### 4.2 Bridge Crate Architecture

A new Rust crate `classic-cpp-bridge` acts as the single FFI surface:

```
rust/
  cpp-bindings/
    classic-cpp-bridge/
      Cargo.toml          # [lib] crate-type = ["staticlib"]
      build.rs            # cxx-build generates C++ source
      src/
        lib.rs            # Top-level module, re-exports bridges
        runtime.rs        # Runtime init, shutdown
        yaml.rs           # YAML settings bridge
        config.rs         # Configuration bridge
        scanner.rs        # Crash log scanning bridge
        database.rs       # Database bridge
        files.rs          # File I/O bridge
        game.rs           # Game detection bridge
        types.rs          # Shared type definitions
```

### 4.3 CXX Bridge Patterns

#### Runtime Management
```rust
#[cxx::bridge(namespace = "classic")]
mod ffi {
    extern "Rust" {
        fn init_runtime();
        fn shutdown_runtime();
    }
}

fn init_runtime() {
    let _ = classic_shared::get_runtime();
}
```

#### Async Operations (Sync Wrappers)
```rust
#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    struct ScanResult {
        log_path: String,
        success: bool,
        report_lines: Vec<String>,
        error_message: String,
    }

    extern "Rust" {
        fn scan_log(path: &str) -> Result<ScanResult>;
        fn scan_logs_batch(paths: &[&str]) -> Result<Vec<ScanResult>>;
    }
}

fn scan_log(path: &str) -> Result<ScanResult, cxx::Exception> {
    classic_shared::get_runtime().block_on(async {
        let orchestrator = OrchestratorCore::new(config)?;
        let result = orchestrator.process_log(path.to_string()).await?;
        Ok(result.into())  // Convert to CXX-compatible struct
    })
}
```

#### Callback Pattern (for Progress Updates)
```rust
#[cxx::bridge(namespace = "classic::scanner")]
mod ffi {
    extern "C++" {
        include!("classic-gui-qt6-c++/src/core/scan_callback.h");
        type ScanCallback;
        fn on_progress(self: &ScanCallback, percent: f32, status: &str);
        fn on_complete(self: &ScanCallback, result: &ScanResult);
        fn on_error(self: &ScanCallback, message: &str);
    }

    extern "Rust" {
        fn scan_log_async(path: &str, callback: &ScanCallback);
    }
}
```

### 4.4 Type Mapping

| Rust Type | CXX Bridge Type | C++ Type | Qt Conversion |
|-----------|----------------|----------|---------------|
| `String` / `&str` | `rust::String` / `&str` | `rust::String` | `QString::fromUtf8(s.data(), s.size())` |
| `Vec<T>` | `rust::Vec<T>` | `rust::Vec<T>` | Iterate to `QVector<T>` or `QStringList` |
| `Result<T, E>` | `Result<T>` | C++ exception | `try/catch` in Qt worker |
| `bool`, `i32`, `f32`, etc. | Pass-through | Same | Direct use |
| `HashMap<K,V>` | Opaque type + accessors | Accessor methods | Build `QMap` via iteration |
| `Option<T>` | Encoded in struct or separate method | Nullable / sentinel | Check before use |
| Custom structs | Shared CXX struct | Generated C++ struct | Map to Qt model data |
| Custom enums | CXX `enum` (C-like) | `enum class` | Direct use |
| `PathBuf` | `String` | `std::string` | `QString::fromStdString()` |

### 4.5 String Bridge Helper

A thin C++ utility converts between `rust::String` and `QString`:

```cpp
// src/core/rust_qt_bridge.h
#pragma once
#include <QString>
#include "rust/cxx.h"

inline QString toQString(const rust::String& s) {
    return QString::fromUtf8(s.data(), static_cast<int>(s.size()));
}

inline QString toQString(rust::Str s) {
    return QString::fromUtf8(s.data(), static_cast<int>(s.size()));
}

inline rust::String toRustString(const QString& s) {
    auto utf8 = s.toUtf8();
    return rust::String(utf8.constData(), utf8.size());
}
```

### 4.6 Qt Event Loop Integration

For async operations that report progress, the Rust bridge spawns work on the Tokio runtime and uses a callback to notify Qt:

```
C++ (Qt Main Thread)           Rust (Tokio Runtime)
        |                              |
  Click "Scan" button                  |
        |                              |
  Create ScanCallback -------> scan_log_async(path, callback)
  (QObject subclass)                   |
        |                     get_runtime().spawn(async {
        |                       for each log:
  <-- callback.on_progress()      process_log(...)
        |                         callback.on_progress(%)
  Update QProgressBar              ...
        |                       callback.on_complete(result)
  <-- callback.on_complete()  })
        |                              |
  Display results                      |
```

The `ScanCallback` is a C++ QObject subclass that emits Qt signals from the callback methods. Since CXX callbacks run on the Tokio thread, the callback implementation must use `QMetaObject::invokeMethod(qApp, ...)` with `Qt::QueuedConnection` to marshal back to the Qt event loop thread.

---

## 5. Project Structure

### 5.1 Directory Layout

```
classic-gui-qt6-c++/                         # NEW: Top-level C++ project directory
  CMakeLists.txt                        # Root CMake: project(), find_package(), add_subdirectory()
  CMakePresets.json                     # Build presets (vcpkg toolchain, Ninja generator)
  vcpkg.json                           # Package manifest (qtbase, qttools)
  vcpkg-configuration.json             # Registry baseline
  src/
    CMakeLists.txt                      # qt_add_executable + sources + Corrosion
    main.cpp                            # Entry point: init runtime, create app, show window
    app/                                # Application-level UI
      mainwindow.h / .cpp              # Main window (QTabWidget + 4 tabs)
      mainwindow.ui                    # Main window layout (Qt Designer)
      settingsdialog.h / .cpp          # Settings dialog (4 sub-tabs)
      settingsdialog.ui                # Settings dialog layout
      aboutdialog.h / .cpp             # About dialog
      aboutdialog.ui                   # About dialog layout
      errordialog.h / .cpp             # Error dialog
      errordialog.ui                   # Error dialog layout
      papyrusdialog.h / .cpp           # Papyrus monitor dialog
      papyrusdialog.ui                 # Papyrus monitor layout
      pathdialog.h / .cpp              # Manual path dialog
      pathdialog.ui                    # Path dialog layout
    core/                               # Business logic integration
      signalhub.h / .cpp               # Central Qt signal routing
      featurecontext.h / .cpp          # Dependency injection container
      threadmanager.h / .cpp           # Thread lifecycle management
      rust_qt_bridge.h                 # QString <-> rust::String helpers
      scan_callback.h / .cpp           # CXX callback -> Qt signal adapter
    controllers/                        # Feature controllers (composition pattern)
      scancontroller.h / .cpp          # Scan orchestration
      backupcontroller.h / .cpp        # File backup management
      gamefilescontroller.h / .cpp     # Game file scan management
      resultscontroller.h / .cpp       # Results viewer management
      settingscontroller.h / .cpp      # Settings management
      updatecontroller.h / .cpp        # Update checking
      papyruscontroller.h / .cpp       # Papyrus monitoring
    widgets/                            # Custom widgets
      reportlistwidget.h / .cpp        # Report list with search + status coloring
      reportlistwidget.ui              # Report list layout
      markdownviewer.h / .cpp          # Markdown renderer with zoom
      reportmetadatawidget.h / .cpp    # Report metadata display
    workers/                            # QThread workers
      scanworker.h / .cpp             # Crash log scan worker
      gamefilesworker.h / .cpp        # Game files scan worker
      updateworker.h / .cpp           # Update check worker
      papyrusworker.h / .cpp          # Papyrus monitor worker
    styles/                             # Stylesheets
      dark_theme.qss                   # Global dark mode stylesheet
  resources/
    resources.qrc                       # Qt resource file
    icons/                              # Application icons
    graphics/                           # UI graphics
  tests/
    CMakeLists.txt                      # Test targets
    test_rust_bridge.cpp               # FFI bridge tests
    test_scan_controller.cpp           # Controller tests
```

### 5.2 Integration with Existing Workspace

The `classic-gui-qt6-c++/` directory sits alongside the existing project structure:

```
J:\CLASSIC-Fallout4\
  rust/                               # Existing Rust workspace
    cpp-bindings/                     # NEW: C++ bridge crate(s)
      classic-cpp-bridge/
        Cargo.toml
        build.rs
        src/lib.rs
    business-logic/                   # Existing: ~19 core crates
    foundation/                       # Existing: shared-core
    python-bindings/                  # Existing: PyO3 crates
    node-bindings/                    # Existing: NAPI-RS crate
    ui-applications/
      classic-gui/                    # Existing: Slint GUI
  classic-gui-qt6-c++/                     # NEW: C++ Qt GUI
  ClassicLib/                         # Existing: Python library
  CLASSIC_Interface.py                # Existing: PySide6 entry point
```

### 5.3 vcpkg.json

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg.schema.json",
  "name": "classic-gui-qt6-c++",
  "version": "1.0.0",
  "description": "CLASSIC Crash Log Scanner - C++ Qt GUI",
  "dependencies": [
    "qtbase",
    "qttools"
  ]
}
```

### 5.4 CMakePresets.json

```json
{
  "version": 3,
  "configurePresets": [
    {
      "name": "default",
      "displayName": "Default (MSVC + Ninja)",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build",
      "cacheVariables": {
        "CMAKE_TOOLCHAIN_FILE": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake",
        "CMAKE_BUILD_TYPE": "Release"
      }
    },
    {
      "name": "debug",
      "inherits": "default",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Debug"
      }
    }
  ],
  "buildPresets": [
    {
      "name": "default",
      "configurePreset": "default"
    },
    {
      "name": "debug",
      "configurePreset": "debug"
    }
  ]
}
```

### 5.5 Root CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.22)
project(ClassicGui VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)  # Auto-generate moc for QObject subclasses
set(CMAKE_AUTOUIC ON)  # Auto-process .ui files via uic
set(CMAKE_AUTORCC ON)  # Auto-process .qrc resource files

# Qt setup
find_package(Qt6 REQUIRED COMPONENTS Widgets Network)
qt_standard_project_setup()

# Import Rust crates via Corrosion
include(FetchContent)
FetchContent_Declare(Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.6
)
FetchContent_MakeAvailable(Corrosion)
corrosion_import_crate(
    MANIFEST_PATH ${CMAKE_SOURCE_DIR}/../rust/Cargo.toml
    CRATES classic-cpp-bridge
)

add_subdirectory(src)
add_subdirectory(tests)
```

---

## 6. Implementation Phases

### Phase 1: Scaffold & Foundation (Wave 1 Bindings)

**Goal**: Buildable C++ Qt project that initializes the Rust runtime and loads YAML settings.

**Tasks**:
1. Create `classic-cpp-bridge` Rust crate with runtime init bridge
2. Set up `classic-gui-qt6-c++/` with CMake + vcpkg + Corrosion
3. Create minimal `main.cpp` that initializes Qt and Rust runtime
4. Bridge `YamlOperations` for settings load/save
5. Bridge `classic-registry-core` for global state
6. Create `MainWindow` skeleton with 4 empty tabs
7. Apply dark mode stylesheet
8. Verify end-to-end: app launches, loads settings from YAML, displays window

**Deliverables**: Empty tabbed window, Rust runtime active, settings loaded.

### Phase 2: Main Options Tab

**Goal**: Functional Main Options tab with folder inputs and button layout.

**Tasks**:
1. Implement folder input widgets (QLineEdit + Browse via QFileDialog)
2. Implement all button layouts (primary scan buttons, bottom rows)
3. Create `SignalHub` with initial signals
4. Create `FeatureContext` DI container
5. Wire Browse buttons to QFileDialog
6. Wire EXIT button to `QApplication::quit()`
7. Persist folder paths to YAML settings

**Deliverables**: Main Options tab visually complete, folder browsing works, settings persist.

### Phase 3: Crash Log Scanning (Wave 2 Bindings)

**Goal**: Full crash log scan workflow with progress and results.

**Tasks**:
1. Bridge `OrchestratorCore` (process_log, process_logs_batch)
2. Bridge `AnalysisConfig` and `build_analysis_config_from_yaml()`
3. Bridge `DatabasePool` for FormID lookups
4. Bridge `LogCollector` for crash log discovery
5. Create `ScanCallback` (C++ QObject with CXX callback interface)
6. Create `ScanWorker` (QThread + worker object pattern)
7. Create `ThreadManager` singleton
8. Create `ScanController` orchestrating the full scan workflow
9. Wire "SCAN CRASH LOGS" button through the full pipeline
10. Implement progress reporting (indeterminate -> determinate)
11. Handle scan errors with `CustomErrorDialog`

**Deliverables**: Clicking "Scan Crash Logs" discovers logs, scans them via Rust, generates reports.

### Phase 4: Results Tab

**Goal**: Full results viewing with report list, markdown rendering, and metadata.

**Tasks**:
1. Create `ReportListWidget` with search filter and status coloring
2. Create `MarkdownViewer` (QTextBrowser + markdown-to-HTML conversion)
3. Create `ReportMetadataWidget`
4. Implement report file discovery and listing
5. Implement report selection -> markdown render -> metadata extraction
6. Add QFileSystemWatcher for auto-refresh (with pause/resume during scans)
7. Add zoom controls for markdown viewer
8. Add Copy, Delete, Open Folder buttons
9. Implement auto-switch to Results tab after scan

**Deliverables**: Results tab shows scan reports with markdown rendering, search, and file watching.

**Markdown rendering**: Uses `pulldown-cmark` via CXX bridge (same parser as Slint GUI). Rust converts markdown→HTML, C++ sets it on `QTextBrowser::setHtml()` with Slint-style CSS (see §2.8). No C/C++ markdown library needed.

### Phase 5: Settings Dialog

**Goal**: Full settings dialog with all sub-tabs, persisted to YAML.

**Tasks**:
1. Bridge `VersionRegistry` for game version dropdown population
2. Create `SettingsDialog` with 4 sub-tabs
3. Implement General tab (game version QComboBox)
4. Implement Scanning tab (checkboxes, spinbox)
5. Implement Paths tab (INI path + FormID databases QListWidget)
6. Implement Updates tab (checkbox + check now button)
7. Load settings from YAML on dialog open
8. Save all settings to YAML on dialog accept
9. Emit `settings_changed` signal on save

**Deliverables**: Settings dialog reads/writes all settings via Rust YAML operations.

### Phase 6: File Backup Tab & Game File Scanning (Wave 3 Bindings)

**Goal**: Full backup/restore/remove functionality and game file scanning workflow.

**Tasks**:
1. Bridge `GameFilesManager` (backup, restore, remove)
2. Bridge `BackupManager` for backup type operations
3. Bridge game file scanning APIs (`classic-scangame-core`)
4. Implement backup section UI (4 sections: XSE, ReShade, Vulkan, ENB)
5. Wire BACKUP/RESTORE/REMOVE buttons to Rust operations
6. Add "Open Classic Backups" folder button
7. Show progress/status for backup operations
8. Create `GameFilesWorker` (QThread worker for game file scan)
9. Create `GameFilesController` orchestrating the scan workflow
10. Wire "SCAN GAME FILES" button (placed in Phase 2) through the full pipeline
11. Combine game file scan results with crash log results where applicable

**Deliverables**: All backup operations work via Rust file I/O. Game file scanning is fully functional.

### Phase 7: Remaining Features (Waves 4-5 Bindings)

**Goal**: Feature parity with PySide6 GUI (excluding deferred pastebin integration).

**Tasks**:
1. Bridge `GithubClient` for update checking
2. Implement update check worker + UI feedback
3. Bridge Papyrus analysis for monitoring
4. Implement Papyrus monitoring (1-second poll loop, stats dialog)
5. Implement Articles tab (external URL buttons via `QDesktopServices::openUrl()`)
6. Implement ABOUT and HELP dialogs
7. Bridge game path detection for first-run setup
8. Implement ManualPathDialog for first-run game path selection
9. Implement window geometry save/restore

**Deliverables**: Complete feature parity with PySide6 GUI (pastebin integration deferred to a future phase).

### Phase 8: Polish & Deployment

**Goal**: Production-ready release.

**Tasks**:
1. Refine dark mode stylesheet to match PySide6 appearance
2. Add application icon and window icon
3. Set up `qt_generate_deploy_app_script()` for deployment
4. Create build script (`build_qt_gui.ps1`)
5. Add CI/CD pipeline (GitHub Actions)
6. Performance testing and optimization
7. Accessibility review (keyboard navigation, screen reader support)
8. Cross-testing with various Windows versions

**Deliverables**: Deployable, tested C++ Qt GUI binary.

---

## 7. CI/CD Pipeline

### 7.1 GitHub Actions Workflow

```yaml
name: Qt C++ GUI CI
on: [push, pull_request]

jobs:
  build-qt-gui:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Qt
        uses: jurplel/install-qt-action@v4
        with:
          version: '6.10.0'
          target: 'desktop'
          arch: 'win64_msvc2022_64'
          cache: true

      - name: Setup MSVC
        uses: ilammy/msvc-dev-cmd@v1
        with:
          arch: x64

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Rust cache
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: rust

      - name: Configure CMake
        working-directory: classic-gui-qt6-c++
        run: cmake --preset default

      - name: Build
        working-directory: classic-gui-qt6-c++
        run: cmake --build build --config Release

      - name: Run tests
        working-directory: classic-gui-qt6-c++
        run: ctest --test-dir build --output-on-failure

      - name: Deploy
        working-directory: classic-gui-qt6-c++
        run: |
          mkdir deploy
          copy build\ClassicGui.exe deploy\
          windeployqt6 --release --no-translations deploy\ClassicGui.exe

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ClassicGui-Qt-Windows
          path: classic-gui-qt6-c++/deploy/
```

### 7.2 Integration with Existing CI

The Qt GUI CI job runs in parallel with the existing Python and Rust CI jobs. It depends on:
- Rust workspace building successfully (shared crates)
- No changes needed to existing CI jobs

---

## 8. Testing Strategy

### 8.1 Test Layers

| Layer | Framework | Tests |
|-------|-----------|-------|
| CXX Bridge | Rust `#[test]` + C++ catch2/gtest | Type conversion, FFI round-trips, error mapping |
| Controllers | Qt Test (QTest) | Controller logic with mocked Rust bridge |
| Widgets | Qt Test | Widget state, signal emission, user interaction simulation |
| Integration | Manual + automated screenshots | Full scan workflow, settings persistence, visual regression |

### 8.2 Bridge Testing Pattern

```cpp
// tests/test_rust_bridge.cpp
#include <QTest>
#include "classic-cpp-bridge/src/lib.rs.h"

class TestRustBridge : public QObject {
    Q_OBJECT
private slots:
    void initTestCase() {
        classic::init_runtime();
    }
    void test_yaml_load() {
        auto result = classic::yaml::load_setting("CLASSIC_Settings.FCX Mode");
        QVERIFY(!result.empty());
    }
    void cleanupTestCase() {
        classic::shutdown_runtime();
    }
};
```

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CXX async limitations | Medium | Medium | Use sync wrappers with `block_on()` in worker threads; callbacks for progress |
| Qt vcpkg build times in CI | High | Low | Use `install-qt-action` (prebuilt) instead of vcpkg for Qt in CI |
| Markdown rendering parity | Low | Low | Use `pulldown-cmark` via CXX (proven in Slint GUI); target Slint's minimalist style which is simpler than PySide6's |
| Complex type mapping | Medium | Medium | Keep CXX bridge types simple (DTOs); complex logic stays in Rust |
| Corrosion CMake integration issues | Low | High | Corrosion v0.6 is stable; pin version in FetchContent |
| LGPL licensing with static Qt | Low | High | Use dynamic linking exclusively; document in build instructions |
| Windows-only deployment | N/A | N/A | Acceptable; CLASSIC is Windows-only (Fallout 4 / Skyrim) |

---

## 10. Success Criteria

1. **Feature parity**: All PySide6 GUI features replicated in C++ Qt
2. **Performance**: Application startup < 500ms (vs ~2s for PySide6)
3. **Binary size**: Deployed package < 50 MB (Qt DLLs + Rust + exe)
4. **Test coverage**: CXX bridge 100% tested, controllers 80%+ tested
5. **CI green**: All CI checks pass on `windows-latest`
6. **Zero Python dependency**: C++ GUI runs without Python installed
7. **Visual parity**: Dark mode appearance and layout matches PySide6 GUI; markdown rendering matches Slint GUI's minimalist style (§2.8)

---

## 11. Open Questions

1. ~~**Markdown rendering**~~: **RESOLVED** — Use `pulldown-cmark` via CXX bridge (Rust→HTML→QTextBrowser). Style follows Slint GUI's clean minimalist aesthetic (§2.8), not PySide6's colored-box approach.
2. ~~**Pastebin integration**~~: **DEFERRED** — Not included in initial C++ Qt GUI scope. May be added in a future phase if needed.
3. ~~**Game files scan**~~: **RESOLVED** — Integrated into Phase 6 alongside file backup (both use Wave 3 bindings). The "SCAN GAME FILES" button UI is placed in Phase 2; wired to Rust in Phase 6.
4. ~~**Qt Designer**~~: **RESOLVED** — Use `.ui` files for all windows, dialogs, and complex widget layouts. Separates visual layout from business logic and enables visual editing with Qt Designer/Creator.
5. **Coexistence**: Should the C++ Qt GUI eventually replace the PySide6 GUI, or coexist as an alternative? Decision deferred to a later date.

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| CXX | Rust crate for safe C++/Rust interop via declared bridges |
| Corrosion | CMake module that imports Rust Cargo projects into CMake builds |
| vcpkg | Microsoft's C/C++ package manager with CMake integration |
| CLASSIC | Crash Log Auto Scanner & Setup Integrity Checker |
| OrchestratorCore | Central Rust type that coordinates crash log analysis |
| AsyncBridge | Pattern for bridging async Tokio work to UI thread updates |
| ONE RUNTIME RULE | Architecture constraint: single shared Tokio runtime via `get_runtime()` |
| SignalHub | Central Qt signal routing object for cross-controller communication |
| FeatureContext | Dependency injection container holding shared references |

## Appendix B: Reference Documents

- [CXX documentation](https://cxx.rs/)
- [Corrosion GitHub](https://github.com/corrosion-rs/corrosion)
- [vcpkg documentation](https://vcpkg.io/en/docs/README.html)
- [Qt 6 CMake documentation](https://doc.qt.io/qt-6/cmake-manual.html)
- PRD: Python-to-Rust Migration (`docs/prd/complete/python-to-rust-migration.md`)
- CLASSIC v9.0.0 Slint GUI (reference implementation for Rust-GUI patterns)
