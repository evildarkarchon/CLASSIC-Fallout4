# Shared Error Schema Definition

**Date:** 2025-12-22
**Track:** Optimize Python-Rust Integration Layer

## Overview
The project standardizes on `ClassicError` (defined in `classic-shared-core`) as the intermediate error type for all Rust-to-Python error propagation.

## Schema Definition
The `ClassicError` enum covers the following categories:

| Rust Variant | Python Exception | Use Case |
| :--- | :--- | :--- |
| `Io` | `IOError` | File system operations, network I/O |
| `Path` | `IOError` | Invalid paths, path resolution failures |
| `Validation` | `ValueError` | Invalid configuration, malformed input data |
| `Parse` | `ValueError` | Log parsing failures, regex mismatches |
| `Database` | `RuntimeError` | SQLite/SQL operations |
| `Cache` | `RuntimeError` | Cache corruption or access errors |
| `Encoding` | `ValueError` | UTF-8 conversion failures |
| `Timeout` | `TimeoutError` | Long-running operations (async) |
| `Permission` | `PermissionError` | Access denied (file system) |
| `Configuration` | `ValueError` | Missing or invalid settings keys |
| `Processing` | `RuntimeError` | General algorithm failures (e.g., GPU detection) |
| `NotFound` | `FileNotFoundError` | Missing resources, files, or records |
| `InvalidState` | `RuntimeError` | Logic errors, illegal state transitions |
| `Generic` | `RuntimeError` | Fallback for unclassified errors |

## Implementation Strategy
1. **Core Crates (`classic-scanlog-core`, etc.):** Will implement `Into<ClassicError>` for their specific error types.
2. **Binding Layer (`classic-scanlog-py`):** Will use `classic_shared_py::to_py_err` (or a new `From` impl) to convert `ClassicError` to `PyErr`.
3. **Python:** Will receive standard Python exceptions with rich context messages.
