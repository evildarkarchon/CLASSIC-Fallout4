# CLASSIC Architecture Overview

> **Document Version**: 2.0 | **Last Updated**: December 2025

This document provides a comprehensive architectural overview of CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker), a hybrid Python-Rust desktop application for analyzing crash logs from Bethesda games.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Diagrams](#component-diagrams)
4. [Data Flow](#data-flow)
5. [Rust Acceleration Layer](#rust-acceleration-layer)
6. [Application Interfaces](#application-interfaces)
7. [Key Patterns](#key-patterns)
8. [Directory Structure](#directory-structure)

---

## Executive Summary

CLASSIC is a **hybrid Python-Rust application** that combines:
- **Python** for UI, high-level logic, and coordination
- **Rust** for performance-critical operations (10-150x speedups)

**Key Characteristics**:
- Three application interfaces: GUI (PySide6), CLI (Python), TUI (Ratatui/Rust)
- Three-tier Rust architecture: Foundation, Business Logic, Python Bindings
- Async-first design with sync wrappers for GUI compatibility
- Automatic Rust acceleration with Python fallbacks

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Interfaces"
        GUI[GUI - PySide6/Qt]
        CLI[CLI - Python asyncio]
        TUI[TUI - Ratatui/Rust]
    end

    subgraph "Python Layer"
        subgraph "Core Library - ClassicLib"
            AB[AsyncBridge]
            GR[GlobalRegistry]
            MH[MessageHandler]
            YS[YamlSettings]
            FIO[FileIOCore]
            SL[ScanLog]
        end

        subgraph "Integration Layer"
            DET[Detector]
            FAC[Factory]
            EXC[Exceptions]
        end
    end

    subgraph "Rust Acceleration Layer"
        subgraph "Python Bindings"
            PY_YAML[classic-yaml-py]
            PY_DB[classic-database-py]
            PY_SCAN[classic-scanlog-py]
            PY_FILE[classic-file-io-py]
        end

        subgraph "Business Logic"
            CORE_YAML[classic-yaml-core]
            CORE_DB[classic-database-core]
            CORE_SCAN[classic-scanlog-core]
            CORE_FILE[classic-file-io-core]
        end

        subgraph "Foundation"
            SHARED[classic-shared-core]
        end
    end

    GUI --> AB
    GUI --> MH
    CLI --> SL
    CLI --> YS
    TUI --> SHARED

    AB --> SL
    GR --> YS
    MH --> YS
    FIO --> PY_FILE

    DET --> PY_YAML
    DET --> PY_DB
    FAC --> DET

    PY_YAML --> CORE_YAML
    PY_DB --> CORE_DB
    PY_SCAN --> CORE_SCAN
    PY_FILE --> CORE_FILE

    CORE_YAML --> SHARED
    CORE_DB --> SHARED
    CORE_SCAN --> SHARED
    CORE_FILE --> SHARED
```

---

## Component Diagrams

### Entry Points

```mermaid
flowchart LR
    subgraph "Entry Points"
        IF[CLASSIC_Interface.py<br/>GUI Entry]
        SL[CLASSIC_ScanLogs.py<br/>CLI Entry]
        SG[CLASSIC_ScanGame.py<br/>Game Scanner]
    end

    subgraph "Initialization"
        SC[SetupCoordinator]
        GR[GlobalRegistry]
        MH[MessageHandler]
    end

    IF --> SC
    SL --> SC
    SG --> SC

    SC --> GR
    SC --> MH
```

### GUI Architecture (Composition Pattern)

```mermaid
classDiagram
    class MainWindow {
        +thread_manager: ThreadManager
        +signal_hub: SignalHub
        +context: FeatureContext
        +scan_controller: ScanController
        +backup_manager: BackupManager
        +folder_manager: FolderManager
        +results_viewer: ResultsViewerController
    }

    class FeatureContext {
        +main_window: MainWindow
        +thread_manager: ThreadManager
        +signal_hub: SignalHub
        +ui_widgets: WidgetRegistry
    }

    class SignalHub {
        +scan_started: Signal
        +scan_completed: Signal
        +results_ready: Signal
        +progress_updated: Signal
    }

    class ThreadManager {
        +start_worker()
        +stop_all_threads()
        +get_active_workers()
    }

    MainWindow --> FeatureContext
    MainWindow --> SignalHub
    MainWindow --> ThreadManager
    FeatureContext --> ThreadManager
    FeatureContext --> SignalHub
```

### CLI Architecture (Async-First)

```mermaid
sequenceDiagram
    participant Main as main()
    participant SC as SetupCoordinator
    participant Exec as ScanLogsExecutor
    participant Orch as OrchestratorCore
    participant Rust as Rust Modules

    Main->>SC: initialize_application()
    Main->>Main: parse_arguments()
    Main->>Exec: create executor
    Main->>Exec: await execute_scan()
    Exec->>Orch: await orchestrate_scan()
    Orch->>Rust: parallel analysis
    Rust-->>Orch: results
    Orch-->>Exec: ScanResult
    Exec-->>Main: summary
```

---

## Data Flow

### Crash Log Analysis Flow

```mermaid
flowchart TB
    subgraph "Input"
        LOG[Crash Log Files]
        YAML[YAML Databases]
    end

    subgraph "Parsing"
        SEG[Segment Extractor]
        PAR[Log Parser]
    end

    subgraph "Analysis"
        FORM[FormID Analyzer]
        PLUG[Plugin Analyzer]
        GPU[GPU Detector]
        SETT[Settings Scanner]
        FCX[FCX Mode Handler]
    end

    subgraph "Reporting"
        FRAG[Fragment Collector]
        COMP[Report Composer]
        OUT[Final Report]
    end

    LOG --> SEG
    SEG --> PAR
    YAML --> FORM
    YAML --> PLUG

    PAR --> FORM
    PAR --> PLUG
    PAR --> GPU
    PAR --> SETT
    PAR --> FCX

    FORM --> FRAG
    PLUG --> FRAG
    GPU --> FRAG
    SETT --> FRAG
    FCX --> FRAG

    FRAG --> COMP
    COMP --> OUT
```

### Configuration Flow

```mermaid
flowchart LR
    subgraph "YAML Files"
        MAIN[CLASSIC Main.yaml]
        SETT[CLASSIC Settings.yaml]
        GAME[CLASSIC Fallout4.yaml]
        IGN[CLASSIC Ignore.yaml]
    end

    subgraph "Cache Layer"
        YC[YamlCache]
        RUST_Y[Rust YAML<br/>yaml-rust2]
    end

    subgraph "API"
        SYNC[yaml_settings<br/>Sync API]
        ASYNC[yaml_settings_async<br/>Async API]
    end

    MAIN --> YC
    SETT --> YC
    GAME --> YC
    IGN --> YC

    YC --> RUST_Y
    YC --> SYNC
    YC --> ASYNC
```

---

## Rust Acceleration Layer

### Three-Tier Architecture

```mermaid
graph TB
    subgraph "Layer 3: Python Bindings"
        direction LR
        PY1[classic-yaml-py]
        PY2[classic-database-py]
        PY3[classic-scanlog-py]
        PY4[classic-file-io-py]
        PY5[classic-config-py]
        PYDOTS[...]
    end

    subgraph "Layer 2: Business Logic"
        direction LR
        CORE1[classic-yaml-core]
        CORE2[classic-database-core]
        CORE3[classic-scanlog-core]
        CORE4[classic-file-io-core]
        CORE5[classic-config-core]
        COREDOTS[...]
    end

    subgraph "Layer 1: Foundation"
        SHARED[classic-shared-core]
        SHAREDPY[classic-shared-py]
    end

    PY1 --> CORE1
    PY2 --> CORE2
    PY3 --> CORE3
    PY4 --> CORE4
    PY5 --> CORE5

    CORE1 --> SHARED
    CORE2 --> SHARED
    CORE3 --> SHARED
    CORE4 --> SHARED
    CORE5 --> SHARED

    SHAREDPY --> SHARED
```

### Crate Organization

| Layer | Purpose | PyO3 | Crate Type |
|-------|---------|------|------------|
| Foundation | Shared runtime, errors, utilities | Minimal | `rlib` |
| Business Logic | Pure Rust algorithms | **None** | `rlib` |
| Python Bindings | PyO3 adapters only | Yes | `cdylib + rlib` |

### Key Architecture Rules

1. **ONE RUNTIME RULE**: All crates share global Tokio runtime via `classic_shared::get_runtime()`
2. **SEPARATION**: Business logic (`-core`) separate from PyO3 bindings (`-py`)
3. **NO MIXED CRATES**: Never combine business logic with PyO3 in same crate
4. **TYPE STUBS**: All `-py` crates must have `.pyi` files

### Performance Gains

```mermaid
xychart-beta
    title "Rust Acceleration Speedups (x times faster)"
    x-axis ["YAML Loading", "File I/O", "Registry Ops", "Log Parsing", "Database"]
    y-axis "Speedup Factor" 0 --> 35
    bar [25, 10, 20, 15, 12]
```

| Component | Python Baseline | Rust Accelerated | Speedup |
|-----------|-----------------|------------------|---------|
| YAML Loading | 100ms | 4ms | 25x |
| File I/O | 50ms | 5ms | 10x |
| Registry Ops | 10ms | 0.5ms | 20x |
| Log Parsing | 200ms | 13ms | 15x |
| Database | 60ms | 5ms | 12x |

---

## Application Interfaces

### GUI (PySide6/Qt)

```mermaid
graph TB
    subgraph "Main Window"
        MW[MainWindow]
        TW[TabWidget]
    end

    subgraph "Tabs"
        MAIN[Main Tab]
        BACK[Backups Tab]
        ART[Articles Tab]
        RES[Results Tab]
    end

    subgraph "Controllers"
        SC[ScanController]
        BM[BackupManager]
        FM[FolderManager]
        PM[PapyrusManager]
        UM[UpdateManager]
    end

    subgraph "Workers"
        SW[ScanWorker]
        FW[FileWorker]
        UW[UpdateWorker]
    end

    MW --> TW
    TW --> MAIN
    TW --> BACK
    TW --> ART
    TW --> RES

    MAIN --> SC
    BACK --> BM
    MAIN --> FM
    MAIN --> PM
    MAIN --> UM

    SC --> SW
    BM --> FW
    UM --> UW
```

### CLI (Async Python)

```mermaid
flowchart TB
    ENTRY[main.py]
    ARGS[Argument Parser]
    CONFIG[ScanConfig]
    EXEC[ScanLogsExecutor]
    RESULT[ScanResult]
    OUTPUT[Console Output]

    ENTRY --> |asyncio.run| ARGS
    ARGS --> CONFIG
    CONFIG --> EXEC
    EXEC --> |await| RESULT
    RESULT --> OUTPUT
```

### TUI (Ratatui/Rust)

```mermaid
graph TB
    subgraph "Rust TUI"
        APP[Application]
        UI[UI Renderer]
        STATE[State Manager]
    end

    subgraph "Screens"
        HOME[Home Screen]
        SCAN[Scan Screen]
        RESULTS[Results Screen]
        SETTINGS[Settings Screen]
    end

    subgraph "Backend"
        CORE[classic-scanlog-core]
        YAML[classic-yaml-core]
    end

    APP --> UI
    APP --> STATE

    STATE --> HOME
    STATE --> SCAN
    STATE --> RESULTS
    STATE --> SETTINGS

    SCAN --> CORE
    SETTINGS --> YAML
```

---

## Key Patterns

### AsyncBridge Pattern (GUI Only)

```mermaid
sequenceDiagram
    participant Qt as Qt Thread
    participant AB as AsyncBridge
    participant BG as Background Loop
    participant Async as Async Function

    Qt->>AB: get_instance()
    AB->>AB: ensure_loop()
    AB->>BG: start background thread
    Qt->>AB: run_async(coro)
    AB->>BG: run_coroutine_threadsafe
    BG->>Async: await coro
    Async-->>BG: result
    BG-->>AB: future.result()
    AB-->>Qt: return result
```

### Async-First Pattern (CLI/TUI)

```mermaid
flowchart TB
    ENTRY[Entry Point]
    ASYNCIO[asyncio.run]
    MAIN[async main]
    WORK[await work]
    RESULT[Result]

    ENTRY --> ASYNCIO
    ASYNCIO --> MAIN
    MAIN --> WORK
    WORK --> RESULT
```

### Factory Pattern (Rust Integration)

```mermaid
flowchart TB
    CODE[Application Code]
    FAC[Factory Function]
    DET[Component Detector]
    RUST{Rust Available?}
    RUST_IMPL[Rust Implementation]
    PY_IMPL[Python Fallback]

    CODE --> FAC
    FAC --> DET
    DET --> RUST
    RUST -->|Yes| RUST_IMPL
    RUST -->|No| PY_IMPL
```

---

## Directory Structure

```
CLASSIC-Fallout4/
├── CLASSIC_Interface.py          # GUI entry point
├── CLASSIC_ScanLogs.py           # CLI entry point
├── CLASSIC_ScanGame.py           # Game scanner entry
│
├── ClassicLib/                   # Main Python library
│   ├── __init__.py              # Public API exports
│   ├── AsyncBridge.py           # Sync/async bridging
│   ├── GlobalRegistry.py        # Global object storage
│   ├── SetupCoordinator.py      # Application initialization
│   │
│   ├── MessageHandler/          # Unified messaging
│   │   ├── handler.py
│   │   ├── formatting/
│   │   ├── output/
│   │   └── progress/
│   │
│   ├── YamlSettings/            # Configuration management
│   │   ├── async_/              # Async API
│   │   ├── sync/                # Sync API
│   │   └── validators.py
│   │
│   ├── FileIO/                  # File operations
│   ├── ScanLog/                 # Crash log analysis
│   │   ├── models/
│   │   ├── fragments/
│   │   ├── pipeline/
│   │   └── composition/
│   │
│   ├── Interface/               # GUI components
│   │   ├── controllers/
│   │   ├── context.py
│   │   └── signal_hub.py
│   │
│   ├── integration/             # Rust integration
│   │   ├── detector.py
│   │   ├── factory/
│   │   └── exceptions.py
│   │
│   ├── Utils/                   # Utility functions
│   ├── python/                  # Python fallbacks
│   └── rust/                    # Rust API wrappers
│
├── ClassicLib-rs/               # Rust workspace
│   ├── Cargo.toml              # Workspace manifest
│   │
│   ├── foundation/             # Layer 1
│   │   ├── classic-shared-core/
│   │   └── classic-shared-py/
│   │
│   ├── business-logic/         # Layer 2 (NO PyO3)
│   │   ├── classic-yaml-core/
│   │   ├── classic-database-core/
│   │   ├── classic-scanlog-core/
│   │   └── ... (19 crates)
│   │
│   ├── python-bindings/        # Layer 3 (PyO3 only)
│   │   ├── classic-yaml-py/
│   │   ├── classic-database-py/
│   │   └── ... (20 crates)
│   │
│   └── ui-applications/        # Standalone apps
│       ├── classic-cli/
│       └── classic-tui/
│
├── tests/                       # Test suite
│   ├── conftest.py
│   ├── fixtures/               # Centralized fixtures
│   └── ... (domain directories)
│
└── docs/                        # Documentation
    ├── api/
    ├── architecture/
    ├── development/
    ├── testing/
    └── rust/
```

---

## See Also

- [API Reference](../api/API_REFERENCE.md)
- [Quick Start Guide](../api/QUICK_START.md)
- [Rust Workspace Architecture](../development/rust_workspace_architecture.md)
- [Async Development Guide](../development/async_development_guide.md)
- [Testing Guide](../testing/TESTING_GUIDE_INDEX.md)

---

*Last updated: December 2025*
