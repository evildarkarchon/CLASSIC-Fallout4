import { describe, test, expect } from "bun:test";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  BATCH_CACHE_TTL,
  DEFAULT_CACHE_TTL,
  MAX_CACHE_TTL,
  createAnalysisConfig,
  createAnalysisConfigFromYamlContent,
  processLogWithYamlContent,
  createYamlDataFromContent,
  getAllYamlFiles,
  getBatchCacheTtl,
  getCached,
  getDefaultCacheTtl,
  getMaxCacheTtl,
  getSettingsCacheStats,
  getYamlFileDescription,
  getYamlSourcePath,
  getYamlSourceDisplayNameWithGame,
  invalidateSettings,
  isCached,
  loadSettingsSync,
  resetSettingsCacheStats,
  settingsCacheKeys,
  settingsCacheSize,
  clearSettingsCache,
  validateSettingsPath,
  validateSettingsPaths,
  getVersionById,
  getAllVersionsForGame,
  getVersionByVersionString,
  YamlDocument,
  yamlClearCache,
  yamlGetCacheStats,
  yamlParse,
  yamlStringify,
} from "../index.js";
import {
  PARITY_MAIN_YAML,
  PARITY_GAME_YAML,
  PARITY_IGNORE_YAML,
  INVALID_PARITY_MAIN_YAML,
  scanlogConfigCases,
  scanlogYamlOptionsCases,
  scanlogErrorCase,
  configSourceCases,
  versionRegistryCases,
} from "./fixtures/tier1_parity.fixtures";

function expectErrorWithMessage(err: unknown): void {
  expect(err).toBeDefined();
  const message = err instanceof Error ? err.message : String(err);
  expect(message.trim().length).toBeGreaterThan(0);
}

describe("Tier-1 parity fixture suites", () => {
  describe("scanlog parity", () => {
    for (const fixture of scanlogConfigCases) {
      test(`createAnalysisConfig parity: ${fixture.id}`, () => {
        const config = createAnalysisConfig(fixture.game, fixture.vrMode);
        expect(config.game).toBe(fixture.game);
        expect(config.vrMode).toBe(fixture.vrMode);
        expect(config.crashgenName).toBe(fixture.expected.crashgenName);
        expect(config.xseAcronym).toBe(fixture.expected.xseAcronym);
        expect(config.classicVersion).toBe(fixture.expected.classicVersion);
        expect(config.fcxMode).toBe(fixture.expected.fcxMode);
        expect(config.simplifyLogs).toBe(fixture.expected.simplifyLogs);
      });
    }

    for (const fixture of scanlogYamlOptionsCases) {
      test(`createAnalysisConfigFromYamlContent parity: ${fixture.id}`, () => {
        const config = createAnalysisConfigFromYamlContent(
          PARITY_MAIN_YAML,
          PARITY_GAME_YAML,
          PARITY_IGNORE_YAML,
          "Fallout4",
          false,
          fixture.options,
        );
        expect(config.game).toBe("Fallout4");
        expect(config.vrMode).toBe(false);
        expect(config.crashgenName).toBe(fixture.expected.crashgenName);
        expect(config.xseAcronym).toBe(fixture.expected.xseAcronym);
        expect(config.classicVersion).toBe(fixture.expected.classicVersion);
        expect(config.fcxMode).toBe(fixture.expected.fcxMode);
        expect(config.simplifyLogs).toBe(fixture.expected.simplifyLogs);
      });
    }

    test("processLogWithYamlContent keeps stable reject semantics for missing file", async () => {
      try {
        await processLogWithYamlContent(
          scanlogErrorCase.missingLogPath,
          PARITY_MAIN_YAML,
          PARITY_GAME_YAML,
          PARITY_IGNORE_YAML,
          "Fallout4",
          false,
        );
        expect(true).toBe(false);
      } catch (err: unknown) {
        expectErrorWithMessage(err);
      }
    });
  });

  describe("config parity", () => {
    test("createYamlDataFromContent returns stable Tier-1 fields", () => {
      const data = createYamlDataFromContent(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        false,
      );
      expect(data.classicVersion).toBe("9.0.0");
      expect(data.xseAcronym).toBe("F4SE");
      expect(data.crashgenName).toBe("Buffout 4");
      expect(data.ignoreList).toEqual(["IgnoreItem1"]);
      expect(data.gameVersion).toBe("1.10.163");
      expect(data.gameVersionNew).toBe("1.10.984");
    });

    for (const fixture of configSourceCases) {
      test(`YamlSource mapping parity: ${fixture.id}`, () => {
        const path = getYamlSourcePath(fixture.source, fixture.game);
        expect(path).toContain(fixture.expectedPathToken);

        const displayName = getYamlSourceDisplayNameWithGame(
          fixture.source,
          fixture.game,
        );
        expect(displayName).toBe(fixture.expectedDisplayName);
      });
    }

    test("createYamlDataFromContent keeps stable error semantics for invalid YAML", () => {
      try {
        createYamlDataFromContent(
          INVALID_PARITY_MAIN_YAML,
          PARITY_GAME_YAML,
          PARITY_IGNORE_YAML,
          "Fallout4",
          false,
        );
        expect(true).toBe(false);
      } catch (err: unknown) {
        expectErrorWithMessage(err);
      }
    });

    test("cache TTL constants and getters stay aligned", () => {
      expect(DEFAULT_CACHE_TTL).toBe(getDefaultCacheTtl());
      expect(BATCH_CACHE_TTL).toBe(getBatchCacheTtl());
      expect(MAX_CACHE_TTL).toBe(getMaxCacheTtl());
      expect(DEFAULT_CACHE_TTL).toBeLessThan(BATCH_CACHE_TTL);
      expect(BATCH_CACHE_TTL).toBeLessThanOrEqual(MAX_CACHE_TTL);
    });

    test("YAML constants and descriptions remain stable", () => {
      const yamlFiles = getAllYamlFiles();
      expect(yamlFiles).toContain("Main");
      expect(yamlFiles).toContain("Cache");
      expect(getYamlFileDescription("Main")).toContain("CLASSIC Main.yaml");
      expect(getYamlFileDescription("Cache")).toContain("cache.yaml");
    });

    test("YAML helper APIs keep parse/stringify/document semantics", () => {
      const parsed = yamlParse("root:\n  count: 2\n  enabled: true\n");
      expect(parsed.root.count).toBe(2);
      expect(parsed.root.enabled).toBe(true);

      const asYaml = yamlStringify(parsed);
      expect(asYaml).toContain("root");

      const doc = new YamlDocument(asYaml);
      doc.setValue("root.enabled", false);
      expect(doc.getValue("root.enabled")).toBe(false);
      expect(doc.getStringValue("root.missing", "fallback")).toBe("fallback");
    });

    test("YAML cache APIs expose stable stats shape", () => {
      yamlClearCache();
      const stats = yamlGetCacheStats();
      expect(typeof stats.cachedFiles).toBe("number");
      expect(typeof stats.totalBytes).toBe("number");
    });

    test("settings cache lifecycle remains stable", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-config-"));
      const filePath = join(dir, "settings.yaml");
      const cacheKey = "tier1-config-cache-key";

      try {
        writeFileSync(filePath, "root:\n  enabled: true\n", "utf-8");
        clearSettingsCache();
        resetSettingsCacheStats();

        const docs = loadSettingsSync(cacheKey, filePath);
        expect(docs[0].root.enabled).toBe(true);
        expect(isCached(cacheKey)).toBe(true);
        expect(settingsCacheSize()).toBe(1);
        expect(settingsCacheKeys()).toContain(cacheKey);

        const cached = getCached(cacheKey);
        expect(cached).not.toBeNull();
        expect(cached![0].root.enabled).toBe(true);

        const stats = getSettingsCacheStats();
        expect(stats.hits).toBeGreaterThanOrEqual(1);
        expect(stats.size).toBe(1);

        expect(invalidateSettings(cacheKey)).toBe(true);
        expect(isCached(cacheKey)).toBe(false);
      } finally {
        clearSettingsCache();
        rmSync(dir, { recursive: true, force: true });
      }
    });

    test("settings path validators keep non-throwing semantics for valid paths", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-paths-"));
      const gameDir = join(dir, "game");
      const docsDir = join(dir, "docs");

      try {
        mkdirSync(gameDir, { recursive: true });
        mkdirSync(docsDir, { recursive: true });
        writeFileSync(join(gameDir, "Fallout4.exe"), "stub", "utf-8");

        expect(() =>
          validateSettingsPath(gameDir, "gamePath", ["Fallout4.exe"]),
        ).not.toThrow();
        expect(() =>
          validateSettingsPaths(gameDir, docsDir, null, "Fallout4.exe"),
        ).not.toThrow();
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });
  });

  describe("version registry parity", () => {
    for (const fixture of versionRegistryCases) {
      test(`getVersionById parity: ${fixture.id}`, () => {
        const info = getVersionById(fixture.versionId);
        expect(info).not.toBeNull();
        expect(info!.id).toBe(fixture.versionId);
        expect(info!.shortName).toBe(fixture.expectedShortName);
        expect(info!.isVr).toBe(fixture.expectedIsVr);
        expect(info!.version).toBe(fixture.expectedVersion);
      });
    }

    test("getAllVersionsForGame parity covers optional isVr semantics", () => {
      const all = getAllVersionsForGame("Fallout4");
      const nonVr = getAllVersionsForGame("Fallout4", false);
      const vrOnly = getAllVersionsForGame("Fallout4", true);

      expect(all).toHaveLength(4);
      expect(nonVr).toHaveLength(3);
      expect(vrOnly).toHaveLength(1);
      expect(vrOnly[0].id).toBe("FO4_VR");
    });

    test("getVersionByVersionString keeps stable throw semantics for invalid input", () => {
      try {
        getVersionByVersionString("invalid");
        expect(true).toBe(false);
      } catch (err: unknown) {
        expectErrorWithMessage(err);
      }
    });
  });
});
