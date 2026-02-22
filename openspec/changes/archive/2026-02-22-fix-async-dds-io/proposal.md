## Why

`FileIOCore::read_dds_header()` is an `async fn` that uses synchronous `std::fs::File::open()` and `std::io::Read::read()` for disk access. Blocking system calls inside Tokio async functions hold a worker thread for the duration of the I/O, starving other async tasks. This is especially visible when scanning multiple crash logs concurrently triggers DDS header lookups in parallel.

## What Changes

- **Replace** `std::fs::File::open()` + `file.read()` inside `read_dds_header` with `tokio::fs::File::open()` + `AsyncReadExt::read()` so the await yields the worker thread during I/O
- The `read_dds_header_sync()` method (used by `read_dds_headers_batch` via Rayon) remains synchronous — that path is correct

## Capabilities

### New Capabilities

*(none — this is a correctness fix, not a new capability)*

### Modified Capabilities

*(no spec-level behavior change — the function returns the same result; only the thread-blocking characteristic changes)*

## Impact

- **Modified**: `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` (`read_dds_header` function body only)
- **No API change**: function signature, return type, and caching behavior unchanged
- **Correctness**: async function no longer blocks Tokio worker threads during DDS file I/O
