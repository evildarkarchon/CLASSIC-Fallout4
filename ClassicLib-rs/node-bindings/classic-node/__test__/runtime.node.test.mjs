import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const require = createRequire(import.meta.url);
const classic = require("../index.js");

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
Crashlog_Error_Check: {}
Crashlog_Stack_Check: {}
Mods_CONF: {}
Mods_CORE: {}
Mods_CORE_FOLON: {}
Mods_FREQ: {}
Mods_OPC2: {}
Mods_SOLU: {}
`;

const IGNORE_YAML = `
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
`;

test("loads native binding in Node runtime", () => {
  assert.equal(typeof classic.getVersion, "function");
  assert.equal(typeof classic.createAnalysisConfig, "function");
  assert.equal(typeof classic.getVersionById, "function");
});

test("runs Tier-1 sync APIs in Node runtime", () => {
  const config = classic.createAnalysisConfig("Fallout4", "auto");
  assert.equal(config.game, "Fallout4");
  assert.equal(config.gameVersion, "auto");

  const fromYaml = classic.createAnalysisConfigFromYamlContent(
    MAIN_YAML,
    GAME_YAML,
    IGNORE_YAML,
    "Fallout4",
    "auto",
  );
  assert.equal(fromYaml.crashgenName, "Buffout 4");
  assert.equal(fromYaml.xseAcronym, "F4SE");

  const versions = classic.getAllVersionsForGame("Fallout4");
  assert.equal(Array.isArray(versions), true);
  assert.equal(versions.length > 0, true);

  const sourceName = classic.getYamlSourceDisplayName("Main");
  assert.equal(sourceName, "Main Database");
});

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
});

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

test("supports optional params and stable string mappings in Node runtime", () => {
  const all = classic.getAllVersionsForGame("Fallout4");
  const vrOnly = classic.getAllVersionsForGame("Fallout4", true);
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
    assert.equal(classic.stripEmojiText("Ready [ok]"), "Ready [ok]");

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

test("runs Tier-1 async API in Node runtime", async () => {
  const results = await classic.processLogsBatchWithYamlContent(
    [],
    MAIN_YAML,
    GAME_YAML,
    IGNORE_YAML,
    "Fallout4",
    "auto",
  );
  assert.deepEqual(results, []);
});
