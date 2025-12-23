# Specification: Optimize Python-Rust Integration Layer

## 1. Overview
This track focuses on refining the interface between the Python application and the Rust core libraries (`classic-core`). The goal is to improve performance by minimizing data copying, ensuring strict type safety across the FFI boundary, and standardizing error handling.

## 2. Goals
*   **Reduce FFI Overhead:** Minimize the serialization/deserialization cost (e.g., JSON string passing) by using direct PyO3 type conversions where applicable.
*   **Enhance Type Safety:** Ensure that data passed between Python and Rust is strictly typed, reducing runtime `TypeError`s.
*   **Standardize Error Handling:** Implement a consistent strategy for propagating Rust `Result`s as Python exceptions.
*   **Memory Safety:** Verify that memory management across the boundary is leak-free, particularly for long-running processes.

## 3. Scope
*   **Target Modules:**
    *   `rust/python-bindings/` (The PyO3 adapter layer)
    *   `ClassicLib/rust_loader.py` (The Python side loader)
    *   Specific focus on high-traffic bindings: `scan_log`, `scan_game`, and `config_manager`.
*   **Out of Scope:**
    *   Rewriting core business logic within Rust (unless necessary for the API change).
    *   Major UI refactoring in Python.

## 4. Technical Approach
*   **PyO3 Type Conversion:** Audit existing `#[pyfunction]` and `#[pymethods]` to use `PyResult<T>` and strictly typed arguments instead of generic `PyObject` where possible.
*   **Custom Exception Mapping:** Define a mapping between Rust `thiserror` enums and custom Python exception classes in `ClassicLib.exceptions`.
*   **Zero-Copy Optimizations:** Investigate using `PyBuffer` protocol for large file buffers if applicable.

## 5. Success Criteria
*   **Performance:** measurable reduction in call overhead for high-frequency FFI calls (benchmarked).
*   **Stability:** No new crashes or memory leaks introduced.
*   **Code Quality:** Clean, well-documented Rust bindings with corresponding `.pyi` type stubs for Python static analysis.
