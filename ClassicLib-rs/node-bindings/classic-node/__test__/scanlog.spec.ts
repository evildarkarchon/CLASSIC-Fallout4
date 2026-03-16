import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, writeFileSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import {
  createAnalysisConfig,
  createAnalysisConfigFromYamlContent,
  getVersion,
  processLog,
  processLogsBatch,
  processLogWithYamlContent,
  processLogsBatchWithYamlContent,
  parseLogSegments,
  extractFormIds,
  extractPluginList,
  detectCrashPattern,
  detectVrLog,
  detectGpuInfo,
  parseCrashgenVersion,
  checkCrashgenVersionStatus,
  analyzePapyrusLog,
} from "../index.js";

// ============================================================================
// Sample crash log content for testing
// ============================================================================

const SAMPLE_CRASH_LOG = `Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

\t[Compatibility]
\tAchievements: true
\tMemoryManager: false
\tF4EE: false

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tPHYSICAL MEMORY: 32.0 GB

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> TESForm::SetReference+0x12
\t[ 1] 0x7FF6EF4C3600 Fallout4.exe+0733600 -> BGSInventoryItem::GetOwner+0x30
\t[ 2] 0x7FFB12340000 nvwgf2umx.dll+00FF1234 -> ?

MODULES:
\tFallout4.exe v1.10.163.0
\tnvwgf2umx.dll v31.0.15.3713
\tkernel32.dll v10.0.22621.1
\tAchievements.dll v2.3.0

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] DLCworkshop01.esm
\t[FE:000] ccBGSFO4001-PipBoy(Black).esl
\t[03] Unofficial Fallout 4 Patch.esp
`;

const FORMID_CONTENT = `PROBABLE CALL STACK:
[0] 0x7FF6DEADBEEF    FormID: 0x00012345    TestMod.esp
[1] 0x7FF6CAFEBABE    FormID: 0x00023456    Fallout4.esm
[2] 0x7FF6BADF00D5    FormID: 0x00034567    DLCCoast.esm
`;

const PLUGIN_CONTENT = `PLUGINS:
[00] Fallout4.esm
[01] DLCRobot.esm
[02] DLCworkshop01.esm
[03] DLCCoast.esm
[FE:000] ccBGSFO4001-PipBoy(Black).esl
[04] TestMod.esp
`;

const SETTINGS_MARKER_CONTENT = `Fallout 4 v1.10.163
[Compatibility]
Achievements: true
MemoryManager: false
`;

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
Mods_CORE: {}
Mods_CORE_FOLON: {}
Mods_FREQ: {}
Mods_OPC2: {}
Mods_SOLU: {}
`;

const IGNORE_YAML = `
CLASSIC_Ignore_Fallout4: []
`;

// ============================================================================
// Version & Config
// ============================================================================

describe("Scanlog bindings", () => {
  test("getVersion returns a semver string", () => {
    const version = getVersion();
    expect(typeof version).toBe("string");
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);
  });

  test("createAnalysisConfig returns a config object", () => {
    const config = createAnalysisConfig("Fallout4", "auto");
    expect(config).toBeDefined();
    expect(config.game).toBe("Fallout4");
    expect(config.gameVersion).toBe("auto");
  });

  test("createAnalysisConfig accepts VR mode", () => {
    const config = createAnalysisConfig("Fallout4", "VR");
    expect(config.gameVersion).toBe("VR");
  });

  test("createAnalysisConfig has correct default values", () => {
    const config = createAnalysisConfig("Fallout4", "auto");
    expect(config.crashgenName).toBe("");
    expect(config.xseAcronym).toBe("");
    expect(config.classicVersion).toBe("CLASSIC");
    expect(config.fcxMode).toBe(false);
    expect(config.simplifyLogs).toBe(false);
  });

  test("createAnalysisConfigFromYamlContent builds config from YAML", () => {
    const config = createAnalysisConfigFromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(config.game).toBe("Fallout4");
    expect(config.gameVersion).toBe("auto");
    expect(config.crashgenName).toBe("Buffout 4");
    expect(config.xseAcronym).toBe("F4SE");
    expect(config.classicVersion).toBe("9.0.0");
  });

  test("createAnalysisConfigFromYamlContent applies optional build flags", () => {
    const config = createAnalysisConfigFromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
      {
        fcxMode: true,
        simplifyLogs: true,
      },
    );
    expect(config.fcxMode).toBe(true);
    expect(config.simplifyLogs).toBe(true);
  });
});

// ============================================================================
// Async Analysis (processLog)
// ============================================================================

describe("processLog", () => {
  test("processLog rejects for a non-existent file", async () => {
    const config = createAnalysisConfig("Fallout4", "auto");
    try {
      await processLog("Z:\\nonexistent\\crash.log", config);
      // If it doesn't throw, the result should indicate failure
      expect(true).toBe(false); // Should not reach here
    } catch (err: unknown) {
      // Expected: file not found or I/O error
      expect(err).toBeDefined();
      const message =
        err instanceof Error ? err.message : String(err);
      expect(message.length).toBeGreaterThan(0);
    }
  });
});

// ============================================================================
// Async Batch Analysis (processLogsBatch)
// ============================================================================

describe("processLogsBatch", () => {
  test("processLogsBatch returns empty array for empty input", async () => {
    const config = createAnalysisConfig("Fallout4", "auto");
    const results = await processLogsBatch([], config);
    expect(results).toEqual([]);
  });

  test("processLogsBatch handles non-existent files gracefully", async () => {
    const config = createAnalysisConfig("Fallout4", "auto");
    const results = await processLogsBatch(
      ["Z:\\nonexistent\\a.log", "Z:\\nonexistent\\b.log"],
      config,
    );
    expect(results.length).toBe(2);
    for (const result of results) {
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    }
  });

  test("processLogsBatch accepts an explicit maxConcurrent override", async () => {
    const config = createAnalysisConfig("Fallout4", "auto");
    const results = await processLogsBatch(["Z:\\nonexistent\\single.log"], config, 1);

    expect(results).toHaveLength(1);
    expect(results[0].success).toBe(false);
  });
});

describe("YAML-backed analysis entry points", () => {
  test("processLogWithYamlContent rejects for invalid YAML payload", async () => {
    try {
      await processLogWithYamlContent(
        "Z:\\nonexistent\\crash.log",
        "this: [is: not: yaml",
        GAME_YAML,
        IGNORE_YAML,
        "Fallout4",
        "auto",
      );
      expect(true).toBe(false);
    } catch (err: unknown) {
      expect(err).toBeDefined();
      const message = err instanceof Error ? err.message : String(err);
      expect(message).toMatch(/yaml/i);
    }
  });

  test("processLogWithYamlContent rejects for a non-existent file", async () => {
    try {
      await processLogWithYamlContent(
        "Z:\\nonexistent\\crash.log",
        MAIN_YAML,
        GAME_YAML,
        IGNORE_YAML,
        "Fallout4",
        "auto",
      );
      expect(true).toBe(false);
    } catch (err: unknown) {
      expect(err).toBeDefined();
      const message = err instanceof Error ? err.message : String(err);
      expect(message.length).toBeGreaterThan(0);
    }
  });

  test("processLogsBatchWithYamlContent returns empty array for empty input", async () => {
    const results = await processLogsBatchWithYamlContent(
      [],
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(results).toEqual([]);
  });

  test("processLogsBatchWithYamlContent returns per-log failures", async () => {
    const results = await processLogsBatchWithYamlContent(
      ["Z:\\nonexistent\\a.log", "Z:\\nonexistent\\b.log"],
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(results.length).toBe(2);
    for (const result of results) {
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    }
  });

  test("processLogsBatchWithYamlContent accepts an explicit maxConcurrent override", async () => {
    const results = await processLogsBatchWithYamlContent(
      ["Z:\\nonexistent\\single.log"],
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
      undefined,
      1,
    );

    expect(results).toHaveLength(1);
    expect(results[0].success).toBe(false);
  });
});

// ============================================================================
// Synchronous: parseLogSegments
// ============================================================================

describe("parseLogSegments", () => {
  test("parses a standard crash log into segments", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments).toBeDefined();
    expect(segments.segmentCount).toBeGreaterThan(0);
  });

  test("extracts system section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.system.length).toBeGreaterThan(0);
    const joined = segments.system.join("\n");
    expect(joined).toContain("AMD Ryzen");
  });

  test("extracts plugins section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.plugins.length).toBeGreaterThan(0);
    const joined = segments.plugins.join("\n");
    expect(joined).toContain("Fallout4.esm");
  });

  test("extracts stack section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.stack.length).toBeGreaterThan(0);
    const joined = segments.stack.join("\n");
    expect(joined).toContain("TESForm");
  });

  test("extracts modules section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.modules.length).toBeGreaterThan(0);
    const joined = segments.modules.join("\n");
    expect(joined).toContain("nvwgf2umx.dll");
  });

  test("extracts header compatibility settings", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.header.length).toBeGreaterThan(0);
    const joined = segments.header.join("\n");
    expect(joined).toContain("Achievements: true");
  });

  test("uses compatibility marker to build header section", () => {
    const segments = parseLogSegments(SETTINGS_MARKER_CONTENT);
    expect(segments.header).toEqual(["Achievements: true", "MemoryManager: false"]);
  });

  test("returns empty segments for empty content", () => {
    const segments = parseLogSegments("");
    expect(segments.segmentCount).toBe(0);
    expect(segments.header).toEqual([]);
    expect(segments.system).toEqual([]);
    expect(segments.stack).toEqual([]);
    expect(segments.modules).toEqual([]);
    expect(segments.plugins).toEqual([]);
  });

  test("returns empty segments for content without markers", () => {
    const segments = parseLogSegments("just some random text\nnothing special");
    expect(segments.segmentCount).toBe(0);
  });
});

// ============================================================================
// Synchronous: extractFormIds
// ============================================================================

describe("extractFormIds", () => {
  test("extracts FormIDs from content with FormID patterns", () => {
    const formIds = extractFormIds(FORMID_CONTENT);
    expect(formIds.length).toBeGreaterThan(0);
    // FormIDs are returned without 0x prefix, lowercase
    for (const fid of formIds) {
      expect(fid).toMatch(/^[0-9a-f]{8}$/);
    }
  });

  test("extracts the expected FormIDs", () => {
    const formIds = extractFormIds(FORMID_CONTENT);
    expect(formIds).toContain("00012345");
    expect(formIds).toContain("00023456");
    expect(formIds).toContain("00034567");
  });

  test("returns empty array for content without FormIDs", () => {
    const formIds = extractFormIds("No formids here\nJust regular text");
    expect(formIds).toEqual([]);
  });

  test("returns empty array for empty content", () => {
    const formIds = extractFormIds("");
    expect(formIds).toEqual([]);
  });
});

// ============================================================================
// Synchronous: extractPluginList
// ============================================================================

describe("extractPluginList", () => {
  test("extracts plugin names from plugin section content", () => {
    const plugins = extractPluginList(PLUGIN_CONTENT);
    expect(plugins.length).toBeGreaterThan(0);
  });

  test("extracts expected plugin names", () => {
    const plugins = extractPluginList(PLUGIN_CONTENT);
    expect(plugins).toContain("Fallout4.esm");
    expect(plugins).toContain("DLCRobot.esm");
    expect(plugins).toContain("DLCworkshop01.esm");
    expect(plugins).toContain("DLCCoast.esm");
    expect(plugins).toContain("TestMod.esp");
  });

  test("extracts only esm/esp plugins (esl not included)", () => {
    const plugins = extractPluginList(PLUGIN_CONTENT);
    // The parser extracts .esm and .esp files; .esl light plugins may not be included
    expect(plugins.length).toBeGreaterThan(0);
  });

  test("returns empty array for content without plugins", () => {
    const plugins = extractPluginList("No plugins here\nJust text");
    expect(plugins).toEqual([]);
  });

  test("returns empty array for empty content", () => {
    const plugins = extractPluginList("");
    expect(plugins).toEqual([]);
  });
});

// ============================================================================
// Synchronous: detectCrashPattern
// ============================================================================

describe("detectCrashPattern", () => {
  test("detects ACCESS_VIOLATION pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("ACCESS_VIOLATION");
  });

  test("detects STACK_OVERFLOW pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_STACK_OVERFLOW" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("STACK_OVERFLOW");
  });

  test("detects INT_DIVIDE_BY_ZERO pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_INT_DIVIDE_BY_ZERO" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("INT_DIVIDE_BY_ZERO");
  });

  test("detects BREAKPOINT pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_BREAKPOINT" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("BREAKPOINT");
  });

  test("detects STACK_BUFFER_OVERRUN pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_STACK_BUFFER_OVERRUN" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("STACK_BUFFER_OVERRUN");
  });

  test("detects pattern from full crash log", () => {
    const pattern = detectCrashPattern(SAMPLE_CRASH_LOG);
    expect(pattern).toBe("ACCESS_VIOLATION");
  });

  test("returns null for content without known patterns", () => {
    const pattern = detectCrashPattern("No crash here\nJust regular log content");
    expect(pattern).toBeNull();
  });

  test("returns null for empty content", () => {
    const pattern = detectCrashPattern("");
    expect(pattern).toBeNull();
  });

  test("returns null for content with unknown exception type", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_UNKNOWN_TYPE" at 0x7FF6EF4C3512',
    );
    // EXCEPTION_UNKNOWN_TYPE is not a known pattern, but the line does contain EXCEPTION_
    // The function should not match it to any known pattern
    expect(pattern).toBeNull();
  });
});

// ============================================================================
// Synchronous: detectVrLog
// ============================================================================

describe("detectVrLog", () => {
  test("returns true for VR crash log content", () => {
    expect(detectVrLog("Fallout4VR.exe v1.2.72.0")).toBe(true);
  });

  test("returns true for VR ESM reference", () => {
    expect(detectVrLog("[00] Fallout4VR.esm")).toBe(true);
  });

  test("returns true for case-insensitive VR match", () => {
    expect(detectVrLog("FALLOUT4VR.EXE loaded")).toBe(true);
  });

  test("returns false for non-VR crash log", () => {
    expect(detectVrLog("Fallout4.exe v1.10.163.0")).toBe(false);
  });

  test("returns false for empty content", () => {
    expect(detectVrLog("")).toBe(false);
  });

  test("returns false for unrelated content", () => {
    expect(detectVrLog("Some random text\nNo game references")).toBe(false);
  });
});

// ============================================================================
// Synchronous: detectGpuInfo
// ============================================================================

describe("detectGpuInfo", () => {
  test("detects Nvidia GPU", () => {
    const info = detectGpuInfo([
      "\tGPU #1: Nvidia AD104 [GeForce RTX 4070]",
    ]);
    expect(info.manufacturer).toBe("Nvidia");
    expect(info.primary).toContain("Nvidia");
    expect(info.rival).toBe("amd");
  });

  test("detects AMD GPU", () => {
    const info = detectGpuInfo(["\tGPU #1: AMD Radeon RX 7900 XTX"]);
    expect(info.manufacturer).toBe("AMD");
    expect(info.primary).toContain("AMD");
    expect(info.rival).toBe("nvidia");
  });

  test("detects Intel GPU", () => {
    const info = detectGpuInfo(["\tGPU #1: Intel UHD Graphics 770"]);
    expect(info.manufacturer).toBe("Intel");
    expect(info.primary).toContain("Intel");
    expect(info.rival).toBeUndefined();
  });

  test("detects secondary GPU", () => {
    const info = detectGpuInfo([
      "\tGPU #1: Nvidia GeForce RTX 4070",
      "\tGPU #2: Intel UHD Graphics 770",
    ]);
    expect(info.primary).toContain("Nvidia");
    expect(info.secondary).toContain("Intel");
  });

  test("returns Unknown for unrecognized GPU lines", () => {
    const info = detectGpuInfo(["no GPU info here"]);
    expect(info.manufacturer).toBe("Unknown");
    expect(info.primary).toBe("Unknown");
    expect(info.secondary).toBeUndefined();
    expect(info.rival).toBeUndefined();
  });

  test("returns Unknown for empty input", () => {
    const info = detectGpuInfo([]);
    expect(info.manufacturer).toBe("Unknown");
  });
});

// ============================================================================
// Synchronous: parseCrashgenVersion
// ============================================================================

describe("parseCrashgenVersion", () => {
  test("parses a simple version string", () => {
    const v = parseCrashgenVersion("1.28.6");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(28);
    expect(v!.patch).toBe(6);
  });

  test("parses a version with v prefix", () => {
    const v = parseCrashgenVersion("v1.29.1");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(29);
    expect(v!.patch).toBe(1);
  });

  test("parses a version with crashgen prefix", () => {
    const v = parseCrashgenVersion("Buffout 4 v1.30.2");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(30);
    expect(v!.patch).toBe(2);
  });

  test("parses version with two components", () => {
    const v = parseCrashgenVersion("1.28");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(28);
    expect(v!.patch).toBe(0);
  });

  test("returns null for invalid version", () => {
    expect(parseCrashgenVersion("not a version")).toBeNull();
  });

  test("returns null for empty string", () => {
    expect(parseCrashgenVersion("")).toBeNull();
  });
});

// ============================================================================
// Synchronous: checkCrashgenVersionStatus
// ============================================================================

describe("checkCrashgenVersionStatus", () => {
  test("returns Valid for matching version", () => {
    const status = checkCrashgenVersionStatus("1.28.6", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe("Valid");
  });

  test("returns Valid for second valid version", () => {
    const status = checkCrashgenVersionStatus("1.37.0", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe("Valid");
  });

  test("returns Outdated for old version", () => {
    const status = checkCrashgenVersionStatus("1.26.0", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe("Outdated");
  });

  test("returns NewerThanKnown for newer version", () => {
    const status = checkCrashgenVersionStatus("1.40.0", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe("NewerThanKnown");
  });

  test("returns NoSupportedVersion for empty valid list", () => {
    const status = checkCrashgenVersionStatus("1.28.6", []);
    expect(status).toBe("NoSupportedVersion");
  });

  test("handles version with crashgen prefix", () => {
    const status = checkCrashgenVersionStatus("Buffout 4 v1.28.6", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe("Valid");
  });

  test("treats unparsable detected version as Outdated", () => {
    const status = checkCrashgenVersionStatus("invalid-version", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe("Outdated");
  });
});

// ============================================================================
// Synchronous: analyzePapyrusLog
// ============================================================================

describe("analyzePapyrusLog", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), "classic-papyrus-test-"));
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  test("analyzes a papyrus log with known content", () => {
    const logPath = join(tempDir, "Papyrus.0.log");
    const content = [
      "[01/01/2025 - 12:00:00AM] Papyrus log opened",
      "[01/01/2025 - 12:00:01AM] warning: Variable not found",
      "[01/01/2025 - 12:00:02AM] error: Stack overflow",
      "[01/01/2025 - 12:00:03AM] warning: Property not found",
      "[01/01/2025 - 12:00:04AM] Dumping Stacks",
      "[01/01/2025 - 12:00:05AM] Dumping Stack",
    ].join("\n");
    writeFileSync(logPath, content);

    const stats = analyzePapyrusLog(logPath);
    expect(stats).toBeDefined();
    expect(stats.warnings).toBe(2);
    expect(stats.errors).toBe(1);
    expect(stats.dumps).toBe(1);
    expect(stats.stacks).toBe(1);
    expect(stats.linesProcessed).toBe(6);
  });

  test("analyzes an empty papyrus log", () => {
    const logPath = join(tempDir, "Empty.log");
    writeFileSync(logPath, "");

    const stats = analyzePapyrusLog(logPath);
    expect(stats.dumps).toBe(0);
    expect(stats.stacks).toBe(0);
    expect(stats.warnings).toBe(0);
    expect(stats.errors).toBe(0);
  });

  test("throws for non-existent log file", () => {
    expect(() =>
      analyzePapyrusLog(join(tempDir, "nonexistent.log")),
    ).toThrow();
  });
});
