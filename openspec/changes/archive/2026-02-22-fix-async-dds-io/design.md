## Context

`FileIOCore::read_dds_header()` in `classic-file-io-core/src/core.rs` is declared `async fn` but uses synchronous I/O internally:

```rust
let mut file = File::open(path)?;         // std::fs::File — blocks worker thread
let bytes_read = file.read(&mut buffer)?; // std::io::Read — blocks worker thread
```

`File` is imported from `std::fs` (line 16 of core.rs). The Tokio executor runs work on a fixed-size thread pool; blocking a thread for the syscall duration reduces available parallelism for all other async tasks.

The sibling method `read_dds_header_sync()` (used by `read_dds_headers_batch` via Rayon) is correctly synchronous — Rayon manages its own thread pool and blocking is expected there.

## Goals / Non-Goals

**Goals:**
- Replace the two blocking I/O calls in `read_dds_header` with `tokio::fs::File` + `AsyncReadExt::read()`
- Keep the cache lookup and insertion logic identical

**Non-Goals:**
- Changing `read_dds_header_sync()` or `read_dds_headers_batch()` — those are correct
- Optimising the DDS write-lock-for-read pattern (LruCache requires `&mut self` for `get`, so `write()` is necessary)
- Increasing the read size beyond 2KB

## Decisions

### Use tokio::fs::File + AsyncReadExt

```rust
use tokio::fs::File;
use tokio::io::AsyncReadExt;

let mut file = File::open(path).await?;
let bytes_read = file.read(&mut buffer).await?;
```

The `std::fs` import remains for other uses in the file (sync read_line iterator, `std::fs::File::create` in tests). Only the two lines in `read_dds_header` change.

**Alternative: `spawn_blocking`** — wrapping the sync I/O in `tokio::task::spawn_blocking` would also work but adds a closure boundary and heap allocation for the task. Using async I/O directly is cleaner and avoids the blocking thread pool.

## Risks / Trade-offs

- **`?` error type**: `tokio::fs::File::open` returns `tokio::io::Result` (same as `std::io::Result`), so the `FileIOError::from(io::Error)` path is unchanged.
- **Minimal change**: Only two lines in one function body change; no signature change, no caller updates needed.

## Migration Plan

1. In `read_dds_header`: replace `File::open(path)?` with `tokio::fs::File::open(path).await?`
2. Replace `file.read(&mut buffer)?` with `file.read(&mut buffer).await?` (add `use tokio::io::AsyncReadExt` if not already in scope)
3. Build and confirm no type errors

## Open Questions

*(none)*
