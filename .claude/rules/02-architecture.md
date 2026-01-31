# Architecture

## Hybrid Python-Rust Architecture

- **Python**: UI, high-level logic in `ClassicLib/`
- **Rust**: Three-layer architecture (10-150x performance gains)
  - **Foundation**: `classic-shared` (runtime, errors, utilities)
  - **Business Logic**: `-core` crates (pure Rust, no PyO3)
  - **Python Bindings**: `-py` crates (PyO3 adapters)
- **Direct imports**: `import classic_yaml`, `import classic_scanlog`
- **Fallback**: Pure Python implementations ensure compatibility

**Key Rules:**
- ONE RUNTIME: Single global Tokio runtime via `classic_shared::get_runtime()`
- NO MIXED CRATES: Business logic in `-core`, PyO3 in `-py`

## Rust Directory Structure

```
rust/
├── Cargo.toml                    # Workspace manifest (authoritative)
├── foundation/                   # Shared runtime, errors
├── business-logic/               # Pure Rust -core crates
├── python-bindings/              # PyO3 -py crates
└── ui-applications/              # CLI, TUI, GUI apps
```

Use `/rust-crate` skill when creating new crates.

## Core Components

| Component | Purpose |
|-----------|---------|
| `CLASSIC_Interface.py` | GUI entry point |
| `CLASSIC_ScanLogs.py` | CLI entry point |
| AsyncBridge | Async/sync bridging (GUI only) |
| MessageHandler | Central messaging for all outputs |
| YamlSettingsCache | Configuration with batch loading |
| FileIOCore | Async file I/O with Rust acceleration |
| OrchestratorCore | Log scanning orchestration |

## Essential Patterns

```python
# AsyncBridge for GUI sync contexts
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Rust acceleration (automatic)
from ClassicLib.ScanLog.Parser import find_segments
from ClassicLib.integration.factory import get_parser  # Auto fallback
```

## References

- `docs/development/rust_workspace_architecture.md` - Crate hierarchy
- `docs/development/async_development_guide.md` - Async patterns
- `docs/development/pyo3_integration_patterns.md` - PyO3 patterns
