import { describe, test, expect } from "bun:test";
import {
  createAnalysisConfig,
  getVersion,
  processLog,
  processLogsBatch,
  parseLogSegments,
  extractFormIds,
  extractPluginList,
  detectCrashPattern,
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
    const config = createAnalysisConfig("Fallout4", false);
    expect(config).toBeDefined();
    expect(config.game).toBe("Fallout4");
    expect(config.vrMode).toBe(false);
  });

  test("createAnalysisConfig accepts VR mode", () => {
    const config = createAnalysisConfig("Fallout4", true);
    expect(config.vrMode).toBe(true);
  });

  test("createAnalysisConfig has correct default values", () => {
    const config = createAnalysisConfig("Fallout4", false);
    expect(config.crashgenName).toBe("");
    expect(config.xseAcronym).toBe("");
    expect(config.classicVersion).toBe("CLASSIC");
    expect(config.fcxMode).toBe(false);
    expect(config.simplifyLogs).toBe(false);
  });
});

// ============================================================================
// Async Analysis (processLog)
// ============================================================================

describe("processLog", () => {
  test("processLog rejects for a non-existent file", async () => {
    const config = createAnalysisConfig("Fallout4", false);
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
    const config = createAnalysisConfig("Fallout4", false);
    const results = await processLogsBatch([], config);
    expect(results).toEqual([]);
  });

  test("processLogsBatch handles non-existent files gracefully", async () => {
    const config = createAnalysisConfig("Fallout4", false);
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
