# External Integrations

**Analysis Date:** 2026-04-04

## APIs & External Services

**Update Checking:**
- GitHub Releases API (`https://api.github.com`) — checks for new CLASSIC releases
  - SDK/Client: `reqwest 0.13.1` (async HTTP)
  - Auth: `GITHUB_TOKEN` env var (optional; loaded via `dotenvy` from `.env` file)
  - Endpoints used: `GET /repos/{owner}/{repo}/releases/latest` and `GET /repos/{owner}/{repo}/releases`
  - Unauthenticated rate limit: 60 req/hr; authenticated: 5,000 req/hr
  - Implementation: `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`

**Mod Distribution Sites (URL utilities only — no live API calls):**
- NexusMods (`https://www.nexusmods.com`) — URL construction and validation helpers
- Bethesda.net — URL helpers
  - SDK/Client: `url 2.5` crate for URL parsing/validation
  - Implementation: `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs`
  - Note: These are URL helper utilities only; no API authentication or live queries are made

## Data Storage

**Databases:**
- SQLite (local bundled) — FormID lookup databases for crash log analysis
  - Connection: local file path from config (not an env var); databases shipped with the app
  - Client: `sqlx 0.8` (async, runtime-tokio) for pool management and queries; `rusqlite 0.38.0` (bundled, backup) for synchronous paths
  - Implementation: `ClassicLib-rs/business-logic/classic-database-core/`
  - Database files: `CLASSIC Data/databases/` — shipped as static data assets (`.yaml`, game-specific lookup files)
  - Schema conventions: `docs/api/formid-sqlite-conventions.md`

**YAML Config Files:**
- Local YAML files (`CLASSIC Main.yaml`, `CLASSIC Fallout4.yaml`) — app settings and game-version metadata
  - Parser: `yaml-rust2 0.11.0` (custom; not serde_yaml)
  - Implementation: `ClassicLib-rs/business-logic/classic-yaml-core/`, `ClassicLib-rs/business-logic/classic-config-core/`
  - Runtime schema: `docs/api/classic-config-core-yaml-schema.md`

**File Storage:**
- Local filesystem only — crash logs read from user-specified directories
- Game files read from Windows game installation paths (discovered via registry or config)
- BA2 archive files parsed via `ba2 3.0.1`
- DDS texture files validated via `ddsfile 0.5`

**Caching:**
- In-process only — `quick_cache 0.6`, `lru 0.16.3`, `dashmap 6.1` for runtime caches
- No external cache service

## Authentication & Identity

**Auth Provider:**
- None for end users
- GitHub token optional for update-check rate limiting (developer/CI use)
  - Implementation: `dotenvy 0.15` loads `GITHUB_TOKEN` from `.env` at runtime in `classic-update-core`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Rollbar, or similar service integrated)

**Logs:**
- `log 0.4.29` facade + `env_logger 0.11` for Rust library logging
- `tracing 0.1.44` + `tracing-subscriber 0.3.22` + `tracing-appender 0.2` for structured/async-aware tracing
- TUI uses `tracing-appender` for file-backed log output
- Log output goes to stdout/stderr or rotating file; no remote log aggregation

## CI/CD & Deployment

**Hosting:**
- GitHub (`https://github.com/evildarkarchon/CLASSIC-Fallout4`) — source repository and release hosting

**CI Pipeline:**
- GitHub Actions (`windows-latest` runners for all jobs)
  - `ci-rust.yml` — rustfmt, clippy, build, test for Rust workspace
  - `ci-cpp.yml` — MSVC build, Catch2 CLI tests, Qt GUI tests via CTest
  - `ci-python-bindings.yml` — parity gates, maturin build, pytest smoke tests
  - `ci-typescript.yml` — NAPI-RS build, parity gates, Bun and Node runtime tests
  - `benchmarks.yml` — Criterion benchmark runs
- Caching: GitHub Actions cache for `~/.cargo/registry`, `~/.cargo/git`, `ClassicLib-rs/target`, vcpkg root and archives

**Distribution:**
- Releases published as GitHub Releases (ZIP packages via CPack for CLI; app bundle for GUI)
- Python wheels built with maturin (not published to PyPI; installed locally)
- Node addon distributed as `.node` binary alongside TypeScript types (`index.d.ts`)

## Windows Platform Integrations

**Windows Registry:**
- Read-only — game installation path discovery (Fallout 4 Steam/GOG paths)
- Implementation: `ClassicLib-rs/business-logic/classic-path-core/`

**PE File Parsing:**
- `pelite 0.10` — reads version resources from game executables and XSE loader DLLs to detect installed versions
- Implementation: `ClassicLib-rs/business-logic/classic-version-core/`

**MSVC Linker:**
- Required at build time; `tools/use_msvc_from_git_bash.sh` sets up environment so Git's `link.exe` does not shadow the VS linker

## Webhooks & Callbacks

**Incoming:**
- None — no HTTP server or webhook receiver

**Outgoing:**
- None — only outbound HTTP is the GitHub Releases API check (pull-only, no push/webhook)

## Environment Configuration

**Required env vars:**
- `VCPKG_ROOT` — must point to vcpkg installation for C++ builds

**Optional env vars:**
- `GITHUB_TOKEN` — GitHub personal access token; read from `.env` via `dotenvy` to increase update-check API rate limit

**Secrets location:**
- `.env` file at repo root (not committed; gitignored); used only for `GITHUB_TOKEN` during development/CI

---

*Integration audit: 2026-04-04*
