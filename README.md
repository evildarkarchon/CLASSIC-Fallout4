# CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker)

## Overview

CLASSIC analyzes crash logs and game/mod setups for Bethesda titles (currently Fallout 4, with Skyrim support in progress). It provides detailed diagnostics and remediation guidance across hundreds of automated checks.

As of the current codebase, CLASSIC is a **native C++ + Rust application**:

- **GUI:** `classic-gui/` (Qt 6, C++)
- **CLI:** `classic-cli/` (C++)
- **Business logic:** `ClassicLib-rs/` (Rust workspace)
- **C++ ↔ Rust bridge:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`

Maintained Python integration bindings exist under **`ClassicLib-rs/python-bindings/`** for integration scenarios.

For older historical context, see [CLASSIC - Readme.pdf](CLASSIC%20-%20Readme.pdf).

Nexus Mods: <https://www.nexusmods.com/fallout4/mods/56255>

---

## Requirements

### Fallout 4

[*Detailed Buffout 4 installation instructions*](https://www.nexusmods.com/fallout4/articles/3115)

- [Fallout 4 Script Extender](https://www.nexusmods.com/fallout4/mods/42147?tab=files)
- [Address Library for F4SE Plugins](https://www.nexusmods.com/fallout4/mods/47327?tab=files)
- [Buffout 4 NG](https://www.nexusmods.com/fallout4/mods/64880?tab=files) (OG/NG/VR), [Buffout 4](https://www.nexusmods.com/fallout4/mods/47359) (OG), or [Addictol](https://www.nexusmods.com/fallout4/mods/84214) (OG/NG/AE)
- [BSArch](https://www.nexusmods.com/newvegas/mods/64745?tab=files) (required for some file scan workflows)

### Skyrim (work in progress)

- [Skyrim Script Extender](https://www.nexusmods.com/skyrimspecialedition/mods/30379?tab=files)
- [Address Library for SKSE Plugins](https://www.nexusmods.com/skyrimspecialedition/mods/32444?tab=files)
- [Crash Logger AE for VR](https://www.nexusmods.com/skyrimspecialedition/mods/59818?tab=files)
- [BSArch](https://www.nexusmods.com/newvegas/mods/64745?tab=files)

---

## Installation

### Option 1 (Recommended): Download prebuilt release

1. Open the [latest release](https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest)
2. Download the `.7z` archive from **Assets**
3. Extract with [7-Zip](https://www.7-zip.org/)
4. Run:
   - `CLASSIC.exe` for GUI
   - `classic-cli.exe` for CLI

Release bundles include `CLASSIC Data/` and required runtime files.

### Option 2: Build from source (Windows)

#### Prerequisites

- Visual Studio with C++ Desktop workload (MSVC toolchain)
- [vcpkg](https://vcpkg.io/)
- `VCPKG_ROOT` environment variable configured (example: `C:\vcpkg`)
- Rust toolchain (`cargo`)
- CMake 3.25+
- Ninja
- Qt 6 (for GUI)

#### Build CLI

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1
```

#### Build GUI

```powershell
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1
```

#### Build with tests

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

CLI integration tests use crash-log fixtures from `sample_logs/FO4` (git submodule). Initialize submodules before running tests:

```powershell
git submodule update --init --recursive
```

Alternatively, run integration tests with an explicit fixture path via `classic-cli/test_cli.ps1 -TestDataDir <path>`.

---

## Development quick reference

### Rust workspace (`ClassicLib-rs/`)

```powershell
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

### C++ apps

```powershell
# CLI
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1

# GUI
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1
```

Use the build scripts instead of raw CMake commands so VS Dev Shell is initialized correctly.

---

## CI

GitHub Actions workflows:

- `ci-cpp.yml` - C++ CLI/GUI build and test pipeline on `windows-latest`
- `ci-rust.yml` - Rust format/lint/build/test
- `ci-typescript.yml` - Node bindings parity gates + Bun/Node runtime tests
- `ci-python-bindings.yml` - Python bindings parity gates + smoke tests
- `benchmarks.yml` - benchmark/performance pipeline

---

## Repository layout

- `classic-cli/` — C++ command-line scanner
- `classic-gui/` — C++ Qt 6 desktop GUI
- `ClassicLib-rs/` — Rust business logic + bindings
- `CLASSIC Data/` — runtime data, databases, help, graphics

---

## Contributing

1. Keep C++ changes in `classic-cli/` or `classic-gui/` focused and testable.
2. Keep core logic in Rust crates under `ClassicLib-rs/business-logic/`.
3. Run relevant C++/Rust checks before opening a PR.
4. Keep docs aligned with architecture changes (especially this README and `AGENTS.md`).
