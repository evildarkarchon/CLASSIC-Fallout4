# External Integrations

**Analysis Date:** 2026-01-29

## APIs & External Services

**GitHub API:**
- Service - Release version checking and updates
- SDK/Client: aiohttp with GitHub REST API v3
- Auth: `GITHUB_TOKEN` env var (required for authenticated requests to avoid rate limiting)
- Endpoints:
  - `GET https://api.github.com/repos/{owner}/{repo}/releases/latest` - Fetch latest stable release
  - `GET https://api.github.com/repos/{owner}/{repo}/releases` - List all releases for prerelease detection
- Scope: `ClassicLib/support/update.py` provides functions:
  - `get_github_latest_stable_version_from_endpoint()` - Async fetch of latest stable version
  - `get_github_latest_prerelease_version_from_list()` - Async fetch of latest prerelease
  - `get_latest_and_top_release_details()` - Comprehensive release details
- Error Handling: Returns None on 404 or connection errors; logs warnings for non-dict responses

**Pastebin Services (Paste Content Fetching):**
- Services:
  - pastebin.com
  - paste.ee
  - hastebin.com
  - haste.zneix.eu
- Purpose: Download crash logs from user-shared pastebin links
- Client:
  - Sync: `requests >= 2.32.3` with 10-second timeout
  - Async: `aiohttp >= 3.10.10` with ClientTimeout(total=10)
- Endpoint Format:
  - pastebin.com → `https://pastebin.com/raw/{paste_id}`
  - paste.ee → `https://paste.ee/r/{paste_id}`
  - hastebin → `https://{service}/raw/{paste_id}`
- Scope: `ClassicLib/Utils/web_utils.py`
  - `pastebin_fetch(url)` - Sync download (blocks)
  - `async_pastebin_fetch(url)` - Async download (non-blocking)
- Output: Saves to `./Crash Logs/Pastebin/crash-{paste_id}.log`
- Error Handling: Catches `requests.RequestException`, `aiohttp.ClientError`, TimeoutError

## Data Storage

**Databases:**
- SQLite (local file-based)
  - Implementation: `ClassicLib/io/database/rust_pool.py`
  - Rust: `classic-database-core` (connection pooling, 25x faster)
  - Python: `ClassicLib/io/database/async_pool.py` (fallback)
  - Client: `rusqlite` (sync) + `sqlx` (async Rust) + `aiosqlite` (async Python fallback)
  - Purpose: Plugin form ID registry, crash analysis cache, configuration
  - Persistence: Application-scoped databases stored in user data directory
  - API: `RustAsyncDatabasePool()` class with async `initialize()`, `get_entry()`, `get_entries_batch()`

**File Storage:**
- Local filesystem only (no cloud integration)
  - Game installation directories (read-only analysis)
  - User home directory for configuration (via appdirs)
  - Application data directory for caches and databases
  - `./Crash Logs/` directory for analysis results

**Caching:**
- In-memory (Rust):
  - `dashmap` - Concurrent hash map for form ID caches
  - `lru` - LRU cache for frequently accessed data
  - `quick_cache` - Lock-free concurrent cache for high-contention data
- In-memory (Python):
  - `ClassicLib/io/yaml/async_/cache.py` - YAML config caching with lazy loading
  - Dictionary-based memoization in performance-critical paths

## Authentication & Identity

**Auth Provider:**
- Custom (GitHub token is optional, not required for core functionality)
- `GITHUB_TOKEN` env var enables authenticated GitHub API requests
- No user login system; token-based API authentication only
- Implementation: `ClassicLib/support/update.py` includes token in request headers if present

**Windows Registry Access:**
- Optional Windows API integration via pywin32 (conditional import)
- Purpose: Extract game executable version info via Win32 API
- Functions: `ClassicLib/Utils/version_utils.py`:
  - `get_version_windows_api(game_exe_path)` - Extract version from .exe metadata
  - `extract_windows_version_info(win32api_module, exe_path)` - Parse Win32 file version info
- Fallback: Pure Python version extraction without API if pywin32 unavailable

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Rollbar, or similar)

**Logs:**
- Approach: `ClassicLib/core/logger.py` - Centralized Python logging module
- MessageHandler system for user-facing messages:
  - `msg_info()` - Information messages
  - `msg_warning()` - Warnings
  - `msg_error()` - Errors
  - `msg_success()` - Success messages
- Rust logging: `log` crate with optional `env_logger`, `tracing`, `tracing-subscriber`
- Output: Console (CLI/TUI) or GUI message dialogs (PySide6)

## CI/CD & Deployment

**Hosting:**
- GitHub repository: https://github.com/evildarkarchon/CLASSIC-Fallout4
- Distribution: Windows executable via GitHub Releases

**CI Pipeline:**
- GitHub Actions (not locally configured; inferred from project structure)
- Build artifact: PyInstaller-bundled Windows .exe in `CLASSIC/` directory

## Environment Configuration

**Required env vars:**
- `GITHUB_TOKEN` - GitHub API authentication token (optional, limits anonymous requests to 60/hour)

**Optional env vars:**
- Logging level configuration via standard Python logging env vars (inferred)

**Secrets location:**
- `.env` file in project root (git-ignored)
- Contains: `GITHUB_TOKEN=github_pat_*` for GitHub API authentication

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- GitHub API reads only (no outgoing webhooks or callbacks)

## PyO3 Rust-Python Bridge

**Module Loading:**
- Dynamic detection in `ClassicLib/integration/detector.py`
- Fallback to pure Python implementations if Rust modules unavailable
- Modules loaded as:
  - `import classic_yaml` → YAML operations
  - `import classic_database` → Database pooling
  - `import classic_scanlog` → Log parsing
  - `import classic_file_io` → Async file I/O
  - `import classic_settings` → Configuration
  - `import classic_registry` → Version registry

**Exception Types:**
- `RustDatabaseError` - Database operation failures
- `RustError` - General Rust errors with context
- Mapped to Python exception hierarchy in `ClassicLib/integration/exceptions.py`

## Threading & Async Model

**AsyncBridge:**
- Location: `ClassicLib/core/async_bridge.py`
- Purpose: Bridge async Rust code to Qt's event loop
- Usage: GUI contexts only (PySide6 slots → async function calls)
- Singleton pattern with thread-safe creation via double-checked locking

**Single Tokio Runtime:**
- Enforced via `classic-shared::get_runtime()` - all Rust async code uses same global runtime
- Prevents multiple runtime conflicts
- Available to Python via `classic-shared-py` Rust bindings

---

*Integration audit: 2026-01-29*
