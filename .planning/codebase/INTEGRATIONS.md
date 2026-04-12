# External Integrations

**Analysis Date:** 2026-04-11

## APIs & External Services

**Release / update services:**
- GitHub Releases API - checks latest CLASSIC releases and compares versions.
  - SDK/Client: `reqwest` in `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`
  - Auth: `GITHUB_TOKEN` loaded from environment or optional repo-root `.env` in `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`
  - Consumers: `ClassicLib-rs/ui-applications/classic-tui/src/app.rs`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/update.rs`, and `ClassicLib-rs/python-bindings/classic-update-py/src/github.rs`

**Mod ecosystem links:**
- Nexus Mods - canonical download/help/update URLs are modeled in `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs`, version registry metadata in `ClassicLib-rs/business-logic/classic-version-registry-core/src/registry.rs`, GUI help buttons in `classic-gui/src/app/mainwindow.cpp`, and README/install docs in `README.md`.
  - SDK/Client: no API SDK detected; links and URL helpers are source-defined
  - Auth: none detected
- Bethesda.net - mod site URL constants are defined in `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` and surfaced through bindings in `ClassicLib-rs/node-bindings/classic-node/src/web.rs` and `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs`.
  - SDK/Client: none detected
  - Auth: none detected
- ModDB - mod site URL constants are defined in `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs`.
  - SDK/Client: none detected
  - Auth: none detected

**Developer platform services:**
- GitHub Actions - CI/CD orchestration for Rust, C++, Python bindings, Node bindings, and benchmarks via `.github/workflows/ci-rust.yml`, `.github/workflows/ci-cpp.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, and `.github/workflows/benchmarks.yml`.
  - SDK/Client: GitHub-hosted workflow runner actions
  - Auth: repository-managed GitHub Actions credentials; no repo-local secret values inspected

## Data Storage

**Databases:**
- SQLite - local FormID and scan-support databases are accessed through `sqlx` and `rusqlite` in `ClassicLib-rs/Cargo.toml` and implemented in `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`.
  - Connection: file-path based SQLite URLs like `sqlite://...` in `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`
  - Client: `sqlx` async pools plus `rusqlite` support from `ClassicLib-rs/Cargo.toml`
- Runtime database assets - packaged data directories are installed from `CLASSIC Data/databases/` by `classic-cli/CMakeLists.txt`; this is repo-managed local data, not a hosted DB service.

**File Storage:**
- Local filesystem only - crash logs, generated reports, packaged help/assets, and local databases live in repo/runtime directories such as `Crash Logs/`, `CLASSIC Data/`, and paths created/opened by `ClassicLib-rs/ui-applications/classic-tui/src/app.rs` and `classic-gui/src/controllers/resultscontroller.cpp`.

**Caching:**
- In-process caches only - TTL query/result caches and pool bookkeeping are implemented in `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs` using `DashMap`, `lru`, and related Rust crates from `ClassicLib-rs/Cargo.toml`.

## Authentication & Identity

**Auth Provider:**
- Custom token header flow for GitHub only.
  - Implementation: `ClassicLib-rs/business-logic/classic-update-core/src/github.rs` conditionally adds `Authorization: Bearer <token>` when `GITHUB_TOKEN` is present.
- No user login, OAuth provider, or session identity service was detected in `classic-cli/`, `classic-gui/`, or `ClassicLib-rs/`.

## Monitoring & Observability

**Error Tracking:**
- None detected as an external SaaS. No Sentry, Honeycomb, App Insights, Datadog, or Rollbar integration was found in `ClassicLib-rs/`, `classic-cli/`, `classic-gui/`, or `.github/workflows/`.

**Logs:**
- Local structured/runtime logging uses Rust logging crates (`log`, `env_logger`, `tracing`, `tracing-subscriber`, `tracing-appender`) declared in `ClassicLib-rs/Cargo.toml`.
- Extra scan diagnostics are environment-controlled through `CLASSIC_SCAN_DIAGNOSTICS` and `CLASSIC_DB_COUNTER_INTERVAL` in `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` and `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`.
- Failure diagnostics are uploaded as CI artifacts in `.github/workflows/ci-cpp.yml`, `.github/workflows/ci-python-bindings.yml`, and `.github/workflows/ci-typescript.yml`.

## CI/CD & Deployment

**Hosting:**
- GitHub repository + GitHub Releases are the only externally hosted delivery surfaces directly referenced in code and docs, including `README.md`, `classic-gui/src/app/mainwindow.cpp`, and `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`.
- Native desktop binaries are packaged locally as ZIP artifacts through CPack in `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt`.

**CI Pipeline:**
- GitHub Actions - source of truth for automated validation and benchmark gating in `.github/workflows/*.yml`.
- vcpkg bootstrap is automated through `.github/scripts/setup-vcpkg.ps1`.

## Environment Configuration

**Required env vars:**
- `VCPKG_ROOT` - required for native C++/Qt builds in `classic-cli/build_cli.ps1`, `classic-cli/CMakePresets.json`, and `classic-gui/CMakePresets.json`
- `GITHUB_TOKEN` - optional but actively consumed for authenticated GitHub API update checks in `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`
- `CLASSIC_SCAN_DIAGNOSTICS` - optional diagnostic toggle in `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs`
- `CLASSIC_DB_COUNTER_INTERVAL` - optional diagnostic/logging interval in `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- `QT_QPA_PLATFORM` - set to `offscreen` in GUI CI at `.github/workflows/ci-cpp.yml`

**Secrets location:**
- Repo-root `.env` and `.env.example` exist and are relevant to update-token configuration, but their contents were not read.
- GitHub Actions secrets, if configured, are external to the repository and consumed by workflow runtime rather than checked-in files.

## Webhooks & Callbacks

**Incoming:**
- None detected. No HTTP server, webhook endpoint, or callback receiver was found in `classic-cli/`, `classic-gui/`, or `ClassicLib-rs/`.

**Outgoing:**
- GitHub REST requests to `https://api.github.com/repos/{owner}/{repo}/releases/latest` in `ClassicLib-rs/business-logic/classic-update-core/src/github.rs`.
- Desktop/browser handoff to external URLs via `QDesktopServices::openUrl` in `classic-gui/src/app/mainwindow.cpp`.
- No outbound webhook posting integration was detected.

---

*Integration audit: 2026-04-11*
