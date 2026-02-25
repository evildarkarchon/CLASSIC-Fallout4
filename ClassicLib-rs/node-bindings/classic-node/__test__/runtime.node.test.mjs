import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

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
