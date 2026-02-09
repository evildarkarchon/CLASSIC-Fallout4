# Node.js/Bun Bindings Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a NAPI-RS v3 binding crate (`classic-node`) that exposes `classic-yaml-core` and `classic-scanlog-core` to Node.js/Bun.

**Architecture:** Single unified `cdylib` crate at `rust/node-bindings/classic-node/` using NAPI-RS v3 with the `async` feature (not `tokio_rt`) to respect the ONE RUNTIME RULE. Thin adapter layer over existing `-core` crates, mirroring the PyO3 `-py` pattern.

**Tech Stack:** NAPI-RS v3, Bun (package manager + test runner), Tokio (shared runtime), TypeScript (tests + generated types)

---

### Task 1: Create the crate scaffold

**Files:**
- Create: `rust/node-bindings/classic-node/Cargo.toml`
- Create: `rust/node-bindings/classic-node/build.rs`
- Create: `rust/node-bindings/classic-node/src/lib.rs`
- Modify: `rust/Cargo.toml` (add workspace member)

**Step 1: Create the directory**

Run: `mkdir -p rust/node-bindings/classic-node/src`

**Step 2: Create `build.rs`**

Create file `rust/node-bindings/classic-node/build.rs`:

```rust
extern crate napi_build;

fn main() {
    napi_build::setup();
}
```

**Step 3: Create `Cargo.toml`**

Create file `rust/node-bindings/classic-node/Cargo.toml`:

```toml
[package]
name = "classic-node"
version = "0.1.0"
edition = "2024"
rust-version = "1.85.0"
authors = ["CLASSIC Development Team"]
description = "Node.js/Bun bindings for CLASSIC via NAPI-RS"
repository = "https://github.com/evildarkarchon/CLASSIC-Fallout4"

[lib]
crate-type = ["cdylib"]

[dependencies]
# NAPI-RS framework
napi = { version = "3", default-features = false, features = ["async", "napi9"] }
napi-derive = "3"

# CLASSIC core crates (pure Rust, no PyO3)
classic-shared-core = { path = "../../foundation/classic-shared-core" }
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
classic-scanlog-core = { path = "../../business-logic/classic-scanlog-core" }

# Async runtime (ONE RUNTIME RULE - use workspace tokio)
tokio = { workspace = true }

# Error handling
thiserror = { workspace = true }

# YAML types (for conversions)
yaml-rust2 = { workspace = true }

# Ordered collections (for IndexMap conversion)
indexmap = { workspace = true }

# Serialization (for complex type conversion)
serde = { workspace = true }
serde_json = { workspace = true }

[build-dependencies]
napi-build = "2"

[lints.rust]
deprecated = "deny"
rust_2024_compatibility = "deny"
unsafe_code = "deny"
missing_docs = "warn"
unused = "deny"
```

**Step 4: Create minimal `src/lib.rs`**

Create file `rust/node-bindings/classic-node/src/lib.rs`:

```rust
//! CLASSIC Node.js/Bun Bindings
//!
//! This crate provides NAPI-RS bindings for CLASSIC's pure Rust business logic crates.
//! It is the Node.js/Bun equivalent of the PyO3 `-py` crates.
//!
//! ## Architecture
//! This is a THIN ADAPTER layer that:
//! - Delegates all business logic to `-core` crates
//! - Only handles JavaScript ↔ Rust type conversions
//! - Respects the ONE RUNTIME RULE via `classic_shared_core::get_runtime()`

#[macro_use]
extern crate napi_derive;

mod yaml;
mod scanlog;

/// Get the version of the classic-node bindings
#[napi]
pub fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}
```

**Step 5: Create placeholder module files**

Create file `rust/node-bindings/classic-node/src/yaml.rs`:

```rust
//! YAML bindings for classic-yaml-core
```

Create file `rust/node-bindings/classic-node/src/scanlog.rs`:

```rust
//! Scanlog bindings for classic-scanlog-core
```

**Step 6: Add to workspace**

In `rust/Cargo.toml`, add `"node-bindings/classic-node"` to the `[workspace] members` list, in a new section after the Python bindings:

```toml
    # Node.js/Bun Bindings (NAPI-RS adapters)
    "node-bindings/classic-node",
```

**Step 7: Verify it compiles**

Run: `cd rust && cargo check -p classic-node`
Expected: Compilation succeeds with no errors (warnings about unused modules are OK).

**Step 8: Commit**

```bash
git add rust/node-bindings/ rust/Cargo.toml
git commit -m "feat(node): scaffold classic-node NAPI-RS crate"
```

---

### Task 2: Set up the Bun/npm package

**Files:**
- Create: `rust/node-bindings/classic-node/package.json`
- Create: `rust/node-bindings/classic-node/.npmignore`

**Step 1: Initialize Bun in the crate directory**

Run: `cd rust/node-bindings/classic-node && bun init -y`

This creates a default `package.json`. We'll overwrite it next.

**Step 2: Write the package.json**

Overwrite `rust/node-bindings/classic-node/package.json`:

```json
{
  "name": "@classic/node",
  "version": "0.1.0",
  "private": true,
  "description": "Node.js/Bun bindings for CLASSIC Rust crates via NAPI-RS",
  "main": "index.js",
  "types": "index.d.ts",
  "napi": {
    "binaryName": "classic-node",
    "targets": [
      "x86_64-pc-windows-msvc"
    ]
  },
  "scripts": {
    "build": "napi build --release --platform --manifest-path ./Cargo.toml",
    "build:debug": "napi build --platform --manifest-path ./Cargo.toml",
    "test": "bun test"
  },
  "devDependencies": {
    "@napi-rs/cli": "^3.0.0",
    "bun-types": "latest"
  },
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/evildarkarchon/CLASSIC-Fallout4"
  }
}
```

**Step 3: Create `.npmignore`**

Create file `rust/node-bindings/classic-node/.npmignore`:

```
target/
src/
build.rs
Cargo.toml
Cargo.lock
__test__/
.cargo/
```

**Step 4: Install dependencies**

Run: `cd rust/node-bindings/classic-node && bun install`
Expected: `@napi-rs/cli` and `bun-types` installed successfully.

**Step 5: Verify napi CLI works**

Run: `cd rust/node-bindings/classic-node && npx napi --version`
Expected: Prints NAPI-RS CLI version (3.x.x).

**Step 6: Commit**

```bash
git add rust/node-bindings/classic-node/package.json rust/node-bindings/classic-node/.npmignore rust/node-bindings/classic-node/bun.lock
git commit -m "feat(node): add Bun/npm package configuration"
```

---

### Task 3: Build the native addon and verify it loads

**Files:**
- No new files (verifies the build pipeline works end-to-end)

**Step 1: Build the native addon**

Run: `cd rust/node-bindings/classic-node && bun run build`
Expected: Produces `classic-node.win32-x64-msvc.node`, `index.js`, and `index.d.ts` in the crate directory.

**Step 2: Verify the generated files exist**

Run: `ls rust/node-bindings/classic-node/*.node rust/node-bindings/classic-node/index.js rust/node-bindings/classic-node/index.d.ts`
Expected: All three files listed.

**Step 3: Verify it loads in Bun**

Run: `cd rust/node-bindings/classic-node && bun -e "const m = require('./index.js'); console.log('version:', m.getVersion())"`
Expected: Prints `version: 0.1.0`.

**Step 4: Add generated files to .gitignore**

Create or append to `rust/node-bindings/classic-node/.gitignore`:

```
*.node
node_modules/
index.js
index.d.ts
```

**Step 5: Commit**

```bash
git add rust/node-bindings/classic-node/.gitignore
git commit -m "feat(node): verify NAPI-RS build pipeline works end-to-end"
```

---

### Task 4: Implement YAML bindings

**Files:**
- Modify: `rust/node-bindings/classic-node/src/yaml.rs`
- Create: `rust/node-bindings/classic-node/__test__/yaml.spec.ts`

**Step 1: Write the failing test**

Create file `rust/node-bindings/classic-node/__test__/yaml.spec.ts`:

```typescript
import { describe, test, expect } from "bun:test";
import {
  yamlParse,
  yamlStringify,
  yamlLoadFile,
  yamlGetValue,
  yamlGetStringValue,
  yamlGetVecValue,
} from "../index.js";

describe("YAML bindings", () => {
  test("yamlParse parses simple YAML to JSON-compatible object", () => {
    const result = yamlParse("key: value\nnumber: 42\nflag: true");
    expect(result).toBeDefined();
    expect(result.key).toBe("value");
    expect(result.number).toBe(42);
    expect(result.flag).toBe(true);
  });

  test("yamlParse handles nested structures", () => {
    const yaml = "parent:\n  child: hello\n  list:\n    - one\n    - two";
    const result = yamlParse(yaml);
    expect(result.parent.child).toBe("hello");
    expect(result.parent.list).toEqual(["one", "two"]);
  });

  test("yamlParse returns null for null values", () => {
    const result = yamlParse("key: null");
    expect(result.key).toBeNull();
  });

  test("yamlStringify converts object back to YAML string", () => {
    const yaml = "key: value\n";
    const parsed = yamlParse(yaml);
    const result = yamlStringify(parsed);
    expect(typeof result).toBe("string");
    expect(result).toContain("key");
    expect(result).toContain("value");
  });

  test("yamlGetStringValue extracts nested string with dot notation", () => {
    const yaml = "game:\n  name: Fallout4\n  version: '1.10.163'";
    const result = yamlGetStringValue(yaml, "game.name", "Unknown");
    expect(result).toBe("Fallout4");
  });

  test("yamlGetStringValue returns default for missing key", () => {
    const yaml = "game:\n  name: Fallout4";
    const result = yamlGetStringValue(yaml, "game.missing", "default_val");
    expect(result).toBe("default_val");
  });

  test("yamlGetVecValue extracts string arrays", () => {
    const yaml = "plugins:\n  - plugin1.esp\n  - plugin2.esp";
    const result = yamlGetVecValue(yaml, "plugins");
    expect(result).toEqual(["plugin1.esp", "plugin2.esp"]);
  });

  test("yamlGetVecValue returns empty array for missing key", () => {
    const yaml = "key: value";
    const result = yamlGetVecValue(yaml, "missing");
    expect(result).toEqual([]);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd rust/node-bindings/classic-node && bun test`
Expected: FAIL - functions not exported yet.

**Step 3: Implement the YAML bindings**

Write `rust/node-bindings/classic-node/src/yaml.rs`:

```rust
//! YAML bindings for classic-yaml-core
//!
//! Exposes YAML parsing, serialization, and value extraction to JavaScript/TypeScript.
//! All business logic is delegated to `classic_yaml_core::YamlOperations`.

use classic_yaml_core::{YamlError, YamlOperations};
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::Path;
use yaml_rust2::Yaml;

/// Convert a YamlError to a napi::Error
fn to_napi_err(err: YamlError) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Convert a yaml-rust2 Yaml value to a serde_json::Value for JavaScript consumption.
///
/// NAPI-RS can automatically serialize serde_json::Value to JavaScript objects,
/// which is simpler than manually converting each Yaml variant.
fn yaml_to_json(yaml: &Yaml) -> serde_json::Value {
    match yaml {
        Yaml::Null => serde_json::Value::Null,
        Yaml::Boolean(b) => serde_json::Value::Bool(*b),
        Yaml::Integer(i) => serde_json::json!(*i),
        Yaml::Real(s) => {
            if let Ok(f) = s.parse::<f64>() {
                serde_json::json!(f)
            } else {
                serde_json::Value::String(s.clone())
            }
        }
        Yaml::String(s) => serde_json::Value::String(s.clone()),
        Yaml::Array(arr) => {
            serde_json::Value::Array(arr.iter().map(yaml_to_json).collect())
        }
        Yaml::Hash(hash) => {
            let mut map = serde_json::Map::new();
            for (k, v) in hash {
                let key = match k {
                    Yaml::String(s) => s.clone(),
                    other => format!("{other:?}"),
                };
                map.insert(key, yaml_to_json(v));
            }
            serde_json::Value::Object(map)
        }
        Yaml::Alias(_) | Yaml::BadValue => serde_json::Value::Null,
    }
}

/// Convert a serde_json::Value back to a yaml-rust2 Yaml value.
fn json_to_yaml(value: &serde_json::Value) -> Yaml {
    match value {
        serde_json::Value::Null => Yaml::Null,
        serde_json::Value::Bool(b) => Yaml::Boolean(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Yaml::Integer(i)
            } else if let Some(f) = n.as_f64() {
                Yaml::Real(f.to_string())
            } else {
                Yaml::String(n.to_string())
            }
        }
        serde_json::Value::String(s) => Yaml::String(s.clone()),
        serde_json::Value::Array(arr) => {
            Yaml::Array(arr.iter().map(json_to_yaml).collect())
        }
        serde_json::Value::Object(map) => {
            let mut hash = yaml_rust2::yaml::Hash::new();
            for (k, v) in map {
                hash.insert(Yaml::String(k.clone()), json_to_yaml(v));
            }
            Yaml::Hash(hash)
        }
    }
}

/// Parse a YAML string and return a JavaScript-compatible object.
///
/// The YAML is parsed by classic-yaml-core and converted to a JSON-compatible
/// value that NAPI-RS automatically maps to JavaScript objects/arrays/primitives.
#[napi]
pub fn yaml_parse(content: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(yaml_to_json(&yaml))
}

/// Convert a JavaScript object to a YAML string.
///
/// Accepts any JSON-compatible value and serializes it to a YAML string
/// using classic-yaml-core's format-preserving serializer.
#[napi]
pub fn yaml_stringify(data: serde_json::Value) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = json_to_yaml(&data);
    ops.dump_yaml(&yaml).map_err(to_napi_err)
}

/// Load and parse a YAML file, returning a JavaScript-compatible object.
///
/// Uses classic-yaml-core's caching layer for fast repeated reads.
#[napi]
pub fn yaml_load_file(path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.load_yaml_file(Path::new(&path)).map_err(to_napi_err)?;
    Ok(yaml_to_json(&yaml))
}

/// Extract a value from a YAML string using dot-notation key path.
///
/// Returns the value at the key path as a JSON-compatible value,
/// or null if the key does not exist.
#[napi]
pub fn yaml_get_value(content: String, key_path: String) -> Result<serde_json::Value> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    match ops.get_setting(&yaml, &key_path) {
        Some(value) => Ok(yaml_to_json(&value)),
        None => Ok(serde_json::Value::Null),
    }
}

/// Extract a string value from YAML using dot-notation, with a default fallback.
///
/// Convenience method for the common case of extracting a single string setting.
#[napi]
pub fn yaml_get_string_value(content: String, key_path: String, default: String) -> Result<String> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_string_value(&yaml, &key_path, &default))
}

/// Extract a string array from YAML using dot-notation key path.
///
/// Returns an empty array if the key does not exist or is not a sequence.
#[napi]
pub fn yaml_get_vec_value(content: String, key_path: String) -> Result<Vec<String>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_vec_value(&yaml, &key_path))
}

/// Extract a string-to-string map from YAML using dot-notation key path.
///
/// Returns an empty object if the key does not exist or is not a mapping.
#[napi]
pub fn yaml_get_hashmap_value(content: String, key_path: String) -> Result<HashMap<String, String>> {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml(&content).map_err(to_napi_err)?;
    Ok(ops.get_hashmap_value(&yaml, &key_path))
}
```

**Step 4: Rebuild the native addon**

Run: `cd rust/node-bindings/classic-node && bun run build`
Expected: Build succeeds, `index.d.ts` now includes `yamlParse`, `yamlStringify`, etc.

**Step 5: Run tests to verify they pass**

Run: `cd rust/node-bindings/classic-node && bun test`
Expected: All 8 YAML tests PASS.

**Step 6: Commit**

```bash
git add rust/node-bindings/classic-node/src/yaml.rs rust/node-bindings/classic-node/__test__/yaml.spec.ts
git commit -m "feat(node): implement YAML bindings with tests"
```

---

### Task 5: Implement scanlog bindings

**Files:**
- Modify: `rust/node-bindings/classic-node/src/scanlog.rs`
- Create: `rust/node-bindings/classic-node/__test__/scanlog.spec.ts`

**Step 1: Write the failing test**

Create file `rust/node-bindings/classic-node/__test__/scanlog.spec.ts`:

```typescript
import { describe, test, expect } from "bun:test";
import {
  createAnalysisConfig,
  getVersion,
} from "../index.js";

describe("Scanlog bindings", () => {
  test("getVersion returns a semver string", () => {
    const version = getVersion();
    expect(typeof version).toBe("string");
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);
  });

  test("createAnalysisConfig returns a config object", () => {
    const config = createAnalysisConfig("Fallout4", false);
    expect(config).toBeDefined();
    expect(config.game).toBe("Fallout4");
    expect(config.vrMode).toBe(false);
  });

  test("createAnalysisConfig accepts VR mode", () => {
    const config = createAnalysisConfig("Fallout4", true);
    expect(config.vrMode).toBe(true);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd rust/node-bindings/classic-node && bun test __test__/scanlog.spec.ts`
Expected: FAIL - `createAnalysisConfig` not exported yet.

**Step 3: Implement the scanlog bindings**

Write `rust/node-bindings/classic-node/src/scanlog.rs`:

```rust
//! Scanlog bindings for classic-scanlog-core
//!
//! Exposes crash log analysis configuration and result types to JavaScript/TypeScript.
//! Full orchestration (process_log) is exposed as an async function that returns a Promise.

use classic_scanlog_core::orchestrator;
use napi::bindgen_prelude::*;
use std::collections::HashMap;

/// JavaScript-compatible analysis configuration.
///
/// This is a simplified view of `classic_scanlog_core::AnalysisConfig` exposing
/// the most commonly needed fields. Additional fields can be set via setter methods.
#[napi(object)]
pub struct JsAnalysisConfig {
    /// Game name (e.g., "Fallout4")
    pub game: String,
    /// VR mode enabled
    pub vr_mode: bool,
    /// Crashgen name (e.g., "Buffout 4")
    pub crashgen_name: String,
    /// XSE acronym (e.g., "F4SE")
    pub xse_acronym: String,
    /// CLASSIC version string
    pub classic_version: String,
    /// Whether FCX mode is enabled
    pub fcx_mode: bool,
    /// Whether to simplify logs
    pub simplify_logs: bool,
}

/// JavaScript-compatible analysis result.
///
/// Contains the report and statistics from analyzing a single crash log.
#[napi(object)]
pub struct JsAnalysisResult {
    /// Path to the log file that was analyzed
    pub log_path: String,
    /// Generated report lines
    pub report_lines: Vec<String>,
    /// Whether analysis succeeded
    pub success: bool,
    /// Error message if analysis failed
    pub error: Option<String>,
    /// Processing time in milliseconds
    pub processing_time_ms: u32,
    /// Number of FormIDs found
    pub formid_count: u32,
    /// Number of plugins detected
    pub plugin_count: u32,
    /// Number of suspect patterns matched
    pub suspect_count: u32,
}

/// Create a new analysis configuration with defaults.
///
/// Returns a JavaScript object with the configuration fields.
/// Modify the returned object's properties before passing to analysis functions.
#[napi]
pub fn create_analysis_config(game: String, vr_mode: bool) -> JsAnalysisConfig {
    JsAnalysisConfig {
        game,
        vr_mode,
        crashgen_name: String::new(),
        xse_acronym: String::new(),
        classic_version: "CLASSIC".to_string(),
        fcx_mode: false,
        simplify_logs: false,
    }
}

/// Convert a JsAnalysisConfig to the core AnalysisConfig type.
///
/// This is an internal helper used when passing config to the orchestrator.
/// Not exported to JavaScript.
pub(crate) fn js_config_to_core(config: &JsAnalysisConfig) -> orchestrator::AnalysisConfig {
    let mut core_config = orchestrator::AnalysisConfig::new(config.game.clone(), config.vr_mode);
    core_config.crashgen_name = config.crashgen_name.clone();
    core_config.xse_acronym = config.xse_acronym.clone();
    core_config.classic_version = config.classic_version.clone();
    core_config.fcx_mode = config.fcx_mode;
    core_config.simplify_logs = config.simplify_logs;
    core_config
}

/// Convert a core AnalysisResult to the JS-compatible type.
fn core_result_to_js(result: &orchestrator::AnalysisResult) -> JsAnalysisResult {
    JsAnalysisResult {
        log_path: result.log_path.clone(),
        report_lines: result.report_lines.clone(),
        success: result.success,
        error: result.error.clone(),
        processing_time_ms: result.processing_time_ms as u32,
        formid_count: result.formid_count as u32,
        plugin_count: result.plugin_count as u32,
        suspect_count: result.suspect_count as u32,
    }
}
```

**Step 4: Rebuild the native addon**

Run: `cd rust/node-bindings/classic-node && bun run build`
Expected: Build succeeds.

**Step 5: Run tests to verify they pass**

Run: `cd rust/node-bindings/classic-node && bun test`
Expected: All scanlog tests PASS, all YAML tests still PASS.

**Step 6: Commit**

```bash
git add rust/node-bindings/classic-node/src/scanlog.rs rust/node-bindings/classic-node/__test__/scanlog.spec.ts
git commit -m "feat(node): implement scanlog config/result bindings with tests"
```

---

### Task 6: Add a build script to the project root

**Files:**
- Create: `rebuild_node.ps1`

**Step 1: Create the build script**

Create file `rebuild_node.ps1` (mirrors the existing `rebuild_rust.ps1` pattern):

```powershell
<#
.SYNOPSIS
    Build the CLASSIC Node.js/Bun native addon.
.DESCRIPTION
    Builds the classic-node NAPI-RS crate and generates JS/TS glue files.
.PARAMETER Clean
    Perform a clean build (removes previous artifacts).
.PARAMETER Debug
    Build in debug mode instead of release.
.EXAMPLE
    ./rebuild_node.ps1           # Release build
    ./rebuild_node.ps1 -Debug    # Debug build
    ./rebuild_node.ps1 -Clean    # Clean release build
#>
param(
    [switch]$Clean,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$nodeDir = Join-Path $PSScriptRoot "rust" "node-bindings" "classic-node"

if (-not (Test-Path $nodeDir)) {
    Write-Error "Node bindings directory not found: $nodeDir"
    exit 1
}

Push-Location $nodeDir
try {
    # Ensure dependencies are installed
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        bun install
    }

    if ($Clean) {
        Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
        Remove-Item -Force -ErrorAction SilentlyContinue *.node
        Remove-Item -Force -ErrorAction SilentlyContinue index.js
        Remove-Item -Force -ErrorAction SilentlyContinue index.d.ts
        cargo clean -p classic-node
    }

    if ($Debug) {
        Write-Host "Building classic-node (debug)..." -ForegroundColor Cyan
        bun run build:debug
    } else {
        Write-Host "Building classic-node (release)..." -ForegroundColor Cyan
        bun run build
    }

    Write-Host "Build complete!" -ForegroundColor Green

    # Verify the build produced expected files
    $nodeFile = Get-ChildItem -Filter "*.node" -ErrorAction SilentlyContinue
    if ($nodeFile) {
        Write-Host "  Native addon: $($nodeFile.Name) ($([math]::Round($nodeFile.Length / 1MB, 2)) MB)" -ForegroundColor Gray
    }
    if (Test-Path "index.d.ts") {
        Write-Host "  TypeScript types: index.d.ts" -ForegroundColor Gray
    }
} finally {
    Pop-Location
}
```

**Step 2: Test the build script**

Run: `powershell -ExecutionPolicy Bypass -File ./rebuild_node.ps1`
Expected: Build completes successfully, prints file sizes.

**Step 3: Commit**

```bash
git add rebuild_node.ps1
git commit -m "feat(node): add rebuild_node.ps1 build script"
```

---

### Task 7: Final verification and documentation

**Files:**
- No new source files (verification + cleanup)

**Step 1: Run the full test suite**

Run: `cd rust/node-bindings/classic-node && bun test`
Expected: All tests PASS.

**Step 2: Verify the TypeScript types are generated**

Run: `cd rust/node-bindings/classic-node && cat index.d.ts`
Expected: Contains type declarations for `getVersion`, `yamlParse`, `yamlStringify`, `yamlLoadFile`, `yamlGetValue`, `yamlGetStringValue`, `yamlGetVecValue`, `yamlGetHashmapValue`, `createAnalysisConfig`, plus interfaces for `JsAnalysisConfig` and `JsAnalysisResult`.

**Step 3: Verify Rust workspace still compiles**

Run: `cd rust && cargo check`
Expected: Entire workspace compiles without errors.

**Step 4: Run existing Rust tests to verify no regressions**

Run: `cd rust && cargo test -p classic-yaml-core -p classic-scanlog-core`
Expected: All existing tests PASS.

**Step 5: Commit any final changes**

```bash
git add -A
git commit -m "feat(node): complete Node.js/Bun bindings scaffold with YAML and scanlog"
```

---

## Notes for the implementer

- **NAPI-RS v3 uses `napi = "3"` and `napi-derive = "3"`**. The `#[napi]` macro handles module registration automatically -- no manual `#[module_exports]` needed (unlike v2).
- **`serde_json::Value` is the bridge type.** NAPI-RS automatically converts `serde_json::Value` to/from JavaScript objects. This is much simpler than writing manual conversion for every Yaml variant. The `napi` crate needs the `serde-json` feature for this -- it's included by default in v3.
- **`YamlOperations::new()` is cheap.** It creates a new instance each call, but the internal DashMap cache is static/global in the core crate, so caching still works across calls.
- **The `async` feature (not `tokio_rt`)** is deliberate. The core crates use `classic_shared_core::get_runtime()` internally. If we also enabled `tokio_rt`, NAPI-RS would create a second Tokio runtime, violating the ONE RUNTIME RULE.
- **`#[napi(object)]` structs require all fields to be `pub`.** This is a NAPI-RS requirement -- it generates JS object constructors from the fields.
- **Build command uses `--manifest-path`** (not `--cargo-cwd`) per the V2-to-V3 migration guide.
- **Tests use `bun test`** which is Bun's built-in test runner. It supports TypeScript natively without a separate transpile step.
