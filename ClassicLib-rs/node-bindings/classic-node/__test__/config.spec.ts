import { describe, test, expect, beforeEach } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import {
  // YamlData class
  YamlData,
  // ClassicConfigJs class
  ClassicConfigJs,
  // Free functions
  createYamlDataFromContent,
  createDefaultConfig,
  clearYamlCache,
  getYamlSourcePath,
  getYamlSourceDisplayName,
  getYamlSourceDisplayNameWithGame,
} from "../index.js";

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
  ErrorPattern1: "Error description 1"
  ErrorPattern2: "Error description 2"
Crashlog_Stack_Check:
  StackPattern1: ["Stack pattern 1", "Stack pattern 2"]
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
  FreqMod: "Frequently used mod"
Mods_SOLU:
  SoluMod: "Solution mod"
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

  test("suspectsErrorList returns correct map", () => {
    const errors = data.suspectsErrorList;
    expect(errors["ErrorPattern1"]).toBe("Error description 1");
    expect(errors["ErrorPattern2"]).toBe("Error description 2");
    expect(Object.keys(errors).length).toBe(2);
  });

  test("suspectsStackList returns correct map with arrays", () => {
    const stacks = data.suspectsStackList;
    expect(stacks["StackPattern1"]).toEqual([
      "Stack pattern 1",
      "Stack pattern 2",
    ]);
    expect(Object.keys(stacks).length).toBe(1);
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

  test("gameModsFreq returns correct map", () => {
    expect(data.gameModsFreq["FreqMod"]).toBe("Frequently used mod");
  });

  test("legacy OPC2 YAML is not exposed through YamlData", () => {
    expect("gameModsOpc2" in data).toBe(false);
  });

  test("gameModsSolu returns correct map", () => {
    expect(data.gameModsSolu["SoluMod"]).toBe("Solution mod");
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
    expect(Object.keys(data.suspectsErrorList).length).toBe(0);
    expect(data.gameModsCoreCount).toBe(0);
  });
});

// ============================================================================
// ClassicConfigJs: Construction and Defaults
// ============================================================================

describe("ClassicConfigJs construction", () => {
  test("default constructor creates config with correct defaults", () => {
    const config = new ClassicConfigJs();
    expect(config.fcxMode).toBe(false);
    expect(config.showFormidValues).toBe(false);
    expect(config.statLogging).toBe(false);
    expect(config.moveUnsolvedLogs).toBe(false);
    expect(config.simplifyLogs).toBe(false);
    expect(config.updateCheck).toBe(true);
    expect(config.gameVersion).toBe("auto");
    expect(config.updateSource).toBe("github");
    expect(config.autoSwitchToResults).toBe(true);
    expect(config.autoRefreshIntervalMs).toBe(5000);
  });

  test("createDefaultConfig free function creates config with defaults", () => {
    const config = createDefaultConfig();
    expect(config.fcxMode).toBe(false);
    expect(config.updateCheck).toBe(true);
    expect(config.gameVersion).toBe("auto");
  });
});

// ============================================================================
// ClassicConfigJs: Feature Flag Setters
// ============================================================================

describe("ClassicConfigJs feature flags", () => {
  test("fcxMode getter/setter", () => {
    const config = new ClassicConfigJs();
    expect(config.fcxMode).toBe(false);
    config.fcxMode = true;
    expect(config.fcxMode).toBe(true);
  });

  test("showFormidValues getter/setter", () => {
    const config = new ClassicConfigJs();
    config.showFormidValues = true;
    expect(config.showFormidValues).toBe(true);
  });

  test("statLogging getter/setter", () => {
    const config = new ClassicConfigJs();
    config.statLogging = true;
    expect(config.statLogging).toBe(true);
  });

  test("moveUnsolvedLogs getter/setter", () => {
    const config = new ClassicConfigJs();
    config.moveUnsolvedLogs = true;
    expect(config.moveUnsolvedLogs).toBe(true);
  });

  test("simplifyLogs getter/setter", () => {
    const config = new ClassicConfigJs();
    config.simplifyLogs = true;
    expect(config.simplifyLogs).toBe(true);
  });

  test("updateCheck getter/setter", () => {
    const config = new ClassicConfigJs();
    expect(config.updateCheck).toBe(true);
    config.updateCheck = false;
    expect(config.updateCheck).toBe(false);
  });

  test("gameVersion getter/setter", () => {
    const config = new ClassicConfigJs();
    config.gameVersion = "NextGen";
    expect(config.gameVersion).toBe("NextGen");
  });

  test("updateSource getter/setter", () => {
    const config = new ClassicConfigJs();
    config.updateSource = "both";
    expect(config.updateSource).toBe("both");
  });

  test("autoSwitchToResults getter/setter", () => {
    const config = new ClassicConfigJs();
    config.autoSwitchToResults = false;
    expect(config.autoSwitchToResults).toBe(false);
  });

  test("autoRefreshIntervalMs getter/setter", () => {
    const config = new ClassicConfigJs();
    config.autoRefreshIntervalMs = 1000;
    expect(config.autoRefreshIntervalMs).toBe(1000);
  });
});

// ============================================================================
// ClassicConfigJs: Path Configuration
// ============================================================================

describe("ClassicConfigJs path configuration", () => {
  test("paths getter returns default path config", () => {
    const config = new ClassicConfigJs();
    const paths = config.paths;
    expect(paths).toBeDefined();
    expect(paths.gameRoot).toBe("");
    expect(paths.iniFolder).toBeUndefined();
    expect(paths.scanCustom).toBeUndefined();
    expect(paths.modsFolder).toBeUndefined();
    expect(paths.docsRoot).toBeUndefined();
  });

  test("paths setter updates path config", () => {
    const config = new ClassicConfigJs();
    config.paths = {
      gameRoot: "C:\\Games\\Fallout4",
      iniFolder: "C:\\Users\\Test\\Documents\\Fallout4",
      scanCustom: undefined,
      modsFolder: "C:\\Games\\Fallout4\\Mods",
      docsRoot: undefined,
    };
    const paths = config.paths;
    expect(paths.gameRoot).toBe("C:\\Games\\Fallout4");
    expect(paths.iniFolder).toBe("C:\\Users\\Test\\Documents\\Fallout4");
    expect(paths.scanCustom).toBeUndefined();
    expect(paths.modsFolder).toBe("C:\\Games\\Fallout4\\Mods");
    expect(paths.docsRoot).toBeUndefined();
  });
});

// ============================================================================
// ClassicConfigJs: FormID Databases
// ============================================================================

describe("ClassicConfigJs FormID databases", () => {
  test("formidDatabases is empty by default", () => {
    const config = new ClassicConfigJs();
    const dbs = config.formidDatabases;
    expect(Object.keys(dbs).length).toBe(0);
  });

  test("formidDatabases getter/setter round-trip", () => {
    const config = new ClassicConfigJs();
    config.formidDatabases = {
      Fallout4: ["databases/FOLON FormIDs.db", "D:/Custom/My FormIDs.db"],
      Skyrim: [],
    };
    const dbs = config.formidDatabases;
    expect(dbs["Fallout4"]).toEqual([
      "databases/FOLON FormIDs.db",
      "D:/Custom/My FormIDs.db",
    ]);
    expect(dbs["Skyrim"]).toEqual([]);
  });
});

// ============================================================================
// ClassicConfigJs: Config Path
// ============================================================================

describe("ClassicConfigJs config path", () => {
  test("getConfigPath returns a CLASSIC-based default path", () => {
    const config = new ClassicConfigJs();
    const path = config.getConfigPath();
    expect(typeof path).toBe("string");
    expect(path).toContain("CLASSIC Settings.yaml");
    expect(path).not.toContain("CLASSIC-Fallout4");
  });

  test("loadOrDefault reads from the resolved default settings path", () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-config-"));
    const originalAppData = process.env.APPDATA;
    const originalXdgConfigHome = process.env.XDG_CONFIG_HOME;
    const originalHome = process.env.HOME;

    try {
      process.env.APPDATA = root;
      delete process.env.XDG_CONFIG_HOME;
      delete process.env.HOME;

      const settingsPath = new ClassicConfigJs().getConfigPath();
      mkdirSync(dirname(settingsPath), { recursive: true });
      writeFileSync(settingsPath, "fcx_mode: true\n", "utf8");

      const config = ClassicConfigJs.loadOrDefault();
      expect(config.fcxMode).toBe(true);
      expect(config.getConfigPath()).toBe(settingsPath);
      expect(config.getConfigPath()).not.toContain("CLASSIC-Fallout4");
    } finally {
      if (originalAppData === undefined) {
        delete process.env.APPDATA;
      } else {
        process.env.APPDATA = originalAppData;
      }
      if (originalXdgConfigHome === undefined) {
        delete process.env.XDG_CONFIG_HOME;
      } else {
        process.env.XDG_CONFIG_HOME = originalXdgConfigHome;
      }
      if (originalHome === undefined) {
        delete process.env.HOME;
      } else {
        process.env.HOME = originalHome;
      }
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("loadFromYaml classifies parse failures as InvalidArg", () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-config-"));

    try {
      const settingsPath = join(root, "invalid-classic-settings.yaml");
      writeFileSync(settingsPath, "{ invalid: yaml: content: }}}", "utf8");

      try {
        ClassicConfigJs.loadFromYaml(settingsPath);
        throw new Error("expected parse failure");
      } catch (err) {
        const error = err as Error & { code?: string };
        expect(error.code).toBe("InvalidArg");
        expect(error.message).toContain("Failed to load merged config YAML");
      }
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("loadFromYaml classifies missing-file failures as GenericFailure", () => {
    const missingPath = join(
      tmpdir(),
      "classic-node-missing",
      "missing-classic-settings.yaml",
    );

    try {
      ClassicConfigJs.loadFromYaml(missingPath);
      throw new Error("expected I/O failure");
    } catch (err) {
      const error = err as Error & { code?: string };
      expect(error.code).toBe("GenericFailure");
      expect(error.message).toContain("Failed to load merged config YAML");
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

  test("getYamlSourcePath returns correct path for Settings", () => {
    const path = getYamlSourcePath("Settings", "");
    expect(path).toContain("CLASSIC Settings.yaml");
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

  test("getYamlSourceDisplayName returns correct name for Settings", () => {
    const name = getYamlSourceDisplayName("Settings");
    expect(name).toBe("Settings");
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
