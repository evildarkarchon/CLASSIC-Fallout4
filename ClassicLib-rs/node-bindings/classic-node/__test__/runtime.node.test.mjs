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
Crashlog_Error_Check: {}
Crashlog_Stack_Check: {}
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: {}
Mods_OPC2: {}
Mods_SOLU: {}
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
GameVR_Info:
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
Crashlog_Error_Check: {}
Crashlog_Stack_Check: {}
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: {}
Mods_OPC2: {}
Mods_SOLU: {}
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
  assert.equal(typeof classic.createAnalysisConfig, "function");
  assert.equal(typeof classic.getVersionById, "function");
});

if (activeTier1Owners.has("scanlog")) {
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
  });
}

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
