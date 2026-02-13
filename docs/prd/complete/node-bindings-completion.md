# PRD: Node.js/Bun Bindings Completion for CLASSIC Rust Crates

**Status**: Draft
**Author**: PRD Writer Agent
**Date**: 2026-02-09
**Version**: 1.0
**Target Package**: `@classic/node` (NAPI-RS v3)

---

## 1. Executive Summary

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4, Skyrim). The Rust workspace contains 19 business-logic `-core` crates, all of which have complete Python bindings via PyO3. A Node.js/Bun binding layer was started using NAPI-RS v3, but currently only exposes a fraction of the available API surface.

This PRD defines the requirements for completing the `@classic/node` package so that every business-logic crate is accessible from Node.js and Bun. The completed package will enable:

- **Third-party tooling**: Electron/Tauri apps, VS Code extensions, and web dashboards built on CLASSIC's analysis engine.
- **Scripting and automation**: Node/Bun scripts for batch crash log analysis, mod list validation, and CI pipelines.
- **Runtime parity**: Feature parity with the Python bindings, ensuring no consumer is limited by binding choice.

The work is organized into **5 implementation waves** spanning an estimated 17 module files within the existing single-crate architecture.

---

## 2. Background & Motivation

### Why Node.js/Bun Bindings?

1. **Ecosystem reach**: Node.js is the most widely used server-side runtime. Bun is the fastest-growing alternative. Together they cover the majority of JavaScript-based tooling.
2. **Electron/Tauri integration**: A native addon is the most performant way to ship CLASSIC's analysis engine inside desktop apps built with web technologies.
3. **VS Code extensions**: The most popular code editor has a rich extension API built on Node.js. Mod authors and game developers could use CLASSIC directly in their workflow.
4. **CI/CD pipelines**: Mod list validation and crash log triage can be automated with `npx`-style tooling.
5. **Bun compatibility**: NAPI-RS v3 natively supports Bun, giving us two runtimes from a single codebase.

### Why NAPI-RS v3?

- **Stable ABI**: Targets Node-API version 9, compatible with Node.js >= 18 and all Bun versions.
- **Auto TypeScript**: The `#[napi]` macro generates `.d.ts` type declarations automatically.
- **Async-first**: Native `async fn` -> `Promise` support, `ThreadsafeFunction` for callbacks.
- **Cross-platform prebuilds**: Built-in CI matrix for Windows, macOS, and Linux binaries.
- **Single cdylib**: All modules compile into one native addon (`classic-node.node`), keeping `npm install` simple.

---

## 3. Current State

### What Exists

| Component | Status | Details |
|-----------|--------|---------|
| `classic-node` crate | Scaffolded | Single cdylib crate, NAPI-RS v3, builds successfully |
| `lib.rs` | Complete | Module registration, `get_version()` export |
| `yaml.rs` | Partial | 7 functions: parse, stringify, load_file, get_value, get_string_value, get_vec_value, get_hashmap_value |
| `scanlog.rs` | Stub | Types only: `JsAnalysisConfig`, `JsAnalysisResult`, `create_analysis_config()`. No actual analysis execution. |
| `package.json` | Complete | `@classic/node`, build scripts, Windows x64 target |
| `Cargo.toml` | Partial | Dependencies for yaml-core and scanlog-core only |

### What Is Missing

- **15 core crates** have zero Node bindings.
- **2 existing modules** (yaml, scanlog) are incomplete.
- No integration tests beyond basic import verification.
- No npm publishing pipeline.
- No cross-platform prebuild CI.

### Python Binding Coverage (Reference)

All 19 business-logic crates have complete Python bindings via PyO3 `-py` crates. This serves as the authoritative reference for API surface and behavior. The Node bindings should achieve equivalent coverage (excluding Python-specific constructs like GIL management and `__repr__`/`__str__` dunder methods).

---

## 4. Scope & Goals

### In Scope

1. Complete Node.js/Bun bindings for all 17 applicable business-logic crates (19 minus 2 exclusions).
2. Full TypeScript type declarations (auto-generated + hand-written supplements).
3. Integration test suite using Vitest.
4. Cross-platform prebuild CI configuration.
5. npm package structure and publishing configuration.

### Goals

| Goal | Metric |
|------|--------|
| API parity with Python bindings | >= 95% of public Python API surface has a Node equivalent |
| Type safety | 100% of exported functions have TypeScript declarations |
| Test coverage | >= 80% of exported functions have at least one integration test |
| Runtime compatibility | Passes on Node.js >= 18 AND Bun >= 1.0 |
| Build time | Incremental rebuild < 30 seconds |

---

## 5. Non-Goals & Exclusions

### Excluded Crates

| Crate | Reason |
|-------|--------|
| `classic-pybridge-core` | Python-specific (AsyncBridge metrics, GIL helpers). Only `is_runtime_available()` and `get_runtime_info()` are useful and will be exposed via the `shared` module as diagnostics. |
| `classic-perf-core` | Small surface area. Will be merged into the `shared` module rather than getting its own module file. |

### Non-Goals

- **Streaming/WebSocket API**: No real-time event streaming beyond `ThreadsafeFunction` callbacks. WebSocket servers are out of scope.
- **Worker thread support**: The native addon runs on the main thread (or libuv thread pool for async). Explicit `worker_threads` support is not targeted.
- **Browser/WASM target**: This PRD covers Node.js/Bun native addons only. A wasm-bindgen target is a separate effort.
- **CLI tool**: No `npx classic-scan` executable. Consumers build their own CLI.
- **GUI framework bindings**: No React/Vue/Svelte component wrappers.
- **Backward compatibility with Node < 18**: NAPI v9 requires Node.js 18+.

---

## 6. Detailed Requirements

Each module below corresponds to a `.rs` file in `ClassicLib-rs/node-bindings/classic-node/src/`. The module name matches the Cargo dependency crate name with `-core` stripped.

### 6.1 `scanlog` Module (COMPLETE - Currently Incomplete)

**Core crate**: `classic-scanlog-core`
**Priority**: Critical
**Async**: Yes (heavy tokio usage)

#### Types to Export

```typescript
// Already exists - extend with missing fields
interface AnalysisConfig {
  game: string;
  vrMode: boolean;
  crashgenName: string;
  xseAcronym: string;
  classicVersion: string;
  fcxMode: boolean;
  simplifyLogs: boolean;
  // --- NEW FIELDS ---
  gamePath: string | null;
  modsFolder: string | null;
  yamlDatabase: Record<string, string>;        // IndexMap<String, String>
  formidDatabase: Record<string, string>;       // IndexMap<String, String>
  pluginDatabase: Record<string, string[]>;     // IndexMap<String, Vec<String>>
  suspectDatabase: Record<string, string[]>;    // IndexMap<String, Vec<String>>
  gpuDatabase: Record<string, string>;
  warningSections: Record<string, string[]>;
  crashgenVersion: string | null;
}

interface AnalysisResult {
  logPath: string;
  reportLines: string[];
  success: boolean;
  error: string | null;
  processingTimeMs: number;
  formidCount: number;
  pluginCount: number;
  suspectCount: number;
}

interface ParsedSegments {
  header: string[];
  stack: string[];
  plugins: string[];
  papyrus: string[];
  bodyEnd: string[];
}
```

#### Functions to Export

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `createAnalysisConfig` | `(game: string, vrMode: boolean) => AnalysisConfig` | No | Already exists, extend fields |
| `processLog` | `(logPath: string, config: AnalysisConfig) => Promise<AnalysisResult>` | Yes | Core analysis pipeline |
| `processLogsBatch` | `(logPaths: string[], config: AnalysisConfig, onProgress?: (done: number, total: number) => void) => Promise<AnalysisResult[]>` | Yes | Batch with `ThreadsafeFunction` progress callback |
| `parseSegments` | `(content: string) => ParsedSegments` | No | Log structure parsing |
| `extractFormids` | `(lines: string[]) => string[]` | No | FormID extraction |
| `extractPlugins` | `(lines: string[]) => string[]` | No | Plugin list extraction |
| `parseComplete` | `(content: string) => ParsedSegments` | No | Full parse pass |
| `detectVrLog` | `(content: string) => boolean` | No | VR log detection |
| `detectMods` | `(plugins: string[], database: Record<string, string[]>) => Record<string, string[]>` | No | Mod detection from plugin list |

### 6.2 `yaml` Module (COMPLETE - Currently Partial)

**Core crate**: `classic-yaml-core`
**Priority**: High
**Async**: No (except batch file loading)

#### New Class: `YamlDocument`

The current stateless function API re-parses YAML on every call. Add a class-based API for efficiency:

```typescript
class YamlDocument {
  constructor(content: string);
  static fromFile(path: string): YamlDocument;
  getValue(keyPath: string): unknown;
  getStringValue(keyPath: string, defaultValue: string): string;
  getVecValue(keyPath: string): string[];
  getHashmapValue(keyPath: string): Record<string, string>;
  getIndexmapValue(keyPath: string): Record<string, string>;
  getHashmapVecValue(keyPath: string): Record<string, string[]>;
  getIndexmapVecValue(keyPath: string): Record<string, string[]>;
  setValue(keyPath: string, value: unknown): void;
  toYamlString(): string;
  save(path: string): void;
}
```

#### Additional Functions

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `yamlParse` | `(content: string) => unknown` | No | Already exists |
| `yamlStringify` | `(data: unknown) => string` | No | Already exists |
| `yamlLoadFile` | `(path: string) => unknown` | No | Already exists |
| `yamlGetValue` | `(content: string, keyPath: string) => unknown` | No | Already exists |
| `yamlGetStringValue` | `(content: string, keyPath: string, default: string) => string` | No | Already exists |
| `yamlGetVecValue` | `(content: string, keyPath: string) => string[]` | No | Already exists |
| `yamlGetHashmapValue` | `(content: string, keyPath: string) => Record<string, string>` | No | Already exists |
| `yamlSaveFile` | `(path: string, data: unknown) => void` | No | **NEW** |
| `yamlSetSetting` | `(content: string, keyPath: string, value: unknown) => string` | No | **NEW** - returns modified YAML string |
| `yamlClearCache` | `() => void` | No | **NEW** |
| `yamlGetCacheStats` | `() => { hits: number; misses: number; size: number }` | No | **NEW** |
| `yamlGetSettingsBatch` | `(content: string, keyPaths: string[]) => Record<string, unknown>` | No | **NEW** |
| `yamlSetSettingsBatch` | `(content: string, settings: Record<string, unknown>) => string` | No | **NEW** |
| `yamlLoadFilesBatch` | `(paths: string[]) => Promise<Record<string, unknown>>` | Yes | **NEW** - async parallel load |

### 6.3 `fileio` Module (NEW)

**Core crate**: `classic-file-io-core`
**Priority**: High
**Async**: Yes (most operations)

#### Classes

```typescript
class FileIOCore {
  constructor();
  readFile(path: string): Promise<string>;
  writeFile(path: string, content: string): Promise<void>;
  readLines(path: string): Promise<string[]>;
  writeLines(path: string, lines: string[]): Promise<void>;
  readBytes(path: string): Promise<Buffer>;
  writeBytes(path: string, data: Buffer): Promise<void>;
  appendFile(path: string, content: string): Promise<void>;
  readFileMmap(path: string): Promise<string>;
  readMultipleFiles(paths: string[]): Promise<Record<string, string>>;
  writeMultipleFiles(files: Record<string, string>): Promise<void>;
  fileExists(path: string): Promise<boolean>;
  getFileSize(path: string): Promise<number>;
  clearCache(): void;
}

class FileHasher {
  static hashFile(path: string): Promise<string>;
  static hashFilesParallel(paths: string[]): Promise<Record<string, string>>;
}

class DDSHeader {
  static parse(data: Buffer): DDSHeaderInfo;
}

interface DDSHeaderInfo {
  width: number;
  height: number;
  mipmapCount: number;
  format: string;
}

class LogCollector {
  static collectAll(directory: string): Promise<string[]>;
}

class BackupManager {
  static createBackup(sourcePath: string, backupDir: string): Promise<string>;
  static listVersions(backupDir: string): Promise<string[]>;
}
```

#### Functions

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `walkDirectory` | `(path: string, pattern?: string) => string[]` | No | Sync walkdir |
| `generateIgnoreFile` | `(path: string, entries: string[]) => Promise<void>` | Yes | Generate .classic-ignore |
| `generateLocalYaml` | `(path: string, config: unknown) => Promise<void>` | Yes | Generate local YAML |

### 6.4 `database` Module (NEW)

**Core crate**: `classic-database-core`
**Priority**: High
**Async**: Yes (all query methods)

#### Classes

```typescript
class DatabasePool {
  static initialize(dbPaths: string[]): Promise<DatabasePool>;
  getEntry(formId: string, plugin: string, table: string): Promise<unknown | null>;
  getEntriesBatch(queries: Array<{ formId: string; plugin: string; table: string }>): Promise<unknown[]>;
  setGameTable(table: string): void;
  clearCache(): void;
  getStats(): PoolStatistics;
  optimize(): Promise<void>;
  close(): Promise<void>;
}

interface PoolStatistics {
  totalQueries: number;
  cacheHits: number;
  cacheMisses: number;
  hitRate: number;
}
```

### 6.5 `constants` Module (NEW)

**Core crate**: `classic-constants-core`
**Priority**: High
**Async**: No

#### Enums (as TypeScript string unions)

```typescript
type Fallout4Version =
  | "Original"
  | "NextGen"
  | "AnniversaryEdition"
  | "VR";

type YamlFile =
  | "Main"
  | "Settings"
  | "Ignore"
  | "Game"
  | "GameLocal"
  | "Test"
  | "Cache";

type GameId =
  | "Fallout4"
  | "Fallout4VR"
  | "Skyrim"
  | "Starfield";
```

#### Functions

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `getGameName` | `(id: GameId) => string` | No | Human-readable name |
| `getYamlFilePath` | `(file: YamlFile, gameId: GameId) => string` | No | Resolve YAML file path |
| `getFallout4VersionInfo` | `(version: Fallout4Version) => { name: string; steamId: number; isVr: boolean }` | No | Version metadata |
| `getAllGameIds` | `() => GameId[]` | No | List all supported games |
| `getAllYamlFiles` | `() => YamlFile[]` | No | List all YAML file types |

### 6.6 `version` Module (NEW)

**Core crate**: `classic-version-core`
**Priority**: High
**Async**: No

#### Functions

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `parseVersion` | `(input: string) => string` | No | Normalize version string |
| `tryParseVersion` | `(input: string) => string \| null` | No | Non-throwing variant |
| `compareVersions` | `(a: string, b: string) => -1 \| 0 \| 1` | No | Semver-style comparison |
| `isKnownFallout4Version` | `(version: string) => boolean` | No | Check against known list |
| `extractVersionFromFilename` | `(filename: string) => string \| null` | No | Parse version from file name |
| `extractVersionFromLog` | `(content: string) => string \| null` | No | Parse version from log content |
| `extractAllVersions` | `(content: string) => string[]` | No | Find all version strings |
| `formatVersion` | `(version: string) => string` | No | Pretty-print version |

### 6.7 `update` Module (NEW)

**Core crate**: `classic-update-core`
**Priority**: High
**Async**: Yes (HTTP operations)

#### Classes

```typescript
class GithubClient {
  constructor(owner: string, repo: string);
  static withToken(owner: string, repo: string, token: string): GithubClient;
  getLatestRelease(): Promise<GithubRelease>;
  getAllReleases(): Promise<GithubRelease[]>;
  hasUpdate(currentVersion: string): boolean;
}

interface GithubRelease {
  tagName: string;
  name: string;
  body: string;
  publishedAt: string;
  assets: GithubAsset[];
  prerelease: boolean;
  draft: boolean;
}

interface GithubAsset {
  name: string;
  downloadUrl: string;
  size: number;
  contentType: string;
}
```

### 6.8 `versionRegistry` Module (NEW)

**Core crate**: `classic-version-registry-core`
**Priority**: High
**Async**: No

Note: This crate has no Python bindings yet -- Node will be the first non-Rust consumer.

#### Types

```typescript
interface GameVersion {
  major: number;
  minor: number;
  patch: number;
  build: number;
}

interface VersionInfo {
  id: string;
  version: GameVersion;
  shortName: string;
  gameId: string;
  description: string;
}

type MatchConfidence =
  | "Exact"
  | "Range"
  | "Nearest"
  | "Default"
  | "Unknown";

interface MatchResult {
  versionInfo: VersionInfo | null;
  confidence: MatchConfidence;
}
```

#### Functions

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `getVersionById` | `(id: string) => VersionInfo \| null` | No | Lookup by ID |
| `getVersionByVersion` | `(version: GameVersion) => VersionInfo \| null` | No | Lookup by version tuple |
| `getVersionByShortName` | `(name: string) => VersionInfo \| null` | No | Lookup by short name |
| `getAllVersions` | `() => VersionInfo[]` | No | Full registry dump |
| `getVersionsForGame` | `(gameId: string) => VersionInfo[]` | No | Filter by game |
| `getCorrectVersions` | `(gameId: string) => VersionInfo[]` | No | Known-good versions |
| `getWrongVersions` | `(gameId: string) => VersionInfo[]` | No | Known-bad versions |
| `matchVersion` | `(version: GameVersion, gameId: string) => MatchResult` | No | Fuzzy version matching |

### 6.9 `config` Module (NEW)

**Core crate**: `classic-config-core`
**Priority**: Medium
**Async**: Yes (file loading)

#### Classes

```typescript
class YamlDataCore {
  static loadFromYamlFiles(paths: string[]): Promise<YamlDataCore>;
  static fromYamlContent(content: string): YamlDataCore;

  // ~30 fields exposed as getters returning JS-native types
  get gameName(): string;
  get gamePathSuffix(): string;
  get warningSections(): Record<string, string[]>;
  get modDatabase(): Record<string, string>;
  get formidDatabase(): Record<string, string>;
  get pluginDatabase(): Record<string, string[]>;
  get suspectDatabase(): Record<string, string[]>;
  // ... (all fields from core struct)

  toObject(): Record<string, unknown>;  // Full dump as plain JS object
}
```

### 6.10 `scangame` Module (NEW)

**Core crate**: `classic-scangame-core`
**Priority**: Medium
**Async**: Mixed

#### Classes and Functions

| Function/Class | Signature | Async | Notes |
|---------------|-----------|-------|-------|
| `BA2Scanner.scan` | `(modsPath: string) => Promise<string[]>` | Yes | BA2 archive scanning |
| `ConfigDuplicateDetector.detect` | `(configDir: string) => string[]` | No | Find duplicate configs |
| `EnbChecker.check` | `(gamePath: string) => { installed: boolean; version: string \| null }` | No | ENB detection |
| `IniValidator.validate` | `(iniPath: string) => Array<{ key: string; expected: string; actual: string; severity: string }>` | No | INI validation |
| `GameIntegrityChecker.check` | `(gamePath: string, hashes: Record<string, string>) => Promise<Array<{ file: string; status: string }>>` | Yes | SHA256 integrity |
| `CrashgenChecker.check` | `(gamePath: string, xseType: string) => { installed: boolean; version: string \| null }` | No | Crash generator detection |
| `UnpackedScanner.scan` | `(dataPath: string) => string[]` | No | Loose file detection |
| `XseChecker.check` | `(gamePath: string, xseType: string) => { installed: boolean; version: string \| null; expectedVersion: string \| null }` | No | Script extender check |

### 6.11 `path` Module (NEW)

**Core crate**: `classic-path-core`
**Priority**: Medium
**Async**: No

#### Classes and Functions

| Function/Class | Signature | Async | Notes |
|---------------|-----------|-------|-------|
| `GamePathFinder.find` | `(gameId: string) => string \| null` | No | Auto-detect game install |
| `DocsPathFinder.find` | `(gameId: string) => string \| null` | No | Auto-detect documents folder |
| `DocumentsChecker.check` | `(docsPath: string) => Array<IniCheckResult>` | No | Documents folder validation |
| `validatePath` | `(path: string) => boolean` | No | Path existence check |
| `validateGamePath` | `(path: string, gameId: string) => boolean` | No | Valid game installation |
| `validateModsPath` | `(path: string) => boolean` | No | Valid mods folder |
| `findFileInDirectory` | `(dir: string, filename: string) => string \| null` | No | File search |
| `getRelativePath` | `(from: string, to: string) => string` | No | Relative path computation |
| `normalizePath` | `(path: string) => string` | No | Path normalization |

```typescript
interface IniCheckResult {
  file: string;
  exists: boolean;
  issues: string[];
}
```

### 6.12 `shared` Module (NEW)

**Core crate**: `classic-shared-core` + `classic-perf-core` + `classic-registry-core`
**Priority**: Medium
**Async**: No

This module aggregates foundation utilities that don't warrant their own module files.

#### Path Utilities (from classic-shared-core)

| Function | Signature | Notes |
|----------|-----------|-------|
| `normalizePath` | `(path: string) => string` | Cross-platform normalization |
| `joinPaths` | `(...parts: string[]) => string` | Safe path joining |
| `validatePathsBatch` | `(paths: string[]) => Record<string, boolean>` | Batch validation |

#### String Utilities (from classic-shared-core)

| Function | Signature | Notes |
|----------|-----------|-------|
| `internString` | `(value: string) => string` | String interning for dedup |
| `processStringBatch` | `(values: string[]) => string[]` | Batch normalization |
| `normalizeString` | `(value: string) => string` | Whitespace/case normalization |

#### Performance Metrics (from classic-perf-core)

| Function | Signature | Notes |
|----------|-----------|-------|
| `recordTiming` | `(label: string, durationMs: number) => void` | Record a timing measurement |
| `getMetricsSummary` | `() => MetricsSummary` | Aggregate statistics |
| `clearMetrics` | `() => void` | Reset all metrics |

```typescript
interface MetricsSummary {
  timings: Record<string, { count: number; totalMs: number; avgMs: number; minMs: number; maxMs: number }>;
}
```

#### Registry (from classic-registry-core)

| Function | Signature | Notes |
|----------|-----------|-------|
| `registryGet` | `(key: string) => unknown \| null` | Get value from global registry |
| `registrySet` | `(key: string, value: unknown) => void` | Set value in global registry |
| `registryRemove` | `(key: string) => boolean` | Remove key |
| `registryClear` | `() => void` | Clear all entries |

Note: Registry values are stored as `serde_json::Value` internally, enabling arbitrary JSON-compatible types.

#### Diagnostics (from classic-pybridge-core subset)

| Function | Signature | Notes |
|----------|-----------|-------|
| `isRuntimeAvailable` | `() => boolean` | Check if Tokio runtime is live |
| `getRuntimeInfo` | `() => { available: boolean; threadCount: number }` | Runtime diagnostics |

### 6.13 `resource` Module (NEW)

**Core crate**: `classic-resource-core`
**Priority**: Medium
**Async**: No (filesystem I/O via walkdir, sync)

#### Types and Functions

```typescript
type ResourceType =
  | "Texture"
  | "Mesh"
  | "Script"
  | "Sound"
  | "Animation"
  | "Interface"
  | "Sequence"
  | "Material"
  | "Other";
```

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `detectResourceType` | `(path: string) => ResourceType` | No | Classify by extension/header |
| `enumerateResources` | `(directory: string) => string[]` | No | Recursive file enumeration |
| `countResourcesByType` | `(directory: string) => Record<ResourceType, number>` | No | Type-counted summary |

### 6.14 `web` Module (NEW)

**Core crate**: `classic-web-core`
**Priority**: Medium
**Async**: No

#### Types and Functions

```typescript
type ModSite =
  | "NexusMods"
  | "BethesdaNet"
  | "ModDB";
```

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `validateModUrl` | `(url: string) => boolean` | No | Check if URL is a known mod site |
| `detectModSite` | `(url: string) => ModSite \| null` | No | Identify which mod site |
| `buildModUrl` | `(site: ModSite, modId: string) => string` | No | Construct canonical URL |

### 6.15 `xse` Module (NEW)

**Core crate**: `classic-xse-core`
**Priority**: Medium
**Async**: No

#### Types and Functions

```typescript
type XseType =
  | "F4SE"
  | "F4SEVR"
  | "SKSE"
  | "SKSE64"
  | "SKSEVR";

interface XseInfo {
  xseType: XseType;
  version: string | null;
  path: string | null;
  installed: boolean;
}
```

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `detectXseVersion` | `(gamePath: string, xseType: XseType) => string \| null` | No | Read version from DLL |
| `isXseInstalled` | `(gamePath: string, xseType: XseType) => boolean` | No | Presence check |
| `getXseInfo` | `(gamePath: string, xseType: XseType) => XseInfo` | No | Full info struct |

### 6.16 `message` Module (NEW)

**Core crate**: `classic-message-core`
**Priority**: Medium
**Async**: No

#### Types and Functions

```typescript
type MessageType =
  | "Info"
  | "Warning"
  | "Error"
  | "Success"
  | "Progress"
  | "Debug"
  | "Critical";

type MessageTarget =
  | "All"
  | "GuiOnly"
  | "CliOnly"
  | "LogOnly";

interface Message {
  messageType: MessageType;
  target: MessageTarget;
  content: string;
  timestamp: number;
}
```

| Function | Signature | Async | Notes |
|----------|-----------|-------|-------|
| `createMessage` | `(type: MessageType, content: string, target?: MessageTarget) => Message` | No | Builder pattern |
| `formatMessage` | `(message: Message) => string` | No | Human-readable format |
| `createLogger` | `(name: string) => Logger` | No | Named logger instance |

```typescript
class Logger {
  info(content: string): void;
  warning(content: string): void;
  error(content: string): void;
  debug(content: string): void;
}
```

### 6.17 `settings` Module (NEW)

**Core crate**: `classic-settings-core`
**Priority**: Medium
**Async**: Yes (file loading)

#### Classes

```typescript
class SettingsCache {
  constructor(ttlSeconds?: number);
  loadSettings(path: string): Promise<Record<string, unknown>>;
  loadSettingsBatch(paths: string[]): Promise<Record<string, unknown>>;
  loadSettingsSync(path: string): Record<string, unknown>;
  loadSettingsBatchSync(paths: string[]): Record<string, unknown>;
  getCached(key: string): unknown | null;
  invalidate(key: string): boolean;
  clearCache(): void;
  getCacheStats(): { hits: number; misses: number; size: number; ttlSeconds: number };
}
```

---

## 7. Architecture & Design Decisions

### 7.1 Single Crate Architecture

**Decision**: Keep all Node bindings in the single `classic-node` crate with one module file per domain.

**Rationale**:
- NAPI-RS compiles to a single `.node` binary. Multiple crates would need to be linked into one anyway.
- Simpler npm packaging: one package, one native addon.
- Module files provide sufficient code organization.
- Matches the existing pattern (`yaml.rs`, `scanlog.rs`).

**Structure**:
```
classic-node/src/
  lib.rs          # Module registration, get_version()
  yaml.rs         # classic-yaml-core bindings
  scanlog.rs      # classic-scanlog-core bindings
  fileio.rs       # classic-file-io-core bindings
  database.rs     # classic-database-core bindings
  constants.rs    # classic-constants-core bindings
  version.rs      # classic-version-core bindings
  update.rs       # classic-update-core bindings
  version_registry.rs  # classic-version-registry-core bindings
  config.rs       # classic-config-core bindings
  scangame.rs     # classic-scangame-core bindings
  path.rs         # classic-path-core bindings
  shared.rs       # classic-shared-core + perf + registry bindings
  resource.rs     # classic-resource-core bindings
  web.rs          # classic-web-core bindings
  xse.rs          # classic-xse-core bindings
  message.rs      # classic-message-core bindings
  settings.rs     # classic-settings-core bindings
```

### 7.2 Class vs Function API

**Decision**: Use classes for stateful objects, free functions for stateless operations.

| Pattern | When to Use | Example |
|---------|-------------|---------|
| `#[napi]` free function | Stateless transformation | `yamlParse(content)` |
| `#[napi] struct` + methods | Object with internal state | `YamlDocument`, `DatabasePool`, `SettingsCache` |
| `#[napi(object)]` struct | Plain data transfer objects | `AnalysisResult`, `GithubRelease` |

**Rationale**: Mirrors the Python binding pattern (PyLogParser, PyFileIOCore) while being idiomatic for JavaScript consumers. Classes enable internal caching and connection pooling.

### 7.3 Async Pattern

**Decision**: Use `#[napi] async fn` for all I/O-bound operations. Use `ThreadsafeFunction` for progress callbacks.

```rust
// Simple async -> Promise
#[napi]
pub async fn process_log(log_path: String, config: JsAnalysisConfig) -> Result<JsAnalysisResult> {
    let rt = classic_shared_core::get_runtime();
    let result = rt.spawn(async move { /* ... */ }).await??;
    Ok(result)
}

// Progress callback via ThreadsafeFunction
#[napi]
pub async fn process_logs_batch(
    log_paths: Vec<String>,
    config: JsAnalysisConfig,
    on_progress: Option<ThreadsafeFunction<(u32, u32), ErrorStrategy::Fatal>>,
) -> Result<Vec<JsAnalysisResult>> {
    // ...
}
```

**Runtime rule**: All async operations use the shared Tokio runtime via `classic_shared_core::get_runtime()`. Never create a new runtime.

### 7.4 Type Mapping Convention

| Rust Type | TypeScript Type | NAPI Strategy |
|-----------|----------------|---------------|
| `String` | `string` | Direct |
| `bool` | `boolean` | Direct |
| `i32`, `u32` | `number` | Direct |
| `i64`, `u64` | `bigint` or `number` | Use `number` for values < 2^53, `bigint` otherwise |
| `f64` | `number` | Direct |
| `Vec<T>` | `T[]` | Direct via `#[napi]` |
| `Vec<u8>` | `Buffer` | Use `napi::bindgen_prelude::Buffer` |
| `Option<T>` | `T \| null` | Direct |
| `HashMap<String, T>` | `Record<string, T>` | Via serde_json or manual conversion |
| `IndexMap<String, T>` | `Record<string, T>` | Via serde_json (V8 preserves insertion order) |
| `PathBuf` | `string` | Convert via `.to_string_lossy()` |
| Rust `enum` (unit) | TypeScript string literal union | Serialize as string |
| Rust `enum` (data) | TypeScript discriminated union | Serialize as `{ type: string; data: ... }` |
| `Result<T, E>` | Throws `Error` or returns `T` | `napi::Error` with message |

### 7.5 Error Handling

**Decision**: All Rust errors convert to `napi::Error` with descriptive messages. Error codes are included for programmatic handling.

```rust
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}
```

For structured error handling, define an error code convention:

| Code Prefix | Domain |
|-------------|--------|
| `YAML_` | YAML parsing/serialization errors |
| `SCAN_` | Scanlog analysis errors |
| `IO_` | File I/O errors |
| `DB_` | Database errors |
| `NET_` | Network/HTTP errors |
| `PATH_` | Path validation errors |
| `CONFIG_` | Configuration errors |

Consumers can catch and match:
```typescript
try {
  await processLog(path, config);
} catch (e) {
  if (e.code === 'SCAN_PARSE_FAILED') { /* ... */ }
}
```

### 7.6 Naming Convention

| Rust | TypeScript | Example |
|------|-----------|---------|
| `snake_case` function | `camelCase` function | `parse_yaml` -> `yamlParse` |
| `PascalCase` struct | `PascalCase` class/interface | `AnalysisConfig` -> `AnalysisConfig` |
| `SCREAMING_SNAKE` const | `SCREAMING_SNAKE` const | `MAX_RETRIES` -> `MAX_RETRIES` |
| `snake_case` field | `camelCase` property | `vr_mode` -> `vrMode` |

NAPI-RS handles the `snake_case` -> `camelCase` conversion automatically via `#[napi(js_name = "camelCase")]` or the default rename behavior.

---

## 8. Implementation Phases

Work is organized into 5 waves. Each wave can be executed independently after its dependencies are met.

### Wave 1: Core Infrastructure (Blockers for Everything Else)

**Dependency**: None
**Modules**: `shared`, `constants`, `version`, `message`

| Module | Effort | Notes |
|--------|--------|-------|
| `shared.rs` | Medium | Foundation utils, perf metrics, registry. Must be first since other modules depend on `get_runtime()` being exposed. |
| `constants.rs` | Small | Pure enum/constant exports. No dependencies. |
| `version.rs` | Small | Pure sync functions. No dependencies. |
| `message.rs` | Small | Message types and Logger. No dependencies. |

**Cargo.toml additions**:
```toml
classic-perf-core = { path = "../../business-logic/classic-perf-core" }
classic-registry-core = { path = "../../business-logic/classic-registry-core" }
classic-constants-core = { path = "../../business-logic/classic-constants-core" }
classic-version-core = { path = "../../business-logic/classic-version-core" }
classic-message-core = { path = "../../business-logic/classic-message-core" }
classic-pybridge-core = { path = "../../business-logic/classic-pybridge-core" }  # pybridge is python-specific infrastructure that doesn't apply to node
```

**Exit criteria**: All 4 modules compile, TypeScript types generate, basic integration tests pass.

### Wave 2: Complete Existing Modules

**Dependency**: Wave 1 (shared module provides runtime utilities)
**Modules**: `yaml` (complete), `scanlog` (complete)

| Module | Effort | Notes |
|--------|--------|-------|
| `yaml.rs` | Medium | Add `YamlDocument` class, save/batch functions, cache management. |
| `scanlog.rs` | Large | Add `processLog`, `processLogsBatch` (with `ThreadsafeFunction` progress), `parseSegments`, all extraction functions. Requires thorough async testing. |

**Exit criteria**: `processLog` returns correct `AnalysisResult` for a known crash log. `YamlDocument` class round-trips parse/save.

### Wave 3: File I/O & Data

**Dependency**: Wave 1
**Modules**: `fileio`, `database`, `settings`, `config`

| Module | Effort | Notes |
|--------|--------|-------|
| `fileio.rs` | Large | Many async methods, Buffer handling, mmap, walk_directory. |
| `database.rs` | Medium | Async pool lifecycle, query methods. |
| `settings.rs` | Medium | Cache with TTL, sync + async load variants. |
| `config.rs` | Medium | ~30 fields, async file loading. |

**Cargo.toml additions**:
```toml
classic-file-io-core = { path = "../../business-logic/classic-file-io-core" }
classic-database-core = { path = "../../business-logic/classic-database-core" }
classic-settings-core = { path = "../../business-logic/classic-settings-core" }
classic-config-core = { path = "../../business-logic/classic-config-core" }
```

**Exit criteria**: File read/write round-trips. Database pool opens, queries, and closes. Settings cache TTL works.

### Wave 4: Game Analysis

**Dependency**: Waves 1-2 (scanlog patterns inform scangame design)
**Modules**: `scangame`, `path`, `xse`, `versionRegistry`

| Module | Effort | Notes |
|--------|--------|-------|
| `scangame.rs` | Large | Many checker classes, mixed sync/async. |
| `path.rs` | Medium | Windows registry access for game detection. |
| `xse.rs` | Small | Simple detection functions. |
| `version_registry.rs` | Medium | OnceLock singleton, first non-Rust consumer. |

**Cargo.toml additions**:
```toml
classic-scangame-core = { path = "../../business-logic/classic-scangame-core" }
classic-path-core = { path = "../../business-logic/classic-path-core" }
classic-xse-core = { path = "../../business-logic/classic-xse-core" }
classic-version-registry-core = { path = "../../business-logic/classic-version-registry-core" }
```

**Exit criteria**: Game path detection works on Windows. XSE detection identifies installed script extenders. Version registry returns correct match results.

### Wave 5: Utilities & Polish

**Dependency**: Wave 1
**Modules**: `resource`, `web`, `update`

| Module | Effort | Notes |
|--------|--------|-------|
| `resource.rs` | Small | Simple enum + walkdir functions. |
| `web.rs` | Small | URL validation/construction. |
| `update.rs` | Medium | Async HTTP via reqwest. GitHub API. |

**Cargo.toml additions**:
```toml
classic-resource-core = { path = "../../business-logic/classic-resource-core" }
classic-web-core = { path = "../../business-logic/classic-web-core" }
classic-update-core = { path = "../../business-logic/classic-update-core" }
```

**Exit criteria**: GitHub release check returns valid data. Resource enumeration lists correct file types. URL validation works for all mod sites.

### Wave Dependency Graph

```
Wave 1 (Infrastructure)
  |
  +-- Wave 2 (Complete Existing)
  |     |
  |     +-- Wave 4 (Game Analysis)
  |
  +-- Wave 3 (File I/O & Data)
  |
  +-- Wave 5 (Utilities & Polish)
```

---

## 9. TypeScript Types Strategy

### Auto-Generated Types

NAPI-RS v3 automatically generates `.d.ts` files for all `#[napi]` exports. This covers:

- Function signatures (parameters and return types)
- `#[napi(object)]` struct interfaces
- `#[napi]` struct classes with methods
- Enum variants (when using `#[napi(string_enum)]`)

The generated file is output to `index.d.ts` in the package root during build.

### Hand-Written Supplements

Create a `types/` directory for complex types that benefit from richer documentation or utility types:

```
classic-node/
  types/
    index.d.ts          # Re-exports all, augments auto-generated types
    scanlog.d.ts         # Complex analysis types with JSDoc
    config.d.ts          # YamlDataCore field documentation
```

### Strategy

1. **Primary**: Rely on NAPI-RS auto-generation for all function/class signatures.
2. **Supplement**: Add JSDoc comments directly in Rust via `///` doc comments (NAPI-RS propagates these to `.d.ts`).
3. **Override**: For complex generic types or utility types not expressible via `#[napi]`, hand-write `.d.ts` supplements.
4. **Validate**: Run `tsc --noEmit` against the generated types in CI to catch type errors.

---

## 10. Testing Strategy

### Framework

**Vitest** for test execution, chosen for:
- Fast startup (important for native addon tests)
- ESM-first (matches modern Node.js)
- Built-in TypeScript support
- Compatible with both Node.js and Bun

### Test Organization

```
classic-node/
  __tests__/
    yaml.test.ts
    scanlog.test.ts
    fileio.test.ts
    database.test.ts
    constants.test.ts
    version.test.ts
    update.test.ts
    version-registry.test.ts
    config.test.ts
    scangame.test.ts
    path.test.ts
    shared.test.ts
    resource.test.ts
    web.test.ts
    xse.test.ts
    message.test.ts
    settings.test.ts
  __tests__/fixtures/
    sample-crash.log
    sample.yaml
    sample.db
```

### Test Categories

| Category | Scope | Runner |
|----------|-------|--------|
| Smoke | Import and call each export | CI (every push) |
| Unit | Individual function behavior | CI (every push) |
| Integration | Cross-module workflows (e.g., load config -> scan log) | CI (every push) |
| Platform | Windows-specific features (registry, game paths) | CI (Windows only) |
| Performance | Benchmark critical paths (parse, scan) | Manual / nightly |

### Test Requirements

1. Every exported function MUST have at least one test.
2. Async functions MUST be tested with both success and error cases.
3. `ThreadsafeFunction` callbacks MUST be tested for correct invocation count.
4. Buffer operations MUST round-trip correctly.
5. Error cases MUST verify the error message contains useful context.

### Coverage Target

- >= 80% of exported functions covered.
- 100% of async functions covered (most likely to have subtle bugs).
- 100% of type conversion edge cases covered (null, empty array, large numbers).

---

## 11. Build, Packaging & Distribution

### Build Pipeline

```bash
# Development (debug, fast iteration)
cd ClassicLib-rs/node-bindings/classic-node
npm run build:debug

# Release (optimized, stripped)
npm run build

# Test
npm test
```

### package.json Updates

```jsonc
{
  "name": "@classic/node",
  "version": "0.2.0",  // Bump for this work
  "private": true,       // Remove when ready for npm publish
  "main": "index.js",
  "types": "index.d.ts",
  "napi": {
    "binaryName": "classic-node",
    "targets": [
      "x86_64-pc-windows-msvc",
      "x86_64-unknown-linux-gnu",
      "x86_64-apple-darwin",
      "aarch64-apple-darwin"
    ]
  },
  "scripts": {
    "build": "napi build --release --platform --manifest-path ./Cargo.toml",
    "build:debug": "napi build --platform --manifest-path ./Cargo.toml",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit",
    "prepublishOnly": "napi prepublish -t npm"
  },
  "devDependencies": {
    "@napi-rs/cli": "^3.0.0",
    "bun-types": "latest",
    "vitest": "^3.0.0",
    "typescript": "^5.7.0"
  },
  "engines": {
    "node": ">= 18"
  }
}
```

### Cross-Platform Prebuilds

NAPI-RS v3 provides a GitHub Actions template for building prebuilt binaries. The CI matrix should cover:

| Target | OS | Arch | Notes |
|--------|----|------|-------|
| `x86_64-pc-windows-msvc` | Windows | x64 | Primary target |
| `x86_64-unknown-linux-gnu` | Linux | x64 | Server/CI usage |
| `x86_64-apple-darwin` | macOS | x64 | Intel Macs |
| `aarch64-apple-darwin` | macOS | ARM64 | Apple Silicon |

ARM Linux (`aarch64-unknown-linux-gnu`) can be added later if demand exists.

### npm Package Structure

When published (future), the package uses NAPI-RS's optional dependencies pattern:

```
@classic/node                     # Main package (JS loader + types)
@classic/node-win32-x64-msvc      # Windows x64 prebuilt
@classic/node-linux-x64-gnu       # Linux x64 prebuilt
@classic/node-darwin-x64           # macOS x64 prebuilt
@classic/node-darwin-arm64         # macOS ARM64 prebuilt
```

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API coverage | >= 95% of Python binding surface | Count exported functions vs Python equivalents |
| TypeScript completeness | 100% | `tsc --noEmit` passes with no errors |
| Test coverage | >= 80% of exports | Vitest coverage report |
| Build time (incremental) | < 30 seconds | CI timing |
| Build time (clean) | < 5 minutes | CI timing |
| Binary size | < 20 MB per platform | File size check |
| Node.js compat | Passes on Node 18, 20, 22 | CI matrix |
| Bun compat | Passes on Bun >= 1.0 | CI matrix |
| No runtime panics | Zero panics in test suite | Test results |
| Memory safety | Zero segfaults | Test + ASan (Linux) |

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Tokio runtime conflicts** | Medium | High | Strictly use `classic_shared_core::get_runtime()`. Never create new runtimes. Test with concurrent async calls. |
| **NAPI-RS v3 breaking changes** | Low | Medium | Pin to exact version in Cargo.toml. Monitor NAPI-RS changelog. |
| **Binary size bloat** | Medium | Low | Use `strip = true`, `lto = "thin"`, `codegen-units = 1` (already configured). Monitor per-wave. |
| **ThreadsafeFunction misuse** | Medium | High | Wrap in helper that handles error reporting. Test callback invocation count. Document correct usage patterns. |
| **IndexMap ordering assumption** | Low | Medium | V8 preserves insertion order for string keys. Add tests verifying order. |
| **Windows registry access fails on non-Windows** | Certain | Medium | Gate `path` module's registry functions behind `#[cfg(target_os = "windows")]`. Return `null` on other platforms. |
| **sqlx compile-time checks** | Low | Medium | Use runtime query checking, not compile-time. Ensure test databases are available. |
| **Large number overflow** | Low | Low | Use `number` for all counts/sizes < 2^53. Document `bigint` usage for file sizes > 4GB if needed. |
| **Stale auto-generated types** | Medium | Low | Generate types during build, not checked in. CI verifies types match. |

---

## 14. Appendix: Full API Surface Reference

### A. Module Summary

| Module | Core Crate | Functions | Classes | Enums | Async | Priority |
|--------|-----------|-----------|---------|-------|-------|----------|
| `scanlog` | classic-scanlog-core | 8 | 0 | 0 | Yes | Critical |
| `yaml` | classic-yaml-core | 14 | 1 | 0 | Partial | High |
| `fileio` | classic-file-io-core | 3 | 5 | 0 | Yes | High |
| `database` | classic-database-core | 0 | 1 | 0 | Yes | High |
| `constants` | classic-constants-core | 5 | 0 | 3 | No | High |
| `version` | classic-version-core | 8 | 0 | 0 | No | High |
| `update` | classic-update-core | 0 | 1 | 0 | Yes | High |
| `versionRegistry` | classic-version-registry-core | 8 | 0 | 1 | No | High |
| `config` | classic-config-core | 0 | 1 | 0 | Yes | Medium |
| `scangame` | classic-scangame-core | 0 | 8 | 0 | Mixed | Medium |
| `path` | classic-path-core | 6 | 3 | 0 | No | Medium |
| `shared` | shared + perf + registry | 12 | 0 | 0 | No | Medium |
| `resource` | classic-resource-core | 3 | 0 | 1 | No | Medium |
| `web` | classic-web-core | 3 | 0 | 1 | No | Medium |
| `xse` | classic-xse-core | 3 | 0 | 1 | No | Medium |
| `message` | classic-message-core | 3 | 1 | 2 | No | Medium |
| `settings` | classic-settings-core | 0 | 1 | 0 | Yes | Medium |
| **TOTAL** | **17 crates** | **76** | **22** | **9** | | |

### B. Complete Function Index

#### Scanlog Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `createAnalysisConfig` | fn | No | `(game: string, vrMode: boolean) => AnalysisConfig` |
| `processLog` | fn | Yes | `(logPath: string, config: AnalysisConfig) => Promise<AnalysisResult>` |
| `processLogsBatch` | fn | Yes | `(logPaths: string[], config: AnalysisConfig, onProgress?: (done: number, total: number) => void) => Promise<AnalysisResult[]>` |
| `parseSegments` | fn | No | `(content: string) => ParsedSegments` |
| `extractFormids` | fn | No | `(lines: string[]) => string[]` |
| `extractPlugins` | fn | No | `(lines: string[]) => string[]` |
| `parseComplete` | fn | No | `(content: string) => ParsedSegments` |
| `detectVrLog` | fn | No | `(content: string) => boolean` |
| `detectMods` | fn | No | `(plugins: string[], database: Record<string, string[]>) => Record<string, string[]>` |

#### YAML Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `yamlParse` | fn | No | `(content: string) => unknown` |
| `yamlStringify` | fn | No | `(data: unknown) => string` |
| `yamlLoadFile` | fn | No | `(path: string) => unknown` |
| `yamlGetValue` | fn | No | `(content: string, keyPath: string) => unknown` |
| `yamlGetStringValue` | fn | No | `(content: string, keyPath: string, default: string) => string` |
| `yamlGetVecValue` | fn | No | `(content: string, keyPath: string) => string[]` |
| `yamlGetHashmapValue` | fn | No | `(content: string, keyPath: string) => Record<string, string>` |
| `yamlSaveFile` | fn | No | `(path: string, data: unknown) => void` |
| `yamlSetSetting` | fn | No | `(content: string, keyPath: string, value: unknown) => string` |
| `yamlClearCache` | fn | No | `() => void` |
| `yamlGetCacheStats` | fn | No | `() => CacheStats` |
| `yamlGetSettingsBatch` | fn | No | `(content: string, keyPaths: string[]) => Record<string, unknown>` |
| `yamlSetSettingsBatch` | fn | No | `(content: string, settings: Record<string, unknown>) => string` |
| `yamlLoadFilesBatch` | fn | Yes | `(paths: string[]) => Promise<Record<string, unknown>>` |
| `YamlDocument` | class | No | See Section 6.2 |

#### FileIO Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `FileIOCore` | class | Yes | See Section 6.3 |
| `FileHasher.hashFile` | static | Yes | `(path: string) => Promise<string>` |
| `FileHasher.hashFilesParallel` | static | Yes | `(paths: string[]) => Promise<Record<string, string>>` |
| `DDSHeader.parse` | static | No | `(data: Buffer) => DDSHeaderInfo` |
| `LogCollector.collectAll` | static | Yes | `(directory: string) => Promise<string[]>` |
| `BackupManager.createBackup` | static | Yes | `(sourcePath: string, backupDir: string) => Promise<string>` |
| `BackupManager.listVersions` | static | No | `(backupDir: string) => string[]` |
| `walkDirectory` | fn | No | `(path: string, pattern?: string) => string[]` |
| `generateIgnoreFile` | fn | Yes | `(path: string, entries: string[]) => Promise<void>` |
| `generateLocalYaml` | fn | Yes | `(path: string, config: unknown) => Promise<void>` |

#### Database Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `DatabasePool` | class | Yes | See Section 6.4 |

#### Constants Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `getGameName` | fn | No | `(id: GameId) => string` |
| `getYamlFilePath` | fn | No | `(file: YamlFile, gameId: GameId) => string` |
| `getFallout4VersionInfo` | fn | No | `(version: Fallout4Version) => object` |
| `getAllGameIds` | fn | No | `() => GameId[]` |
| `getAllYamlFiles` | fn | No | `() => YamlFile[]` |

#### Version Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `parseVersion` | fn | No | `(input: string) => string` |
| `tryParseVersion` | fn | No | `(input: string) => string \| null` |
| `compareVersions` | fn | No | `(a: string, b: string) => -1 \| 0 \| 1` |
| `isKnownFallout4Version` | fn | No | `(version: string) => boolean` |
| `extractVersionFromFilename` | fn | No | `(filename: string) => string \| null` |
| `extractVersionFromLog` | fn | No | `(content: string) => string \| null` |
| `extractAllVersions` | fn | No | `(content: string) => string[]` |
| `formatVersion` | fn | No | `(version: string) => string` |

#### Update Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `GithubClient` | class | Yes | See Section 6.7 |

#### Version Registry Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `getVersionById` | fn | No | `(id: string) => VersionInfo \| null` |
| `getVersionByVersion` | fn | No | `(version: GameVersion) => VersionInfo \| null` |
| `getVersionByShortName` | fn | No | `(name: string) => VersionInfo \| null` |
| `getAllVersions` | fn | No | `() => VersionInfo[]` |
| `getVersionsForGame` | fn | No | `(gameId: string) => VersionInfo[]` |
| `getCorrectVersions` | fn | No | `(gameId: string) => VersionInfo[]` |
| `getWrongVersions` | fn | No | `(gameId: string) => VersionInfo[]` |
| `matchVersion` | fn | No | `(version: GameVersion, gameId: string) => MatchResult` |

#### Config Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `YamlDataCore` | class | Yes | See Section 6.9 |

#### Scangame Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `BA2Scanner` | class | Yes | See Section 6.10 |
| `ConfigDuplicateDetector` | class | No | See Section 6.10 |
| `EnbChecker` | class | No | See Section 6.10 |
| `IniValidator` | class | No | See Section 6.10 |
| `GameIntegrityChecker` | class | Yes | See Section 6.10 |
| `CrashgenChecker` | class | No | See Section 6.10 |
| `UnpackedScanner` | class | No | See Section 6.10 |
| `XseChecker` | class | No | See Section 6.10 |

#### Path Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `GamePathFinder.find` | static | No | `(gameId: string) => string \| null` |
| `DocsPathFinder.find` | static | No | `(gameId: string) => string \| null` |
| `DocumentsChecker.check` | static | No | `(docsPath: string) => IniCheckResult[]` |
| `validatePath` | fn | No | `(path: string) => boolean` |
| `validateGamePath` | fn | No | `(path: string, gameId: string) => boolean` |
| `validateModsPath` | fn | No | `(path: string) => boolean` |
| `findFileInDirectory` | fn | No | `(dir: string, filename: string) => string \| null` |
| `getRelativePath` | fn | No | `(from: string, to: string) => string` |
| `normalizePath` | fn | No | `(path: string) => string` |

#### Shared Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `normalizePath` | fn | No | `(path: string) => string` |
| `joinPaths` | fn | No | `(...parts: string[]) => string` |
| `validatePathsBatch` | fn | No | `(paths: string[]) => Record<string, boolean>` |
| `internString` | fn | No | `(value: string) => string` |
| `processStringBatch` | fn | No | `(values: string[]) => string[]` |
| `normalizeString` | fn | No | `(value: string) => string` |
| `recordTiming` | fn | No | `(label: string, durationMs: number) => void` |
| `getMetricsSummary` | fn | No | `() => MetricsSummary` |
| `clearMetrics` | fn | No | `() => void` |
| `registryGet` | fn | No | `(key: string) => unknown \| null` |
| `registrySet` | fn | No | `(key: string, value: unknown) => void` |
| `registryRemove` | fn | No | `(key: string) => boolean` |
| `registryClear` | fn | No | `() => void` |
| `isRuntimeAvailable` | fn | No | `() => boolean` |
| `getRuntimeInfo` | fn | No | `() => RuntimeInfo` |

#### Resource Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `detectResourceType` | fn | No | `(path: string) => ResourceType` |
| `enumerateResources` | fn | No | `(directory: string) => string[]` |
| `countResourcesByType` | fn | No | `(directory: string) => Record<ResourceType, number>` |

#### Web Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `validateModUrl` | fn | No | `(url: string) => boolean` |
| `detectModSite` | fn | No | `(url: string) => ModSite \| null` |
| `buildModUrl` | fn | No | `(site: ModSite, modId: string) => string` |

#### XSE Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `detectXseVersion` | fn | No | `(gamePath: string, xseType: XseType) => string \| null` |
| `isXseInstalled` | fn | No | `(gamePath: string, xseType: XseType) => boolean` |
| `getXseInfo` | fn | No | `(gamePath: string, xseType: XseType) => XseInfo` |

#### Message Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `createMessage` | fn | No | `(type: MessageType, content: string, target?: MessageTarget) => Message` |
| `formatMessage` | fn | No | `(message: Message) => string` |
| `createLogger` | fn | No | `(name: string) => Logger` |
| `Logger` | class | No | See Section 6.16 |

#### Settings Module

| Export | Kind | Async | Signature |
|--------|------|-------|-----------|
| `SettingsCache` | class | Yes | See Section 6.17 |

### C. Excluded APIs

| API | Crate | Reason |
|-----|-------|--------|
| `AsyncBridge` | classic-pybridge-core | Python-specific (GIL, Slint event loop) |
| `GilHelper` | classic-pybridge-core | Python-specific |
| `PyO3 dunder methods` | all -py crates | Python-specific (`__repr__`, `__str__`, `__eq__`) |
| `metrics_for_pybridge` | classic-perf-core | Python-specific; general metrics merged into shared |

---

*End of PRD*
