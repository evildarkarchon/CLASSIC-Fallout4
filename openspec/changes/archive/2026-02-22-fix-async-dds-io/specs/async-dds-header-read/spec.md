## ADDED Requirements

### Requirement: read_dds_header uses non-blocking I/O
The `FileIOCore::read_dds_header()` async method SHALL use `tokio::fs::File` and `tokio::io::AsyncReadExt` for file access, so that the Tokio worker thread yields during I/O rather than blocking.

#### Scenario: No blocking syscall on worker thread
- **WHEN** `read_dds_header()` is called and the path is not cached
- **THEN** the function SHALL NOT call `std::fs::File::open()` or `std::io::Read::read()` (blocking variants) inside the async context

#### Scenario: Async I/O path yields on open
- **WHEN** `read_dds_header()` opens a file that is slow to access (e.g., network path or cold cache)
- **THEN** the Tokio worker thread SHALL be available for other tasks while awaiting the open and read

#### Scenario: Return value unchanged
- **WHEN** a valid DDS file path is provided
- **THEN** `read_dds_header()` SHALL return `Ok(Some(DDSHeader { ... }))` with the same header data as the sync variant

#### Scenario: Cache behavior unchanged
- **WHEN** `read_dds_header()` is called twice for the same path
- **THEN** the second call SHALL return the cached result without performing I/O

### Requirement: read_dds_header_sync remains synchronous
The `FileIOCore::read_dds_header_sync()` method SHALL continue to use `std::fs::File` (blocking I/O), as it is called exclusively from Rayon threads where blocking is expected.

#### Scenario: Sync variant unmodified
- **WHEN** `read_dds_headers_batch()` calls `read_dds_header_sync()` via Rayon
- **THEN** it SHALL use the same sync I/O path as before this change
