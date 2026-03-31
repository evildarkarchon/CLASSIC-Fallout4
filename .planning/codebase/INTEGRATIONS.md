# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**GitHub Releases API:**
- Used for: checking for new CLASSIC releases and downloading update metadata
- SDK/Client: `reqwest` 0.13.1 (async HTTP)
- Crate: `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`
- Auth: `GITHUB_TOKEN` env var (optional); loaded via `dotenvy` from `.env` file
- Endpoint: `https://api.github.com/repos/evildarkarchon/CLASSIC-Fallout4/releases/latest`
- Rate limit: 60 req/hr unauthenticated, 5,000 req/hr with token
- User-agent: `CLASSIC-Update/<version>`

**Mod Site URL Helpers (reference only — no live API calls):**
- NexusMods (`https://www.nexusmods.com`) — URL validation and domain extraction
- Bethesda.net (`https://bethesda.net`) — URL validation and domain extraction
- ModDB (`https://www.moddb.com`) — URL validation and domain extraction
- Crate: `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` (`ModSite` enum)
- These are URL utilities only; no API key or HTTP calls are made to these services

## Data Storage

**Databases:**
- Type: SQLite (local file-based, no server)
- Client: `sqlx` 0.8 (async, WAL mode) + `rusqlite` 0.38.0 (bundled, sync fallback)
- Pool crate: `ClassicLib-rs/business-logic/classic-database-core/`
- Location: `CLASSIC Data/databases/` (shipped with application)
- Known databases:
  - `Fallout4 FormIDs Main.db` — base game FormID lookup
  - `Fallout4 FormIDs Local.db` — local/user FormID database
  - `aSW FormIDs.db` — additional mod FormID database
  - `FOLON FormIDs.db` — Fallout London mod FormIDs
  - `FormIDs.db` — general FormID database
- User-configured paths: `CLASSIC Settings.yaml` under `CLASSIC_Settings.FormID Databases`
- Access pattern: async connection pool with TTL-based query caching and WAL concurrency

**File Storage:**
- Local filesystem only — no cloud storage integration
- Game archive reading: Bethesda BA2 archives via `ba2` 3.0.1 crate (read-only)
- Log collection: crash log files from game documents directory or custom scan path

**Caching:**
- In-process only — `quick_cache` 0.6 (lock-free), `lru` 0.16.3
- YAML file cache keyed by path + mtime (in `classic-yaml-core`)
- Settings cache with sync/async loaders (in `classic-settings-core`)
- No external cache service (Redis, Memcached, etc.)

## Authentication & Identity

**Auth Provider:**
- None — application does not authenticate users
- `GITHUB_TOKEN` is an optional developer/CI token for raising API rate limits (not user auth)

## Game Platform Integrations

**Steam (Windows):**
- Integration: Windows Registry reads (`HKEY_LOCAL_MACHINE`) to locate game installation path
- Crate: `ClassicLib-rs/business-logic/classic-path-core/src/platform/windows.rs`
- Dependency: `winreg` 0.52 (Windows target only)

**Steam (Linux/Proton):**
- Integration: Steam library VDF file parsing (`~/.local/share/Steam/steamapps/libraryfolders.vdf`)
- Crate: `ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs`
- No external library; custom VDF parser

**GOG:**
- Integration: Windows Registry reads alongside Steam paths
- Crate: `ClassicLib-rs/business-logic/classic-path-core/src/game_path.rs`

## File Format Integrations

**Bethesda BA2 Archives:**
- Format: Fallout 4 BA2 (GNRL general and DX10 texture formats)
- Library: `ba2` 3.0.1
- Used by: `ClassicLib-rs/business-logic/classic-scangame-core/src/ba2.rs`
- Purpose: scanning game archives for file presence and validation

**PE (Windows Portable Executable) Files:**
- Format: Windows `.exe`/`.dll` version resources (`VS_VERSIONINFO`)
- Library: `pelite` 0.10
- Used by: `ClassicLib-rs/business-logic/classic-version-core/src/pe_version.rs`
- Purpose: extracting game version from `Fallout4.exe` and XSE loader DLLs

**DDS Texture Files:**
- Library: `ddsfile` 0.5
- Purpose: texture file validation in loose-file scanning

**INI Files:**
- Library: `configparser` 3.1
- Purpose: parsing Fallout 4 `.ini` configuration files (game settings discovery)
- Used by: `ClassicLib-rs/business-logic/classic-path-core/`

## Monitoring & Observability

**Error Tracking:**
- None — no external error tracking service (Sentry, Bugsnag, etc.)

**Logs:**
- Rust: `log` 0.4.29 facade + `env_logger` 0.11` for environment-driven log levels
- Rust async: `tracing` 0.1.44 + `tracing-subscriber` 0.3.22 + `tracing-appender` 0.2 for structured async-aware logging with file appender support
- TUI: tracing with file appender (`ClassicLib-rs/ui-applications/classic-tui/`)

## CI/CD & Deployment

**Hosting:**
- GitHub: `https://github.com/evildarkarchon/CLASSIC-Fallout4`
- Releases distributed as standalone Windows ZIP archives via GitHub Releases

**CI Pipeline:**
- GitHub Actions (`.github/workflows/`)
- `ci-rust.yml` — rustfmt, Clippy, Rust tests (runs on `windows-latest`)
- `ci-cpp.yml` — C++ CLI and GUI builds + CTest/Catch2/QtTest (runs on `windows-latest`, uses `ilammy/msvc-dev-cmd@v1`)
- `ci-python-bindings.yml` — Python parity gates, stub validation, pytest (runs on `windows-latest`, uses `astral-sh/setup-uv@v7`)
- `ci-typescript.yml` — Node parity gates, Bun tests, DTS freshness (runs on `windows-latest`, uses `oven-sh/setup-bun@v2`)
- `benchmarks.yml` — Criterion benchmarks on PRs to `main` with PR comment reporting

**CI Build Caching:**
- `actions/cache@v5` for `~/.cargo/registry` and `~/.cargo/git`, keyed by `Cargo.lock` hash
- Python venv cached by `astral-sh/setup-uv@v7`

## Webhooks & Callbacks

**Incoming:**
- None — the application does not expose any web endpoints

**Outgoing:**
- GitHub API: outgoing HTTPS GET to `api.github.com` for release checks (user-triggered or automated at startup when `Update Check: true` in settings)

## Environment Configuration

**Required env vars (build/dev):**
- `VCPKG_ROOT` — path to vcpkg installation (required for C++ builds)

**Optional env vars (runtime):**
- `GITHUB_TOKEN` — GitHub personal access token for higher API rate limit; loaded from `.env` by `dotenvy` in `classic-update-core`
- `RUST_BACKTRACE` — Rust panic backtraces (set to `1` or `full` in CI)
- `CARGO_TERM_COLOR` — Cargo output coloring (set to `always` in CI)

**Secrets location:**
- `.env` file at repo root (gitignored) — stores `GITHUB_TOKEN` for local development
- GitHub Actions secrets — `GITHUB_TOKEN` injected as workflow env for CI

---

*Integration audit: 2026-03-30*
