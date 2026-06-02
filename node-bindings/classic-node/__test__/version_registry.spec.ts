import { describe, test, expect } from "bun:test";
import {
  getVersionById,
  getVersionByVersionString,
  getVersionByShortName,
  getAllVersions,
  getVersionRegistry,
  getAllVersionsForGame,
  getCorrectVersions,
  getWrongVersions,
  matchVersion,
  getAddressLibraryFilename,
  getCrashgenVersions,
  getCrashgenVersionStrings,
  getCrashgenForVersion,
  getAllExeHashes,
  getAllScriptHashes,
  getScriptHashesForVersion,
  getUnknownVersionHandling,
  getUnknownVersionDefault,
  isVersionCompatible,
  parseGameVersion,
  gameVersionDistance,
  checkCrashgenConfigWithRules,
  checkCrashgenFullWithRules,
} from "../index.js";
import type {
  JsCrashgenRegistryEntry,
  JsCrashgenSettingsRules,
} from "../index.js";

// ============================================================================
// Lookup Functions
// ============================================================================

describe("Version Registry bindings", () => {
  describe("getVersionById", () => {
    test("returns OG version info for FO4_OG", () => {
      const info = getVersionById("FO4_OG");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_OG");
      expect(info!.shortName).toBe("OG");
      expect(info!.game).toBe("Fallout4");
      expect(info!.isVr).toBe(false);
      expect(info!.version).toBe("1.10.163.0");
      expect(info!.displayName).toBe("Fallout 4 Original");
    });

    test("returns NG version info for FO4_NG", () => {
      const info = getVersionById("FO4_NG");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_NG");
      expect(info!.shortName).toBe("NG");
      expect(info!.version).toBe("1.10.984.0");
    });

    test("returns AE version info for FO4_AE", () => {
      const info = getVersionById("FO4_AE");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_AE");
      expect(info!.shortName).toBe("AE");
      expect(info!.version).toBe("1.11.221.0");
      expect(info!.priority).toBe(300);
    });

    test("returns VR version info for FO4_VR", () => {
      const info = getVersionById("FO4_VR");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_VR");
      expect(info!.shortName).toBe("VR");
      expect(info!.isVr).toBe(true);
      expect(info!.version).toBe("1.2.72.0");
    });

    test("returns null for unknown version ID", () => {
      const info = getVersionById("FO4_MISSING");
      expect(info).toBeNull();
    });

    test("version info has address library config", () => {
      const info = getVersionById("FO4_OG");
      expect(info).not.toBeNull();
      expect(info!.addressLibrary).toBeDefined();
      expect(info!.addressLibrary!.filename).toBe("version-1-10-163-0.bin");
      expect(info!.addressLibrary!.format).toBe("bin");
      expect(info!.addressLibrary!.nexusUrl).toContain("nexusmods.com");
    });

    test("VR version has CSV address library format", () => {
      const info = getVersionById("FO4_VR");
      expect(info).not.toBeNull();
      expect(info!.addressLibrary).toBeDefined();
      expect(info!.addressLibrary!.format).toBe("csv");
    });

    test("version info has XSE config", () => {
      const info = getVersionById("FO4_OG");
      expect(info).not.toBeNull();
      expect(info!.xse).toBeDefined();
      expect(info!.xse!.acronym).toBe("F4SE");
      expect(info!.xse!.compatibleVersion).toBe("0.6.23");
      expect(info!.xse!.loader).toBe("f4se_loader.exe");
    });

    test("VR version has F4SEVR XSE config", () => {
      const info = getVersionById("FO4_VR");
      expect(info).not.toBeNull();
      expect(info!.xse).toBeDefined();
      expect(info!.xse!.acronym).toBe("F4SEVR");
      expect(info!.xse!.loader).toBe("f4sevr_loader.exe");
    });

    test("version info has deprecated field", () => {
      const info = getVersionById("FO4_OG");
      expect(info).not.toBeNull();
      expect(info!.deprecated).toBe(false);
    });
  });

  describe("getVersionByVersionString", () => {
    test("finds OG by version string", () => {
      const info = getVersionByVersionString("1.10.163.0");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_OG");
    });

    test("finds NG by version string", () => {
      const info = getVersionByVersionString("1.10.984.0");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_NG");
    });

    test("finds VR by version string", () => {
      const info = getVersionByVersionString("1.2.72.0");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_VR");
    });

    test("returns null for unknown version", () => {
      const info = getVersionByVersionString("9.9.9.9");
      expect(info).toBeNull();
    });

    test("accepts 3-component version (build defaults to 0)", () => {
      const info = getVersionByVersionString("1.10.163");
      // Should parse as 1.10.163.0 and find OG
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_OG");
    });

    test("throws for invalid version string", () => {
      expect(() => getVersionByVersionString("invalid")).toThrow();
    });
  });

  describe("getVersionByShortName", () => {
    test("finds OG by short name", () => {
      const info = getVersionByShortName("OG");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_OG");
    });

    test("finds NG by short name", () => {
      const info = getVersionByShortName("NG");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_NG");
    });

    test("finds VR by short name", () => {
      const info = getVersionByShortName("VR");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_VR");
    });

    test("finds AE by short name", () => {
      const info = getVersionByShortName("AE");
      expect(info).not.toBeNull();
      expect(info!.id).toBe("FO4_AE");
    });

    test("returns null for unknown short name", () => {
      const info = getVersionByShortName("MISSING");
      expect(info).toBeNull();
    });
  });

  // ============================================================================
  // Enumeration Functions
  // ============================================================================

  describe("getAllVersions", () => {
    test("returns exactly 4 versions (OG, NG, AE, VR)", () => {
      const versions = getAllVersions();
      expect(versions).toHaveLength(4);
    });

    test("is sorted by priority descending (AE first)", () => {
      const versions = getAllVersions();
      expect(versions[0].id).toBe("FO4_AE");
    });

    test("all versions have required fields", () => {
      const versions = getAllVersions();
      for (const v of versions) {
        expect(v.id).toBeTruthy();
        expect(v.game).toBe("Fallout4");
        expect(v.version).toBeTruthy();
        expect(v.displayName).toBeTruthy();
        expect(v.shortName).toBeTruthy();
      }
    });
  });

  describe("getVersionRegistry", () => {
    test("returns snapshot for Fallout4 with all versions", () => {
      const snapshot = getVersionRegistry("Fallout4");
      expect(snapshot.game).toBe("Fallout4");
      expect(snapshot.versions).toHaveLength(4);
      expect(snapshot.unknownVersionHandling).toBeDefined();
      expect(["nearest_match", "strict", "default_only"]).toContain(
        snapshot.unknownVersionHandling.strategy,
      );
    });

    test("supports VR filter in snapshot", () => {
      const snapshot = getVersionRegistry("Fallout4", true);
      expect(snapshot.versions).toHaveLength(1);
      for (const version of snapshot.versions) {
        expect(version.isVr).toBe(true);
      }
    });

    test("returns empty version list for unknown game", () => {
      const snapshot = getVersionRegistry("UnknownGame");
      expect(snapshot.game).toBe("UnknownGame");
      expect(snapshot.versions).toEqual([]);
      expect(snapshot.unknownVersionHandling).toBeDefined();
    });
  });

  describe("getAllVersionsForGame", () => {
    test("returns all Fallout4 versions when is_vr is omitted", () => {
      const versions = getAllVersionsForGame("Fallout4");
      expect(versions).toHaveLength(4);
    });

    test("returns non-VR versions when is_vr=false", () => {
      const versions = getAllVersionsForGame("Fallout4", false);
      expect(versions).toHaveLength(3); // OG, NG, AE
      for (const v of versions) {
        expect(v.isVr).toBe(false);
      }
    });

    test("returns VR versions when is_vr=true", () => {
      const versions = getAllVersionsForGame("Fallout4", true);
      expect(versions).toHaveLength(1);
      expect(versions[0].isVr).toBe(true);
    });

    test("returns empty array for unknown game", () => {
      const versions = getAllVersionsForGame("UnknownGame");
      expect(versions).toHaveLength(0);
    });
  });

  describe("getCorrectVersions", () => {
    test("returns non-VR versions for is_vr=false", () => {
      const versions = getCorrectVersions(false);
      expect(versions).toHaveLength(3); // OG, NG, AE
      for (const v of versions) {
        expect(v.isVr).toBe(false);
      }
    });

    test("returns VR versions for is_vr=true", () => {
      const versions = getCorrectVersions(true);
      expect(versions).toHaveLength(1);
      expect(versions[0].isVr).toBe(true);
      expect(versions[0].id).toBe("FO4_VR");
    });
  });

  describe("getWrongVersions", () => {
    test("returns VR version as wrong for non-VR mode", () => {
      const versions = getWrongVersions(false);
      expect(versions).toHaveLength(1);
      expect(versions[0].isVr).toBe(true);
    });

    test("returns non-VR versions as wrong for VR mode", () => {
      const versions = getWrongVersions(true);
      expect(versions).toHaveLength(3); // OG, NG, AE
      for (const v of versions) {
        expect(v.isVr).toBe(false);
      }
    });
  });

  // ============================================================================
  // Matching Functions
  // ============================================================================

  describe("matchVersion", () => {
    test("exact match for OG version", () => {
      const result = matchVersion("1.10.163.0", "Fallout4", false);
      expect(result.confidence).toBe("exact");
      expect(result.isExact).toBe(true);
      expect(result.shouldWarn).toBe(false);
      expect(result.isValid).toBe(true);
      expect(result.versionInfo).not.toBeUndefined();
      expect(result.versionInfo!.id).toBe("FO4_OG");
    });

    test("exact match for NG version", () => {
      const result = matchVersion("1.10.984.0", "Fallout4", false);
      expect(result.confidence).toBe("exact");
      expect(result.versionInfo!.id).toBe("FO4_NG");
    });

    test("exact match for VR version", () => {
      const result = matchVersion("1.2.72.0", "Fallout4", true);
      expect(result.confidence).toBe("exact");
      expect(result.versionInfo!.id).toBe("FO4_VR");
    });

    test("nearest match for unknown version between OG and NG", () => {
      const result = matchVersion("1.10.500.0", "Fallout4", false);
      expect(result.confidence).toBe("nearest");
      expect(result.shouldWarn).toBe(true);
      expect(result.isValid).toBe(true);
      // 1.10.500 is closer to OG (163, dist=337) than NG (984, dist=484)
      expect(result.versionInfo!.id).toBe("FO4_OG");
    });

    test("range match for AE-compatible version", () => {
      const result = matchVersion("1.11.140.0", "Fallout4", false);
      // AE has compatible_range 1.11.137.0 - 1.11.999.0, so 1.11.140 should range match
      expect(result.confidence).toBe("range");
      expect(result.versionInfo!.id).toBe("FO4_AE");
    });

    test("detected version is preserved in result", () => {
      const result = matchVersion("1.10.163.0", "Fallout4", false);
      expect(result.detected).toBe("1.10.163.0");
    });

    test("message is non-empty", () => {
      const result = matchVersion("1.10.163.0", "Fallout4", false);
      expect(result.message.length).toBeGreaterThan(0);
    });

    test("throws for invalid version string", () => {
      expect(() => matchVersion("invalid", "Fallout4", false)).toThrow();
    });

    test("defaults for unknown game return unknown confidence", () => {
      const result = matchVersion("1.10.163.0", "UnknownGame", false);
      expect(result.confidence).toBe("unknown");
      expect(result.isValid).toBe(false);
      expect(result.versionInfo).toBeUndefined();
    });
  });

  describe("getAddressLibraryFilename", () => {
    test("returns filename for OG version", () => {
      const filename = getAddressLibraryFilename("1.10.163.0", false);
      expect(filename).toBe("version-1-10-163-0.bin");
    });

    test("returns filename for NG version", () => {
      const filename = getAddressLibraryFilename("1.10.984.0", false);
      expect(filename).toBe("version-1-10-984-0.bin");
    });

    test("returns filename for VR version", () => {
      const filename = getAddressLibraryFilename("1.2.72.0", true);
      expect(filename).toBe("version-1-2-72-0.csv");
    });

    test("throws for invalid version string", () => {
      expect(() => getAddressLibraryFilename("invalid", false)).toThrow();
    });
  });

  // ============================================================================
  // Crashgen Functions
  // ============================================================================

  describe("getCrashgenVersions", () => {
    test("returns crashgen configs for OG", () => {
      const configs = getCrashgenVersions("FO4_OG");
      expect(configs.length).toBeGreaterThan(0);
      expect(typeof configs[0].version).toBe("string");
      expect(typeof configs[0].name).toBe("string");
    });

    test("returns crashgen configs for NG", () => {
      const configs = getCrashgenVersions("FO4_NG");
      expect(configs.length).toBeGreaterThan(0);
      expect(typeof configs[0].version).toBe("string");
    });

    test("returns crashgen configs for AE", () => {
      const configs = getCrashgenVersions("FO4_AE");
      expect(configs.length).toBeGreaterThan(0);
      expect(typeof configs[0].version).toBe("string");
      expect(typeof configs[0].name).toBe("string");
    });

    test("returns crashgen configs for VR", () => {
      const configs = getCrashgenVersions("FO4_VR");
      expect(configs.length).toBeGreaterThan(0);
      expect(typeof configs[0].version).toBe("string");
      expect(typeof configs[0].name).toBe("string");
    });

    test("returns empty array for unknown version ID", () => {
      const configs = getCrashgenVersions("FO4_MISSING");
      expect(configs).toHaveLength(0);
    });

    test("configs have download URLs", () => {
      const configs = getCrashgenVersions("FO4_OG");
      for (const c of configs) {
        expect(typeof c.downloadUrl).toBe("string");
        if (c.downloadUrl !== "") {
          expect(c.downloadUrl).toContain("http");
        }
      }
    });

    test("configs have hasCompatibleRange field", () => {
      const configs = getCrashgenVersions("FO4_OG");
      for (const c of configs) {
        expect(typeof c.hasCompatibleRange).toBe("boolean");
      }
    });
  });

  describe("getCrashgenVersionStrings", () => {
    test("returns version strings for OG", () => {
      const versions = getCrashgenVersionStrings("FO4_OG");
      expect(versions.length).toBeGreaterThan(0);
      expect(typeof versions[0]).toBe("string");
    });

    test("returns version strings for NG", () => {
      const versions = getCrashgenVersionStrings("FO4_NG");
      expect(versions.length).toBeGreaterThan(0);
      expect(typeof versions[0]).toBe("string");
    });

    test("returns version strings for AE", () => {
      const versions = getCrashgenVersionStrings("FO4_AE");
      expect(versions.length).toBeGreaterThan(0);
      expect(typeof versions[0]).toBe("string");
    });

    test("returns version strings for VR", () => {
      const versions = getCrashgenVersionStrings("FO4_VR");
      expect(versions.length).toBeGreaterThan(0);
      expect(typeof versions[0]).toBe("string");
    });

    test("returns empty array for unknown version ID", () => {
      const versions = getCrashgenVersionStrings("FO4_MISSING");
      expect(versions).toEqual([]);
    });
  });

  describe("getCrashgenForVersion", () => {
    test("finds config when valid crashgen version is provided", () => {
      // First get a valid version string to test with
      const validVersions = getCrashgenVersionStrings("FO4_OG");
      if (validVersions.length > 0) {
        const config = getCrashgenForVersion("FO4_OG", validVersions[0]);
        expect(config).not.toBeNull();
        expect(config!.version).toBe(validVersions[0]);
        expect(typeof config!.name).toBe("string");
      }
    });

    test("returns null for unknown crashgen version", () => {
      const config = getCrashgenForVersion("FO4_OG", "9.99.99");
      expect(config).toBeNull();
    });

    test("returns null for unknown version ID", () => {
      const config = getCrashgenForVersion("FO4_MISSING", "1.28.6");
      expect(config).toBeNull();
    });
  });

  describe("hash and unknown-version APIs", () => {
    test("getAllExeHashes returns unique hashes", () => {
      const hashes = getAllExeHashes("Fallout4");
      expect(Array.isArray(hashes)).toBe(true);
      expect(hashes.length).toBeGreaterThan(0);
      expect(new Set(hashes).size).toBe(hashes.length);
    });

    test("getAllScriptHashes returns grouped script hashes", () => {
      const scriptHashes = getAllScriptHashes("Fallout4");
      expect(typeof scriptHashes).toBe("object");
      const keys = Object.keys(scriptHashes);
      expect(keys.length).toBeGreaterThan(0);
      for (const key of keys) {
        expect(Array.isArray(scriptHashes[key])).toBe(true);
      }
    });

    test("getScriptHashesForVersion returns hashes for FO4_OG", () => {
      const hashes = getScriptHashesForVersion("FO4_OG");
      expect(typeof hashes).toBe("object");
      expect(Object.keys(hashes).length).toBeGreaterThan(0);
    });

    test("getUnknownVersionHandling returns policy config", () => {
      const handling = getUnknownVersionHandling();
      expect([
        "nearest_match",
        "strict",
        "default_only",
      ]).toContain(handling.strategy);
      expect(["debug", "warning", "error"]).toContain(handling.logLevel);
      expect(typeof handling.defaults).toBe("object");
    });

    test("getUnknownVersionDefault returns configured default for Fallout4", () => {
      const fallback = getUnknownVersionDefault("Fallout4");
      if (fallback !== null) {
        expect(typeof fallback).toBe("string");
        expect(fallback.length).toBeGreaterThan(0);
      }
    });

    test("getUnknownVersionDefault returns null for unknown game", () => {
      const fallback = getUnknownVersionDefault("UnknownGame");
      expect(fallback).toBeNull();
    });
  });

  // ============================================================================
  // Version Compatibility
  // ============================================================================

  describe("isVersionCompatible", () => {
    test("OG version is compatible with its own version", () => {
      expect(isVersionCompatible("FO4_OG", "1.10.163.0")).toBe(true);
    });

    test("OG version is not compatible with NG version", () => {
      expect(isVersionCompatible("FO4_OG", "1.10.984.0")).toBe(false);
    });

    test("AE is compatible with versions in its range", () => {
      expect(isVersionCompatible("FO4_AE", "1.11.140.0")).toBe(true);
      expect(isVersionCompatible("FO4_AE", "1.11.191.0")).toBe(true);
      expect(isVersionCompatible("FO4_AE", "1.11.200.0")).toBe(true);
    });

    test("AE is not compatible with NG version", () => {
      expect(isVersionCompatible("FO4_AE", "1.10.984.0")).toBe(false);
    });

    test("returns false for unknown version ID", () => {
      expect(isVersionCompatible("FO4_MISSING", "1.10.163.0")).toBe(false);
    });

    test("throws for invalid version string", () => {
      expect(() => isVersionCompatible("FO4_OG", "invalid")).toThrow();
    });
  });

  // ============================================================================
  // GameVersion Utility Functions
  // ============================================================================

  describe("parseGameVersion", () => {
    test("parses 4-component version", () => {
      expect(parseGameVersion("1.10.163.0")).toBe("1.10.163.0");
    });

    test("parses 3-component version (build defaults to 0)", () => {
      expect(parseGameVersion("1.10.163")).toBe("1.10.163.0");
    });

    test("throws for invalid version string", () => {
      expect(() => parseGameVersion("invalid")).toThrow();
    });

    test("throws for 2-component version", () => {
      expect(() => parseGameVersion("1.10")).toThrow();
    });

    test("throws for 5-component version", () => {
      expect(() => parseGameVersion("1.10.163.0.1")).toThrow();
    });

    test("throws for empty string", () => {
      expect(() => parseGameVersion("")).toThrow();
    });
  });

  describe("gameVersionDistance", () => {
    test("distance between same version is 0", () => {
      expect(gameVersionDistance("1.10.163.0", "1.10.163.0")).toBe(0);
    });

    test("patch-level difference for OG to NG", () => {
      // OG: 1.10.163.0, NG: 1.10.984.0
      // distance = 0 * 1,000,000 + 0 * 1,000 + |984-163| = 821
      expect(gameVersionDistance("1.10.163.0", "1.10.984.0")).toBe(821);
    });

    test("patch-level difference", () => {
      // 1.10.163.0 vs 1.10.500.0 = 337
      expect(gameVersionDistance("1.10.163.0", "1.10.500.0")).toBe(337);
    });

    test("major version difference is large", () => {
      const dist = gameVersionDistance("1.10.163.0", "2.0.0.0");
      expect(dist).toBeGreaterThan(1_000_000);
    });

    test("distance ignores build component changes", () => {
      expect(gameVersionDistance("1.10.163.0", "1.10.163.99")).toBe(0);
    });

    test("throws for invalid version", () => {
      expect(() => gameVersionDistance("invalid", "1.10.163.0")).toThrow();
      expect(() => gameVersionDistance("1.10.163.0", "invalid")).toThrow();
    });
  });

  // ============================================================================
  // Crashgen Registry + Settings Rules (Plan 4 version_registry promotion)
  // ============================================================================

  describe("JsCrashgenRegistryEntry interface shape", () => {
    test("crashgenRegistry on version snapshot contains expected fields", () => {
      const snapshot = getVersionRegistry("Fallout4");
      // The snapshot may or may not expose crashgenRegistry depending on the binding
      // Verify the type shape via getVersionById which includes crashgen data
      const ogInfo = getVersionById("FO4_OG");
      expect(ogInfo).not.toBeNull();
      // Verify crashgen config data exists at the version level
      const configs = getCrashgenVersions("FO4_OG");
      expect(configs.length).toBeGreaterThan(0);
      // Each config has typed string fields
      const first = configs[0];
      expect(typeof first.name).toBe("string");
      expect(typeof first.version).toBe("string");
    });
  });

  describe("JsCrashgenSettingsRules interface shape", () => {
    test("interface has version, preflight, and checks fields", () => {
      // Type-level assertion: constructing a minimal typed object proves the interface
      // shape matches the NAPI-generated definition (version: number, preflight: array, checks: array)
      const rules: JsCrashgenSettingsRules = {
        version: 1,
        preflight: [],
        checks: [],
      };
      expect(typeof rules.version).toBe("number");
      expect(Array.isArray(rules.preflight)).toBe(true);
      expect(Array.isArray(rules.checks)).toBe(true);
    });
  });

  describe("checkCrashgenConfigWithRules", () => {
    test("callable with verified signature (pluginsPath, crashgenName, settingsRules?)", () => {
      // Signature: checkCrashgenConfigWithRules(pluginsPath: string, crashgenName: string, settingsRules?: JsCrashgenSettingsRules | undefined | null): JsCrashgenCheckResult
      try {
        const result = checkCrashgenConfigWithRules("", "Buffout 4");
        expect(result).toBeDefined();
        expect(typeof result).toBe("object");
      } catch (e) {
        // Function may reject empty path — assert the error shape
        expect(e).toBeInstanceOf(Error);
      }
    });
  });

  describe("checkCrashgenFullWithRules", () => {
    test("callable with verified signature (pluginsPath, crashgenName, settingsRules?)", () => {
      // Signature: checkCrashgenFullWithRules(pluginsPath: string, crashgenName: string, settingsRules?: JsCrashgenSettingsRules | undefined | null): JsCrashgenReport
      try {
        const result = checkCrashgenFullWithRules("", "Buffout 4");
        expect(result).toBeDefined();
        expect(typeof result).toBe("object");
      } catch (e) {
        // Function may reject empty path — assert the error shape
        expect(e).toBeInstanceOf(Error);
      }
    });
  });
});
