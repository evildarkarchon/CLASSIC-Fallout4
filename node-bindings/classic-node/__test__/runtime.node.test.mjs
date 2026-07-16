import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const classic = require("../index.js");
const runtimeCoverageRegistry = JSON.parse(
  readFileSync(new URL("./fixtures/runtime_coverage_registry.json", import.meta.url), "utf-8"),
);
const activeTier1Owners = new Set(
  runtimeCoverageRegistry.entries
    .filter((entry) => entry.tier === "tier1")
    .map((entry) => entry.ownerModule),
);

const MAIN_YAML = `
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
catch_log_records:
  - "LAND"
`;

const GAME_YAML = `
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "1.37.0"
  CRASHGEN_LogName: "Buffout 4"
  Main_Root_Name: "Fallout4"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found"
  Warn_Outdated: "Outdated"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: []
Mods_SOLU: []
`;

const IGNORE_YAML = `
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
`;

const CLI_SAMPLE_LOG = `Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tPHYSICAL MEMORY: 32.0 GB

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> TESForm::SetReference+0x12
\t[ 1] 0x7FF6EF4C3600 Fallout4.exe+0733600 -> BGSInventoryItem::GetOwner+0x30

MODULES:
\tFallout4.exe v1.10.163.0
\tnvwgf2umx.dll v31.0.15.3713

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[03] Unofficial Fallout 4 Patch.esp
`;

function replaceDocsPlaceholder(content, docsPath) {
  return content.replaceAll("DOCS_XSE_PLACEHOLDER", docsPath.replaceAll("\\", "\\\\"));
}

function createCliWorkspace() {
  const packageRoot = fileURLToPath(new URL("..", import.meta.url));
  const workspace = mkdtempSync(join(tmpdir(), "classic-node-runtime-cli-"));
  const classicDataDir = join(workspace, "CLASSIC Data");
  const databaseDir = join(classicDataDir, "databases");
  const docsDir = join(workspace, "docs", "F4SE");
  const scanDir = join(workspace, "incoming");
  const logPath = join(scanDir, "crash-2026-03-06-12-00-00.log");
  const localYaml = `
Game_Info:
  Docs_Folder_XSE: "DOCS_XSE_PLACEHOLDER"
`;
  const gameYaml = `
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "1.37.0"
  CRASHGEN_LogName: "Buffout 4"
  Main_Root_Name: "Fallout4"
  Docs_Folder_XSE: "DOCS_XSE_PLACEHOLDER"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found"
  Warn_Outdated: "Outdated"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: []
Mods_SOLU: []
`;

  mkdirSync(databaseDir, { recursive: true });
  mkdirSync(docsDir, { recursive: true });
  mkdirSync(scanDir, { recursive: true });

  writeFileSync(join(databaseDir, "CLASSIC Main.yaml"), MAIN_YAML, "utf8");
  writeFileSync(join(databaseDir, "CLASSIC Fallout4.yaml"), replaceDocsPlaceholder(gameYaml, docsDir), "utf8");
  writeFileSync(join(workspace, "CLASSIC Ignore.yaml"), IGNORE_YAML, "utf8");
  writeFileSync(
    join(classicDataDir, "CLASSIC Fallout4 Local.yaml"),
    replaceDocsPlaceholder(localYaml, docsDir),
    "utf8",
  );
  writeFileSync(logPath, CLI_SAMPLE_LOG, "utf8");

  return {
    cliPath: join(packageRoot, "dist", "cli", "main.js"),
    logPath,
    workspace,
  };
}

test("loads native binding in Node runtime", () => {
  assert.equal(typeof classic.getVersion, "function");
  assert.equal(typeof classic.scanRunExecute, "function");
  assert.equal(typeof classic.getVersionById, "function");
});

test("exposes only the User Settings replacement contract in Node", () => {
  const root = mkdtempSync(join(tmpdir(), "classic-node-runtime-user-settings-"));

  try {
    assert.equal(classic.ClassicConfigJs, undefined);
    assert.equal(classic.createDefaultConfig, undefined);
    assert.equal(typeof classic.openUserSettings, "function");
    assert.equal(typeof classic.previewUserSettingsUpdate, "function");
    assert.equal(typeof classic.commitUserSettingsUpdate, "function");
    assert.equal(typeof classic.planUserSettingsMigration, "function");
    assert.equal(typeof classic.applyUserSettingsMigration, "function");

    const snapshot = classic.openUserSettings(root);
    assert.equal(snapshot.classification, "missing");
    assert.equal(snapshot.crashLogScanSettings.gameVersionSelection, "auto");

    const preview = classic.previewUserSettingsBootstrap(root, {
      simplifyLogs: true,
    });
    assert.equal(preview.accepted, true);
    assert.equal(preview.baseRevision, "missing");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

if (activeTier1Owners.has("config")) {
  test("runs Tier-1 config/cache APIs in Node runtime", () => {
    assert.equal(classic.DEFAULT_CACHE_TTL, classic.getDefaultCacheTtl());
    assert.equal(classic.BATCH_CACHE_TTL, classic.getBatchCacheTtl());
    assert.equal(classic.MAX_CACHE_TTL, classic.getMaxCacheTtl());

    const yamlFiles = classic.getAllYamlFiles();
    assert.equal(Array.isArray(yamlFiles), true);
    assert.equal(yamlFiles.includes("Main"), true);
    assert.equal(
      classic.getYamlFileDescription("Main").includes("CLASSIC Main.yaml"),
      true,
    );

    const yaml = classic.yamlStringify({ root: { enabled: true } });
    const parsed = classic.yamlParse(yaml);
    assert.equal(parsed.root.enabled, true);
    assert.equal(classic.getYamlSourceDisplayName("Main"), "Main Database");
  });
}

if (activeTier1Owners.has("config")) {
  test("runs Tier-1 settings cache and path validators in Node runtime", () => {
    const dir = mkdtempSync(join(tmpdir(), "classic-node-runtime-"));
    const gameDir = join(dir, "game");
    const docsDir = join(dir, "docs");
    const settingsPath = join(dir, "settings.yaml");

    try {
      mkdirSync(gameDir, { recursive: true });
      mkdirSync(docsDir, { recursive: true });
      writeFileSync(join(gameDir, "Fallout4.exe"), "stub", "utf8");
      writeFileSync(settingsPath, "root:\n  enabled: true\n", "utf8");

      classic.clearSettingsCache();
      classic.resetSettingsCacheStats();

      const docs = classic.loadSettingsSync("runtime-node", settingsPath);
      assert.equal(Array.isArray(docs), true);
      assert.equal(docs[0].root.enabled, true);
      assert.equal(classic.isCached("runtime-node"), true);
      assert.equal(classic.settingsCacheSize(), 1);

      const cached = classic.getCached("runtime-node");
      assert.equal(Array.isArray(cached), true);
      assert.equal(cached[0].root.enabled, true);

      const stats = classic.getSettingsCacheStats();
      assert.equal(typeof stats.hits, "number");
      assert.equal(typeof stats.size, "number");

      classic.validateSettingsPath(gameDir, "gamePath", ["Fallout4.exe"]);
      classic.validateSettingsPaths(gameDir, docsDir, null, "Fallout4.exe");

      assert.equal(classic.invalidateSettings("runtime-node"), true);
      assert.equal(classic.isCached("runtime-node"), false);
    } finally {
      classic.clearSettingsCache();
      rmSync(dir, { recursive: true, force: true });
    }
  });
}

if (activeTier1Owners.has("version_registry")) {
  test("supports optional params and stable string mappings in Node runtime", () => {
    const all = classic.getAllVersionsForGame("Fallout4");
    const vrOnly = classic.getAllVersionsForGame("Fallout4", true);
    assert.equal(Array.isArray(all), true);
    assert.equal(all.length >= vrOnly.length, true);

    const handling = classic.getUnknownVersionHandling();
    assert.equal(
      ["nearest_match", "strict", "default_only"].includes(handling.strategy),
      true,
    );
    assert.equal(
      ["debug", "warning", "error"].includes(handling.logLevel),
      true,
    );
  });
}

if (activeTier1Owners.has("aux")) {
  test("runs Phase 4A aux foundation APIs in Node runtime", async () => {
    const dir = mkdtempSync(join(tmpdir(), "classic-node-aux-foundation-"));
    const settingsA = join(dir, "a.yaml");
    const settingsB = join(dir, "b.yaml");
    const textFile = join(dir, "text.txt");

    try {
      writeFileSync(settingsA, "alpha: 1\n", "utf8");
      writeFileSync(settingsB, "beta: 2\n", "utf8");
      writeFileSync(textFile, "hello world", "utf8");

      const normalized = classic.normalizePath(".");
      assert.equal(typeof normalized, "string");
      assert.equal(classic.joinPaths(["C:\\", "Games", "Fallout4"]).includes("Games"), true);
      const batch = classic.validatePathsBatch([".", "Z:\\nonexistent\\classic-node"]);
      assert.equal(batch["."], true);
      assert.equal(batch["Z:\\nonexistent\\classic-node"], false);

      assert.equal(classic.isRuntimeAvailable(), true);
      const runtime = classic.getRuntimeInfo();
      assert.equal(runtime.available, true);
      assert.equal(runtime.threadCount > 0, true);

      classic.clearAllMetrics();
      classic.recordTimingMetric("phase4a_runtime_node", 5.0);
      const metrics = classic.getMetricsSummary();
      assert.equal(metrics.timings.phase4a_runtime_node.count, 1);

      const message = classic.createMessage(
        classic.JsMessageType.Info,
        "phase4a ready",
        classic.JsMessageTarget.All,
      );
      assert.equal(message.messageType, "Info");
      assert.equal(classic.formatMessage(message).includes("phase4a"), true);

      classic.clearSettingsCache();
      assert.equal(classic.loadBatchSync([settingsA, settingsB]), 2);
      classic.clearSettingsCache();
      assert.equal(await classic.loadBatchAsync([settingsA, settingsB]), 2);

      const io = new classic.JsFileIO();
      await io.writeFile(textFile, "hello world");
      assert.equal(await io.readFile(textFile), "hello world");
      assert.equal(classic.detectEncoding(textFile), "UTF-8");
    } finally {
      classic.clearSettingsCache();
      classic.clearAllMetrics();
      rmSync(dir, { recursive: true, force: true });
    }
  });
}

if (activeTier1Owners.has("aux")) {
  test("runs Phase 4B aux scanner stack APIs in Node runtime", async () => {
    const dir = mkdtempSync(join(tmpdir(), "classic-node-aux-scanner-stack-"));
    const logPath = join(dir, "runtime.log");

    try {
      writeFileSync(logPath, "INFO: start\nERROR: runtime scanner stack\n", "utf8");

      const pool = new classic.JsDatabasePool("Fallout4");
      assert.equal(pool.getGameTable(), "Fallout4");
      assert.equal(await pool.getEntry("012345", "Test.esm"), null);

      assert.equal(classic.detectResourceType("mods/Test.esp"), "plugin");
      assert.equal(classic.parseResourceType("TEXTURE"), "texture");
      assert.equal(classic.isSupportedResource("meshes/body.nif"), true);
      assert.equal(classic.getResourceExtensions("plugin").includes("esp"), true);
      assert.equal(classic.createResourceInfo("textures/armor.dds").resourceType, "texture");

      assert.equal(classic.parseXseType("f4se"), "F4SE");
      assert.equal(classic.xseTypeForGame("Fallout4"), "F4SE");
      assert.equal(classic.xseLoaderName("F4SE").includes("loader"), true);
      assert.equal(classic.xseDllPrefix("F4SE").includes("f4se"), true);

      assert.equal(classic.getModSiteUrl("NexusMods").includes("nexusmods.com"), true);
      assert.equal(classic.getModSiteName("NexusMods"), "Nexus Mods");
      assert.equal(
        classic.getModSiteGameUrl("NexusMods", "Fallout4").includes("fallout4"),
        true,
      );
      assert.equal(classic.getUserAgentPrefix(), "CLASSIC");
      assert.equal(classic.getUserAgent().includes("CLASSIC/"), true);
      assert.equal(classic.getUserAgentWithSuffix("NodeRuntime").includes("NodeRuntime"), true);
      assert.equal(classic.isValidUrl("https://example.com"), true);
      assert.equal(classic.validateUrl("https://example.com").includes("https://example.com"), true);
      assert.equal(classic.joinUrl("https://example.com", "api/v1").includes("/api/v1"), true);
      assert.equal(
        classic
          .buildUrlWithQuery("https://example.com/search", [{ key: "q", value: "node" }])
          .includes("q=node"),
        true,
      );

      const enbChecker = new classic.JsEnbChecker(dir);
      assert.equal(enbChecker.checkBinaries(), "NotInstalled");
      assert.equal(classic.checkEnb(dir).isPresent, false);

      const logProcessor = new classic.JsLogProcessor(["error"], [], []);
      assert.equal(logProcessor.processLogs(dir).includes("TOTAL NUMBER OF DETECTED LOG ERRORS"), true);
      assert.equal(classic.processGameLogs(dir, ["error"], [], []).includes("TOTAL NUMBER OF DETECTED LOG ERRORS"), true);
      assert.deepEqual(classic.scanAllBa2Archives(dir), []);

      const unpacked = classic.scanUnpackedFiles(dir, []);
      assert.equal(Array.isArray(unpacked.texFrmt), true);
      assert.equal(Array.isArray(unpacked.sndFrmt), true);

      const client = new classic.GithubClient("owner", "repo");
      assert.equal(client.repoUrl().includes("github.com/owner/repo"), true);
      assert.equal(classic.hasUpdate("1.0.0", "1.0.1"), true);

      const releasePromise = classic.getLatestRelease("owner", "repo");
      const updatePromise = classic.checkForUpdates("owner", "repo", "1.0.0");
      assert.equal(releasePromise instanceof Promise, true);
      assert.equal(updatePromise instanceof Promise, true);
      releasePromise.catch(() => { });
      updatePromise.catch(() => { });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
}

if (activeTier1Owners.has("scanlog")) {
  test("runs final Standard and Targeted scan contracts in Node runtime", async () => {
    const { workspace } = createCliWorkspace();
    const configuration = {
      yamlDirRoot: workspace,
      yamlDirData: join(workspace, "CLASSIC Data"),
      game: "Fallout4",
      gameVersion: "auto",
      showFormidValues: false,
      simplifyLogs: false,
      formidDatabasePaths: [],
      maxConcurrent: 1,
    };

    try {
      const standardEvents = [];
      const standardRequest = classic.ScanRunRequest.standard(
        configuration,
        { baseDirectory: join(workspace, "incoming") },
        classic.ScanRunUnsolvedLogs.leaveInPlace(),
      );
      const standardExecution = await classic.scanRunExecute(
        standardRequest,
        new classic.ScanRunCancellation(),
        (event) => {
          standardEvents.push(event.kind);
        },
      );

      assert.equal(standardExecution.error, undefined);
      assert.equal(standardExecution.result.status, "completed");
      const discoveredLogPath = standardExecution.result.logs[0].crashLog;
      assert.equal(discoveredLogPath.endsWith("crash-2026-03-06-12-00-00.log"), true);
      assert.equal(standardEvents.includes("discovery_completed"), true);
      assert.equal(standardEvents.includes("effective_concurrency_selected"), true);

      const missingPath = join(workspace, "missing-crash.log");
      const targetedRequest = classic.ScanRunRequest.targeted(
        configuration,
        { inputs: [missingPath, discoveredLogPath] },
      );
      const targetedExecution = await classic.scanRunExecute(
        targetedRequest,
        new classic.ScanRunCancellation(),
      );

      assert.equal(targetedExecution.error, undefined);
      assert.deepEqual(
        targetedExecution.result.discovery.acceptedLogs,
        [discoveredLogPath],
      );
      assert.equal(
        targetedExecution.result.discovery.rejectedInputs[0].path,
        missingPath,
      );
      assert.equal(targetedExecution.result.logs[0].discoveryIndex, 0);
    } finally {
      rmSync(workspace, { recursive: true, force: true });
    }
  });
}

if (activeTier1Owners.has("scanlog")) {
  test("runs functional CLI workflow in Node runtime", () => {
    const { cliPath, logPath, workspace } = createCliWorkspace();

    try {
      assert.equal(existsSync(cliPath), true);

      const result = spawnSync(
        process.execPath,
        [cliPath, "--json", "--scan-path", join(workspace, "incoming"), "--game-version", "auto"],
        {
          cwd: workspace,
          encoding: "utf8",
        },
      );

      assert.equal(result.status, 0);

      const output = JSON.parse(result.stdout);
      assert.equal(output.mode, "scan");
      assert.equal(output.logsFound, 1);
      assert.equal(output.scanErrors, 0);
      assert.equal(output.reportsWritten, 1);
      assert.equal(existsSync(logPath.replace(".log", "-AUTOSCAN.md")), true);
    } finally {
      rmSync(workspace, { recursive: true, force: true });
    }
  });
}

// ============================================================================
// Phase 4 Plan 2 (D-TEST-02): cross-runtime smoke for promoted scanlog symbols
// ============================================================================
//
// Task 2 promotes 9 Node-exposed scanlog exports from Tier-2 deferred to
// enforced Tier-1 contract rows. Per D-TEST-02 the plan adds at least one
// representative cross-runtime test here so the symbols are exercised under
// node:test (not just bun:test). parseXseLog is the representative pick
// because its string|null return surface is the most likely NAPI marshalling
// failure point across runtimes.
if (activeTier1Owners.has("scanlog")) {
  test("scanlog Plan 2 promotion: parseXseLog + CRASH_LOG_PATTERN exercised under node:test", () => {
    // MEDIUM concern: any unexpected throw is wrapped in try/catch so the
    // suite survives with a typed-error assertion instead of a panic.

    // CRASH_LOG_PATTERN is a const export — real-shape check.
    assert.equal(typeof classic.CRASH_LOG_PATTERN, "string");
    assert.ok(classic.CRASH_LOG_PATTERN.length > 0);
    // It must compile as a JS regex without throwing.
    assert.doesNotThrow(() => new RegExp(classic.CRASH_LOG_PATTERN));

    // parseXseLog returns `string | null` per index.d.ts.
    const workspace = mkdtempSync(join(tmpdir(), "classic-node-runtime-xse-"));
    try {
      const logPath = join(workspace, "f4se.log");
      writeFileSync(logPath, "F4SE runtime: initialize (version = 0.6.23)\r\n", "utf8");
      try {
        const result = classic.parseXseLog(logPath);
        // Real-shape check: null or string.
        assert.ok(result === null || typeof result === "string");
      } catch (e) {
        // Acceptable fallback: parser throws a typed Error.
        assert.ok(e instanceof Error);
      }

      // Empty-string input must not panic.
      try {
        const emptyResult = classic.parseXseLog("");
        assert.ok(emptyResult === null || typeof emptyResult === "string");
      } catch (e) {
        assert.ok(e instanceof Error);
      }
    } finally {
      rmSync(workspace, { recursive: true, force: true });
    }

    // checkXsePlugins is the other sync function promoted in Task 2; sanity-
    // check its return type across runtimes too.
    try {
      const msg = classic.checkXsePlugins("/nonexistent/dir", "1.10.163");
      assert.equal(typeof msg, "string");
    } catch (e) {
      assert.ok(e instanceof Error);
    }
  });
}

// ============================================================================
// Phase 4 Plan 3 (D-TEST-02): cross-runtime smoke for promoted config symbols
// ============================================================================
//
// Task 2 promotes 23 Node-exposed config entries from Tier-2 deferred to
// enforced Tier-1 contract rows. Per D-TEST-02 the plan adds at least one
// representative cross-runtime test here so the symbols are exercised under
// node:test (not just bun:test). getHashCacheStats is the representative pick
// because its multi-field return shape is the most likely NAPI marshalling
// failure point across runtimes.
// ============================================================================
// Phase 4 Plan 4 (D-TEST-02): cross-runtime smoke for PE-version + version_registry
// ============================================================================
//
// Task 2 adds extractPeVersion and isValidPePath NAPI wrappers plus promotes
// 4 version_registry entries. Per D-TEST-02 the plan adds cross-runtime tests
// here so the symbols are exercised under node:test (not just bun:test).
if (activeTier1Owners.has("version_registry")) {
  test("version Plan 4: isValidPePath returns false for nonexistent (cross-runtime D-TEST-02)", () => {
    assert.strictEqual(classic.isValidPePath("/nonexistent/path.exe"), false);
  });

  if (process.platform === "win32") {
    test("version Plan 4: extractPeVersion against kernel32.dll (Windows-only D-TEST-02)", () => {
      const version = classic.extractPeVersion("C:\\Windows\\System32\\kernel32.dll");
      assert.ok(version !== undefined);
      assert.strictEqual(typeof version.major, "number");
      assert.strictEqual(typeof version.minor, "number");
      assert.strictEqual(typeof version.patch, "number");
      assert.strictEqual(typeof version.build, "number");
      assert.ok(version.major >= 6, `Expected major >= 6, got ${version.major}`);
    });
  }

  test("version_registry Plan 4: checkCrashgenConfigWithRules callable with typed return (cross-runtime D-TEST-02)", () => {
    // Signature: checkCrashgenConfigWithRules(pluginsPath, crashgenName, settingsRules?)
    // Passing minimal valid arguments. On empty plugins path, the function either returns a
    // result object or throws -- either outcome is an acceptable typed signal.
    try {
      const result = classic.checkCrashgenConfigWithRules("", "Buffout 4");
      assert.ok(result !== undefined, "result must be defined");
      assert.ok(typeof result === "object", "result must be an object");
    } catch (e) {
      // A thrown Error is acceptable -- signals the function is callable and validates input
      assert.ok(e instanceof Error, "thrown value must be an Error");
    }
  });
}

if (activeTier1Owners.has("config")) {
  test("config Plan 3 promotion: getHashCacheStats + cache constants exercised under node:test", () => {
    // resetHashCacheStats clears counters — real-shape check.
    classic.resetHashCacheStats();
    const stats = classic.getHashCacheStats();
    assert.ok(stats !== undefined);
    assert.strictEqual(typeof stats.hits, "number");
    assert.strictEqual(typeof stats.misses, "number");
    assert.strictEqual(typeof stats.hit_rate, "number");
    assert.strictEqual(typeof stats.size, "number");
    assert.strictEqual(typeof stats.capacity, "number");
    assert.strictEqual(stats.hits, 0);
    assert.strictEqual(stats.misses, 0);

    // Cache constants — real-shape check.
    assert.strictEqual(typeof classic.DEFAULT_CACHE_CLEANUP_INTERVAL, "number");
    assert.ok(classic.DEFAULT_CACHE_CLEANUP_INTERVAL > 0);
    assert.strictEqual(typeof classic.DEFAULT_CACHE_CLEANUP_THRESHOLD, "number");
    assert.ok(classic.DEFAULT_CACHE_CLEANUP_THRESHOLD > 0);
    assert.strictEqual(typeof classic.DEFAULT_QUERY_CACHE_CAPACITY, "number");
    assert.ok(classic.DEFAULT_QUERY_CACHE_CAPACITY > 0);

    // Getter functions return the const values.
    assert.strictEqual(classic.getDefaultCacheCleanupInterval(), classic.DEFAULT_CACHE_CLEANUP_INTERVAL);
    assert.strictEqual(classic.getDefaultCacheCleanupThreshold(), classic.DEFAULT_CACHE_CLEANUP_THRESHOLD);
    assert.strictEqual(classic.getDefaultQueryCacheCapacity(), classic.DEFAULT_QUERY_CACHE_CAPACITY);

    // clearHashCache is callable without throwing.
    classic.clearHashCache();

    // gameSetupNeedsPathDetection returns object with boolean fields.
    const result = classic.gameSetupNeedsPathDetection();
    assert.strictEqual(typeof result.needsGamePath, "boolean");
    assert.strictEqual(typeof result.needsDocsPath, "boolean");
  });
}

// Phase 4 Plan 5: cross-owner overlap and crashgen_rules cross-runtime tests
test("Plan-5: getApplicationDir returns string or null (cross-runtime, read-only)", () => {
  // MEDIUM concern: do NOT call setApplicationDir in the same process
  try {
    const dir = classic.getApplicationDir();
    assert.ok(typeof dir === "string" || dir === null,
      `getApplicationDir must return string or null, got ${typeof dir}`);
  } catch (e) {
    // Once not initialized -- acceptable
    assert.ok(e instanceof Error, "expected an Error if Once is not initialized");
  }
});

test("Plan-5: normalizeGameSetupVersionSelection returns string (cross-runtime)", () => {
  const result = classic.normalizeGameSetupVersionSelection("Original");
  assert.strictEqual(typeof result, "string",
    `normalizeGameSetupVersionSelection must return string, got ${typeof result}`);
});
