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
  const config = classic.createAnalysisConfig("Fallout4", false);
  assert.equal(config.game, "Fallout4");
  assert.equal(config.vrMode, false);

  const fromYaml = classic.createAnalysisConfigFromYamlContent(
    MAIN_YAML,
    GAME_YAML,
    IGNORE_YAML,
    "Fallout4",
    false,
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

test("runs Tier-1 async API in Node runtime", async () => {
  const results = await classic.processLogsBatchWithYamlContent(
    [],
    MAIN_YAML,
    GAME_YAML,
    IGNORE_YAML,
    "Fallout4",
    false,
  );
  assert.deepEqual(results, []);
});
