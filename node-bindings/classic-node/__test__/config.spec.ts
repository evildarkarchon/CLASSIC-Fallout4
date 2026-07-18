import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createHash } from "node:crypto";
import {
  // YamlData class
  YamlData,
  // Free functions
  createYamlDataFromContent,
  clearYamlCache,
  registryClear,
  getApplicationDir,
  setApplicationDir,
  getYamlSourcePath,
  getYamlSourceDisplayName,
  getYamlSourceDisplayNameWithGame,
  persistGameLocalPaths,
  JsGameId,
  loadExplicitYamlData,
} from "../index.js";
import { getRuntimeCoverageEntries } from "./fixtures/runtime_coverage_registry";

const THIS_SUITE =
  "node-bindings/classic-node/__test__/config.spec.ts";

// ============================================================================
// Test Fixtures
// ============================================================================

const MAIN_YAML = `
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
catch_log_records:
  - "LAND"
  - "REFR"
  - "CELL"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
  autoscan_text_Skyrim: "Autoscan Skyrim"
`;

const GAME_YAML = `
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "4.0.0"
  CRASHGEN_LogName: "crash-og"
Game_Hints:
  - "Hint 1"
  - "Hint 2"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found!"
  Warn_Outdated: "Your version is outdated."
Crashlog_Plugins_Exclude:
  - "Unofficial*.esp"
Crashlog_Records_Exclude:
  - "RecordType1"
Crashlog_Error_Check:
  - id: error_pattern_1
    name: Error Pattern 1
    severity: 4
    main_error_contains_any:
      - "Error description 1"
  - id: error_pattern_2
    name: Error Pattern 2
    severity: 2
    main_error_contains_any:
      - "Error description 2"
Crashlog_Stack_Check:
  - id: stack_pattern_1
    name: Stack Pattern 1
    severity: 3
    main_error_required_any:
      - "Main error required"
    main_error_optional_any:
      - "Main error optional"
    stack_contains_any:
      - "Stack pattern 1"
      - "Stack pattern 2"
    exclude_if_stack_contains_any:
      - "Excluded pattern"
    stack_contains_at_least:
      - substring: "Repeated pattern"
        count: 2
Mods_CONF:
  - mod_a: modA
    mod_b: modB
    name_a: Mod A
    name_b: Mod B
    description: "Config for ModA"
    fix: "Remove one."
Mods_CORE:
  - detect: ModB
    name: Core Mod B
    description: "Core mod B"
Mods_FREQ:
  - id: freq-mod
    criteria:
      any:
        - FreqMod
    name: Frequent Mod
    description: "Frequently used mod"
Mods_SOLU:
  - id: solu-mod
    criteria:
      any:
        - SoluMod
    name: Solution Mod
    description: "Solution mod"
`;

const IGNORE_YAML = `
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
  - "IgnoreItem2"
CLASSIC_Ignore_Skyrim:
  - "SkyrimIgnore1"
`;

const GAME_YAML_MAIN_ROOT_ONLY = `
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
`;

const EXPLICIT_MAIN_YAML = [
  'schema_version: "2.0"',
  "CLASSIC_Info:",
  '  version: "9.1.0"',
  "CLASSIC_Interface:",
  '  autoscan_text_Fallout4: "explicit node"',
  "",
].join("\r\n");

const EXPLICIT_GAME_YAML = `schema_version: "1.0"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_FREQ: []
Mods_SOLU: []
`;

const EXPLICIT_EMPTY_IGNORE_YAML = "CLASSIC_Ignore_Fallout4: []\n";

// ============================================================================
// YamlData: Construction
// ============================================================================

describe("YamlData construction", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("fromYamlContent creates a valid instance", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data).toBeDefined();
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("createYamlDataFromContent free function works", () => {
    const data = createYamlDataFromContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data).toBeDefined();
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("fromYamlContent throws on invalid YAML", () => {
    expect(() =>
      YamlData.fromYamlContent(
        "{ invalid: yaml: content: }}}",
        GAME_YAML,
        IGNORE_YAML,
        "Fallout4",
        "auto",
      ),
    ).toThrow(/Failed to parse main YAML:/);
  });

  test("fromYamlContent classifies parse failures as InvalidArg", () => {
    try {
      YamlData.fromYamlContent(
        "{ invalid: yaml: content: }}}",
        GAME_YAML,
        IGNORE_YAML,
        "Fallout4",
        "auto",
      );
      throw new Error("expected parse failure");
    } catch (err) {
      const error = err as Error & { code?: string };
      expect(error.code).toBe("InvalidArg");
      expect(error.message).toContain("Failed to parse main YAML:");
    }
  });

  test("fromYamlContent throws on empty document", () => {
    expect(() =>
      YamlData.fromYamlContent("", GAME_YAML, IGNORE_YAML, "Fallout4", "auto"),
    ).toThrow();
  });

  test("fromYamlContent keeps metadata non-empty when Game_Info only has Main_Root_Name", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML_MAIN_ROOT_ONLY,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );

    expect(data.crashgenName.length).toBeGreaterThan(0);
    expect(data.xseAcronym.length).toBeGreaterThan(0);
    expect(data.gameVersion.length).toBeGreaterThan(0);
  });
});

describe("explicit YAML Data loading", () => {
  test("loads arbitrary paths with typed VR role and exact byte identities", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-explicit-yaml-"));
    try {
      const mainPath = join(root, "chosen-main.fixture");
      const gamePath = join(root, "chosen-game.fixture");
      const ignorePath = join(root, "chosen-ignore.fixture");
      writeFileSync(mainPath, EXPLICIT_MAIN_YAML);
      writeFileSync(gamePath, EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, EXPLICIT_EMPTY_IGNORE_YAML);

      const snapshot = await loadExplicitYamlData(
        { mainPath, gamePath, ignorePath },
        JsGameId.Fallout4Vr,
        "VR",
      );

      expect(snapshot.game).toBe(JsGameId.Fallout4Vr);
      expect(snapshot.gameDataRole).toBe("Fallout4");
      expect(snapshot.yamlData.classicVersion).toBe("9.1.0");
      expect(snapshot.yamlData.ignoreList).toEqual([]);
      expect(snapshot.mainIdentity.byteLen).toBe(
        Buffer.byteLength(EXPLICIT_MAIN_YAML),
      );
      expect(snapshot.mainIdentity.sha256).toBe(
        createHash("sha256").update(EXPLICIT_MAIN_YAML).digest("hex"),
      );

      writeFileSync(mainPath, "replacement bytes");
      expect(snapshot.yamlData.classicVersion).toBe("9.1.0");
      expect(snapshot.mainIdentity.sha256).toBe(
        createHash("sha256").update(EXPLICIT_MAIN_YAML).digest("hex"),
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("returns stable typed unsupported-game and Local Ignore errors", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-explicit-yaml-errors-"));
    try {
      await expect(
        loadExplicitYamlData(
          {
            mainPath: join(root, "missing-main"),
            gamePath: join(root, "missing-game"),
            ignorePath: join(root, "missing-ignore"),
          },
          JsGameId.Skyrim,
          "AnniversaryEdition",
        ),
      ).rejects.toMatchObject({ code: "unsupported_game" });

      const mainPath = join(root, "chosen-main.fixture");
      const gamePath = join(root, "chosen-game.fixture");
      const ignorePath = join(root, "chosen-ignore.fixture");
      writeFileSync(mainPath, EXPLICIT_MAIN_YAML);
      writeFileSync(gamePath, EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, "CLASSIC_Ignore_Fallout4: not-a-sequence\n");

      await expect(
        loadExplicitYamlData(
          { mainPath, gamePath, ignorePath },
          JsGameId.Fallout4,
          "Original",
        ),
      ).rejects.toMatchObject({
        code: "invalid_role_data",
        yamlRole: "local_ignore",
        path: ignorePath,
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

describe("runtime coverage metadata", () => {
  test("tracks application directory and Game Local persistence adapters", () => {
    const bindingIdentifiers = new Set(
      getRuntimeCoverageEntries(THIS_SUITE).flatMap(
        (entry) => entry.bindingIdentifiers ?? [],
      ),
    );

    expect(bindingIdentifiers.has("getApplicationDir")).toBe(true);
    expect(bindingIdentifiers.has("setApplicationDir")).toBe(true);
    expect(bindingIdentifiers.has("persistGameLocalPaths")).toBe(true);
  });
});

describe("application directory overrides", () => {
  beforeEach(() => {
    registryClear();
  });

  afterEach(() => {
    registryClear();
  });

  test("setApplicationDir and getApplicationDir round-trip", () => {
    expect(getApplicationDir()).toBeNull();

    const appDir = mkdtempSync(join(tmpdir(), "classic-node-appdir-"));
    setApplicationDir(appDir);

    expect(getApplicationDir()).toBe(appDir);
  });
});

// ============================================================================
// YamlData: Main YAML Properties
// ============================================================================

describe("YamlData main YAML properties", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("classicVersion returns correct version", () => {
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("classicVersionDate returns correct date", () => {
    expect(data.classicVersionDate).toBe("2024-01-15");
  });

  test("classicRecordsList returns correct records", () => {
    expect(data.classicRecordsList).toEqual(["LAND", "REFR", "CELL"]);
  });

  test("autoscanText returns game-specific text", () => {
    expect(data.autoscanText).toBe("Autoscan Fallout 4");
  });

  test("classicGameHints returns correct hints", () => {
    expect(data.classicGameHints).toEqual(["Hint 1", "Hint 2"]);
  });
});

// ============================================================================
// YamlData: Game YAML Properties
// ============================================================================

describe("YamlData game properties", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("xseAcronym returns correct value", () => {
    expect(data.xseAcronym).toBe("F4SE");
  });

  test("gameVersion returns correct version", () => {
    expect(data.gameVersion).toBe("1.10.163");
  });

  test("crashgenLatestOg returns correct version", () => {
    expect(data.crashgenLatestOg).toBe("4.0.0");
  });

  test("does not expose deprecated VR and split-version YAML fields", () => {
    expect((data as unknown as Record<string, unknown>).gameVersionNew).toBeUndefined();
    expect((data as unknown as Record<string, unknown>).gameVersionVr).toBeUndefined();
    expect((data as unknown as Record<string, unknown>).crashgenLatestVr).toBeUndefined();
  });

  test("warnNoplugins returns correct warning", () => {
    expect(data.warnNoplugins).toBe("No plugins found!");
  });

  test("warnOutdated returns correct warning", () => {
    expect(data.warnOutdated).toBe("Your version is outdated.");
  });
});

// ============================================================================
// YamlData: Ignore Lists
// ============================================================================

describe("YamlData ignore lists", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("ignoreList returns Fallout4-specific entries", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.ignoreList).toEqual(["IgnoreItem1", "IgnoreItem2"]);
  });

  test("ignoreList returns Skyrim-specific entries", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Skyrim",
      "auto",
    );
    expect(data.ignoreList).toEqual(["SkyrimIgnore1"]);
  });

  test("gameIgnorePlugins returns correct list", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.gameIgnorePlugins).toEqual(["Unofficial*.esp"]);
  });

  test("gameIgnoreRecords returns correct list", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.gameIgnoreRecords).toEqual(["RecordType1"]);
  });
});

// ============================================================================
// YamlData: Suspect Patterns
// ============================================================================

describe("YamlData suspect patterns", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("suspectErrorRules returns structured rules", () => {
    const rules = data.suspectErrorRules;
    expect(rules).toHaveLength(2);
    expect(rules[0]).toMatchObject({
      id: "error_pattern_1",
      name: "Error Pattern 1",
      severity: 4,
      mainErrorContainsAny: ["Error description 1"],
    });
  });

  test("suspectStackRules returns structured rules", () => {
    const rules = data.suspectStackRules;
    expect(rules).toHaveLength(1);
    expect(rules[0]).toMatchObject({
      id: "stack_pattern_1",
      name: "Stack Pattern 1",
      severity: 3,
      mainErrorRequiredAny: ["Main error required"],
      mainErrorOptionalAny: ["Main error optional"],
      stackContainsAny: ["Stack pattern 1", "Stack pattern 2"],
      excludeIfStackContainsAny: ["Excluded pattern"],
    });
    expect(rules[0].stackContainsAtLeast).toEqual([
      { substring: "Repeated pattern", count: 2 },
    ]);
  });
});

// ============================================================================
// YamlData: Mod Databases
// ============================================================================

describe("YamlData mod databases", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("gameModsConf returns structured entries", () => {
    expect(data.gameModsConf).toHaveLength(1);
    expect(data.gameModsConf[0].modA).toBe("modA");
    expect(data.gameModsConf[0].description).toBe("Config for ModA");
  });

  test("gameModsCoreCount returns correct count", () => {
    expect(data.gameModsCoreCount).toBe(1);
  });

  test("gameModsCoreDetects returns detect ids", () => {
    expect(data.gameModsCoreDetects).toEqual(["ModB"]);
  });

  test("gameModsCoreNames returns display names", () => {
    expect(data.gameModsCoreNames).toEqual(["Core Mod B"]);
  });

  test("gameModsCoreDescriptions returns descriptions", () => {
    expect(data.gameModsCoreDescriptions).toEqual(["Core mod B"]);
  });

  test("gameModsFreq returns structured entries", () => {
    expect(data.gameModsFreq).toHaveLength(1);
    expect(data.gameModsFreq[0].id).toBe("freq-mod");
    expect(data.gameModsFreq[0].criteria.any).toEqual(["FreqMod"]);
    expect(data.gameModsFreq[0].name).toBe("Frequent Mod");
    expect(data.gameModsFreq[0].description).toBe("Frequently used mod");
  });

  test("legacy OPC2 YAML is not exposed through YamlData", () => {
    expect("gameModsOpc2" in data).toBe(false);
  });

  test("gameModsSolu returns structured entries", () => {
    expect(data.gameModsSolu).toHaveLength(1);
    expect(data.gameModsSolu[0].id).toBe("solu-mod");
    expect(data.gameModsSolu[0].criteria.any).toEqual(["SoluMod"]);
    expect(data.gameModsSolu[0].criteria.all).toBeUndefined();
    expect(data.gameModsSolu[0].exceptions).toEqual([]);
    expect(data.gameModsSolu[0].name).toBe("Solution Mod");
    expect(data.gameModsSolu[0].description).toBe("Solution mod");
  });
});

// ============================================================================
// YamlData: VR Mode
// ============================================================================

describe("YamlData VR mode", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("VR mode keeps shared YAML metadata and defers VR version metadata", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "VR",
    );
    // VR-specific static metadata is no longer sourced from YAML.
    // YamlData exposes shared config, while version-specific metadata now
    // comes from the version-registry APIs.
    expect(data.getCrashgenName()).toBe("crash-og");
    expect(data.getCrashgenIgnore()).toEqual([]);
    expect(data.crashgenName).toBe("crash-og");
  });

  test("non-VR mode reads from Game_Info section via accessor", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.getCrashgenName()).toBe("crash-og");
    expect(data.crashgenName).toBe("crash-og");
  });
});

// ============================================================================
// YamlData: toString
// ============================================================================

describe("YamlData toString", () => {
  test("toString returns a human-readable string", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    const str = data.toString();
    expect(typeof str).toBe("string");
    expect(str).toContain("YamlData(");
    expect(str).toContain("7.31.0");
  });
});

// ============================================================================
// YamlData: Missing Keys Default Gracefully
// ============================================================================

describe("YamlData missing keys", () => {
  test("missing YAML keys return empty defaults", () => {
    const sparseMain = "other_key: value\n";
    const sparseGame = "unrelated: data\n";
    const sparseIgnore = "different_game: []\n";

    const data = YamlData.fromYamlContent(
      sparseMain,
      sparseGame,
      sparseIgnore,
      "Fallout4",
      "auto",
    );

    expect(data.classicVersion).toBe("");
    expect(data.classicRecordsList).toEqual([]);
    expect(data.ignoreList).toEqual([]);
    expect(data.xseAcronym).toBe("");
    expect(data.suspectErrorRules).toEqual([]);
    expect(data.gameModsCoreCount).toBe(0);
  });
});

// ============================================================================
// Game Local Path Persistence
// ============================================================================

describe("Game Local path persistence", () => {
  test("updates supplied paths without touching User Settings", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-game-local-"));

    try {
      const localYamlPath = join(
        root,
        "CLASSIC Data",
        "CLASSIC Fallout4 Local.yaml",
      );
      const userSettingsPath = join(root, "CLASSIC Settings.yaml");
      const userSettingsSentinel =
        "{ malformed user settings that must stay untouched";

      mkdirSync(dirname(localYamlPath), { recursive: true });
      writeFileSync(
        localYamlPath,
        [
          "Game_Info:",
          "  Root_Folder_Game: C:/Games/Old",
          "  Root_Folder_Docs: C:/Users/Test/Documents/Existing",
          "  Docs_Folder_XSE: C:/Users/Test/Documents/Existing/F4SE",
          "",
        ].join("\n"),
        "utf8",
      );
      writeFileSync(userSettingsPath, userSettingsSentinel, "utf8");

      await persistGameLocalPaths(
        localYamlPath,
        "D:/Games/Fallout4",
        undefined,
      );

      const localYaml = readFileSync(localYamlPath, "utf8");
      expect(localYaml).toContain('Root_Folder_Game: "D:/Games/Fallout4"');
      expect(localYaml).toContain(
        'Root_Folder_Docs: "C:/Users/Test/Documents/Existing"',
      );
      expect(localYaml).toContain(
        'Docs_Folder_XSE: "C:/Users/Test/Documents/Existing/F4SE"',
      );
      expect(readFileSync(userSettingsPath, "utf8")).toBe(
        userSettingsSentinel,
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// YamlSource Free Functions
// ============================================================================

describe("YamlSource free functions", () => {
  test("getYamlSourcePath returns correct path for Main", () => {
    const path = getYamlSourcePath("Main", "");
    expect(path).toContain("CLASSIC Main.yaml");
  });

  test("getYamlSourcePath returns correct path for Game with game name", () => {
    const path = getYamlSourcePath("Game", "Fallout4");
    expect(path).toContain("CLASSIC Fallout4.yaml");
  });

  test("getYamlSourcePath shares the Fallout4 database with Fallout4VR", () => {
    const path = getYamlSourcePath("Game", "Fallout4VR");
    expect(path).toContain("CLASSIC Fallout4.yaml");
    expect(path).not.toContain("CLASSIC Fallout4VR.yaml");
  });


  test("getYamlSourcePath returns correct path for Ignore", () => {
    const path = getYamlSourcePath("Ignore", "");
    expect(path).toContain("CLASSIC Ignore.yaml");
  });

  test("getYamlSourcePath returns correct path for GameLocal", () => {
    const path = getYamlSourcePath("GameLocal", "Skyrim");
    expect(path).toContain("CLASSIC Skyrim Local.yaml");
  });

  test("getYamlSourcePath returns CLASSIC cache path", () => {
    const path = getYamlSourcePath("Cache", "");
    expect(path).toContain("CLASSIC");
    expect(path).toContain("cache.yaml");
    expect(path).not.toContain("CLASSIC-Fallout4");
  });

  test("getYamlSourceDisplayName returns correct name for Main", () => {
    const name = getYamlSourceDisplayName("Main");
    expect(name).toBe("Main Database");
  });


  test("getYamlSourceDisplayNameWithGame returns game-specific name", () => {
    const name = getYamlSourceDisplayNameWithGame("Game", "Fallout4");
    expect(name).toBe("Fallout4 Database");
  });

  test("getYamlSourceDisplayNameWithGame for GameLocal", () => {
    const name = getYamlSourceDisplayNameWithGame("GameLocal", "Skyrim");
    expect(name).toBe("Skyrim Local Config");
  });
});

// ============================================================================
// clearYamlCache
// ============================================================================

describe("clearYamlCache", () => {
  test("clearYamlCache does not throw", () => {
    expect(() => clearYamlCache()).not.toThrow();
  });

  test("clearYamlCache can be called multiple times", () => {
    clearYamlCache();
    clearYamlCache();
    clearYamlCache();
    // No error means success
  });
});

// ============================================================================
// Phase 4 Plan 3: Promoted config cache constants (real-shape assertions)
// ============================================================================

import {
  DEFAULT_CACHE_CLEANUP_INTERVAL,
  DEFAULT_CACHE_CLEANUP_THRESHOLD,
  DEFAULT_QUERY_CACHE_CAPACITY,
  getDefaultCacheCleanupInterval,
  getDefaultCacheCleanupThreshold,
  getDefaultQueryCacheCapacity,
  getHashCacheStats,
  resetHashCacheStats,
  clearHashCache,
  detectConfigDuplicates,
  gameSetupNeedsPathDetection,
  JsConfigDuplicateDetector,
} from "../index.js";

describe("config: cache constants (Plan 3 promotion)", () => {
  test("DEFAULT_CACHE_CLEANUP_INTERVAL is a positive number", () => {
    expect(typeof DEFAULT_CACHE_CLEANUP_INTERVAL).toBe("number");
    expect(DEFAULT_CACHE_CLEANUP_INTERVAL).toBeGreaterThan(0);
  });

  test("getDefaultCacheCleanupInterval returns the const value", () => {
    expect(getDefaultCacheCleanupInterval()).toBe(
      DEFAULT_CACHE_CLEANUP_INTERVAL,
    );
  });

  test("DEFAULT_CACHE_CLEANUP_THRESHOLD is a positive number", () => {
    expect(typeof DEFAULT_CACHE_CLEANUP_THRESHOLD).toBe("number");
    expect(DEFAULT_CACHE_CLEANUP_THRESHOLD).toBeGreaterThan(0);
  });

  test("getDefaultCacheCleanupThreshold returns the const value", () => {
    expect(getDefaultCacheCleanupThreshold()).toBe(
      DEFAULT_CACHE_CLEANUP_THRESHOLD,
    );
  });

  test("DEFAULT_QUERY_CACHE_CAPACITY is a positive integer", () => {
    expect(typeof DEFAULT_QUERY_CACHE_CAPACITY).toBe("number");
    expect(Number.isInteger(DEFAULT_QUERY_CACHE_CAPACITY)).toBe(true);
    expect(DEFAULT_QUERY_CACHE_CAPACITY).toBeGreaterThan(0);
  });

  test("getDefaultQueryCacheCapacity returns the const value", () => {
    expect(getDefaultQueryCacheCapacity()).toBe(DEFAULT_QUERY_CACHE_CAPACITY);
  });
});

describe("config: hash cache stats (Plan 3 promotion)", () => {
  test("getHashCacheStats returns a stats shape with numeric fields", () => {
    const stats = getHashCacheStats();
    expect(stats).toBeDefined();
    expect(typeof stats.hits).toBe("number");
    expect(typeof stats.misses).toBe("number");
    expect(typeof stats.hit_rate).toBe("number");
    expect(typeof stats.size).toBe("number");
    expect(typeof stats.capacity).toBe("number");
  });

  test("resetHashCacheStats clears counters", () => {
    resetHashCacheStats();
    const stats = getHashCacheStats();
    expect(stats.hits).toBe(0);
    expect(stats.misses).toBe(0);
  });

  test("clearHashCache is callable without throwing", () => {
    expect(() => clearHashCache()).not.toThrow();
  });
});

describe("config: duplicate detector class (Plan 3 promotion)", () => {
  test("JsConfigDuplicateDetector can be constructed", () => {
    const det = new JsConfigDuplicateDetector();
    expect(det).toBeDefined();
    expect(typeof det).toBe("object");
  });

  test("JsConfigDuplicateDetector.withWhitelist creates instance", () => {
    const det = JsConfigDuplicateDetector.withWhitelist(["test.dll"]);
    expect(det).toBeDefined();
    expect(typeof det).toBe("object");
  });

  test("detectConfigDuplicates returns an array for a temp dir", () => {
    const dir = mkdtempSync(join(tmpdir(), "classic-node-dup-"));
    try {
      const result = detectConfigDuplicates(dir);
      expect(Array.isArray(result)).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("config: game setup path detection helpers (Plan 3 promotion)", () => {
  test("gameSetupNeedsPathDetection returns object with boolean fields", () => {
    const result = gameSetupNeedsPathDetection();
    expect(typeof result.needsGamePath).toBe("boolean");
    expect(typeof result.needsDocsPath).toBe("boolean");
  });
});
