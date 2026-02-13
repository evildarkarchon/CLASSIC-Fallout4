# Node.js/Bun Bindings for CLASSIC Rust Crates

**Date:** 2026-02-08
**Status:** Approved

## Goal

Add Node.js/Bun bindings to the existing pure-Rust `-core` crates using NAPI-RS v3. This creates a parallel binding layer alongside the existing PyO3 `-py` crates, enabling CLASSIC's Rust-accelerated functionality to be consumed from JavaScript/TypeScript.

The initial scope is infrastructure scaffolding with a minimal proof-of-concept API. Specific use cases (web tooling, API server, library distribution) will be decided later.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Binding technology | NAPI-RS v3 | Mature, Bun-native, mirrors PyO3 pattern |
| Crate structure | Single unified `classic-node` | Less boilerplate; can split later |
| Location | `ClassicLib-rs/node-bindings/classic-node/` | Parallel to `python-bindings/` |
| Initial crates bound | `classic-yaml-core`, `classic-scanlog-core` | High-value + proves sync/async |
| Runtime strategy | `async` feature (not `tokio_rt`) | Respects ONE RUNTIME RULE |
| Package manager | Bun | User preference |
| Target platform | `x86_64-pc-windows-msvc` | Development platform; expand later |
| npm publishing | Private (`"private": true`) | No distribution story yet |

## Architecture

### Crate Location and Structure

```
ClassicLib-rs/node-bindings/classic-node/
├── Cargo.toml          # Rust crate (cdylib)
├── package.json        # npm/Bun package
├── build.rs            # napi-build codegen
├── src/
│   ├── lib.rs          # NAPI module registration + re-exports
│   ├── yaml.rs         # Bindings for classic-yaml-core
│   └── scanlog.rs      # Bindings for classic-scanlog-core
├── __test__/
│   └── index.spec.ts   # Bun test suite
└── index.js            # Generated JS glue (napi build output)
```

The crate produces a `cdylib` (`.node` shared library). NAPI-RS auto-generates `index.js` (loader), `index.d.ts` (TypeScript types), and the platform-specific `.node` binary.

### Dependency Graph

```
classic-node (cdylib, NAPI-RS)
├── classic-yaml-core (rlib, pure Rust)
│   └── classic-shared-core
├── classic-scanlog-core (rlib, pure Rust)
│   ├── classic-shared-core
│   ├── classic-yaml-core
│   ├── classic-file-io-core
│   └── classic-database-core
└── classic-shared-core (rlib, pure Rust)
```

No PyO3 dependency anywhere in this chain.

### Cargo Configuration

```toml
[package]
name = "classic-node"
version = "0.1.0"
edition = "2024"
rust-version = "1.85.0"
description = "Node.js/Bun bindings for CLASSIC via NAPI-RS"

[lib]
crate-type = ["cdylib"]

[dependencies]
napi = { version = "3", features = ["async", "napi9"] }
napi-derive = "3"
classic-shared-core = { path = "../../foundation/classic-shared-core" }
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
classic-scanlog-core = { path = "../../business-logic/classic-scanlog-core" }
tokio = { workspace = true }
thiserror = { workspace = true }
anyhow = { workspace = true }

[build-dependencies]
napi-build = "2"
```

- `napi9` targets Node 18+ and Bun 1.x
- `async` feature (not `tokio_rt`) avoids spinning up a second Tokio runtime

### Runtime Management

The `-core` crates internally use `classic_shared::get_runtime()` for the global Tokio runtime. NAPI-RS's `async` feature uses a libuv-based executor for top-level async dispatch, so there is no runtime conflict.

```rust
// Sync: called from Node's main thread, safe to block_on
#[napi]
pub fn load_yaml_sync(path: String) -> napi::Result<String> {
    let rt = classic_shared_core::get_runtime();
    rt.block_on(async {
        classic_yaml_core::load_yaml_file(&path).await
    }).map_err(|e| napi::Error::from_reason(e.to_string()))
}

// Async: returns JS Promise, core crates use get_runtime() internally
#[napi]
pub async fn load_yaml(path: String) -> napi::Result<String> {
    classic_yaml_core::load_yaml_file(&path)
        .await
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}
```

### Package Configuration

```json
{
  "name": "@classic/node",
  "version": "0.1.0",
  "private": true,
  "main": "index.js",
  "types": "index.d.ts",
  "napi": {
    "binaryName": "classic-node",
    "targets": ["x86_64-pc-windows-msvc"]
  },
  "scripts": {
    "build": "napi build --release --platform",
    "build:debug": "napi build --platform",
    "test": "bun test"
  },
  "devDependencies": {
    "@napi-rs/cli": "^3.0.0",
    "bun-types": "latest"
  }
}
```

## Initial API Surface

### YAML Bindings (yaml.rs)

```rust
#[napi(object)]
pub struct YamlDocument { /* wraps core type */ }

#[napi]
pub async fn load_yaml(path: String) -> napi::Result<YamlDocument>;

#[napi]
pub fn load_yaml_string(content: String) -> napi::Result<YamlDocument>;

#[napi]
pub fn get_yaml_value(doc: &YamlDocument, key: String) -> napi::Result<Option<String>>;
```

### Scanlog Bindings (scanlog.rs)

```rust
#[napi(object)]
pub struct ScanResult { /* wraps core scan output */ }

#[napi]
pub async fn scan_log_file(path: String) -> napi::Result<ScanResult>;

#[napi]
pub fn get_version() -> String;
```

### What This Proves

- Sync and async functions both work through NAPI-RS
- Struct wrapping via `#[napi(object)]` produces TypeScript interfaces
- Full pipeline: TypeScript -> `.node` addon -> `-core` crate -> shared Tokio runtime -> JS Promise

## Testing

Bun test runner with integration tests in `__test__/index.spec.ts`:

```typescript
import { describe, test, expect } from "bun:test";
import { loadYaml, loadYamlString, getVersion, scanLogFile } from "../index.js";

describe("classic-node", () => {
  test("getVersion returns a string", () => {
    expect(typeof getVersion()).toBe("string");
  });

  test("loadYamlString parses YAML content", () => {
    const doc = loadYamlString("key: value");
    expect(doc).toBeDefined();
  });

  test("loadYaml reads a file", async () => {
    const doc = await loadYaml("path/to/fixture.yaml");
    expect(doc).toBeDefined();
  });

  test("scanLogFile returns results", async () => {
    const result = await scanLogFile("path/to/fixture.log");
    expect(result).toBeDefined();
  });
});
```

## Build Workflow

```bash
cd ClassicLib-rs/node-bindings/classic-node
bun install                  # install @napi-rs/cli
bun run build                # compile Rust + generate JS/TS glue
bun test                     # run tests
```

## Future Expansion

- Add more `-core` crate bindings (same pattern, add modules to `src/`)
- Cross-platform targets via CI matrix
- Streaming APIs via `ThreadsafeFunction`
- npm publishing if distribution is needed
- Split into per-crate packages if modularity matters
