## 1. Fix read_dds_header to use async I/O

- [x] 1.1 In `classic-file-io-core/src/core.rs`, add `use tokio::io::AsyncReadExt;` to the imports (if not already present)
- [x] 1.2 In the `read_dds_header` function body (after the cache-miss path), replace `let mut file = File::open(path)?;` with `let mut file = tokio::fs::File::open(path).await?;`
- [x] 1.3 Replace `let bytes_read = file.read(&mut buffer)?;` with `let bytes_read = file.read(&mut buffer).await?;`
- [x] 1.4 Confirm `std::fs::File` import is still needed for other uses in the file (sync line iterator, tests); do not remove it

## 2. Build and test

- [x] 2.1 Run `cargo build -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml` and confirm clean compilation
- [x] 2.2 Run `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml` and confirm all tests pass
- [x] 2.3 Confirm `read_dds_headers_batch` (Rayon/sync path) still calls `read_dds_header_sync` unchanged
