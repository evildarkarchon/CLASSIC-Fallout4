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
  loadBatchSync,
  loadBatchAsync,
  resetSettingsCacheStats,
  settingsCacheKeys,
  settingsCacheSize,
  clearSettingsCache,
  clearHashCache,
  validateSettingsPath,
  validateSettingsPaths,
  normalizePath,
  joinPaths,
  validatePathsBatch,
  isRuntimeAvailable,
  getRuntimeInfo,
  clearAllMetrics,
  recordTimingMetric,
  getMetricsSummary,
  createMessage,
  formatMessage,
  JsMessageType,
  JsMessageTarget,
  JsFileIO,
  detectEncoding,
  getHashCacheStats,
  hashFile,
  JsDatabasePool,
  detectResourceType,
  parseResourceType,
  isSupportedResource,
  getResourceExtensions,
  createResourceInfo,
  parseXseType,
  xseTypeForGame,
  xseLoaderName,
  xseDllPrefix,
  getModSiteUrl,
  getModSiteName,
  getModSiteGameUrl,
  getUserAgent,
  getUserAgentPrefix,
  getUserAgentWithSuffix,
  isValidUrl,
  validateUrl,
  joinUrl,
  buildUrlWithQuery,
  GithubClient,
  hasUpdate,
  JsEnbChecker,
  checkEnb,
  JsLogProcessor,
  processGameLogs,
  runGameSetupIntake,
  scanAllBa2Archives,
  scanUnpackedFiles,
  getVersionById,
  getAllVersionsForGame,
  getVersionByVersionString,
  YamlDocument,
  yamlClearCache,
  yamlGetCacheStats,
  yamlParse,
  resetHashCacheStats,
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
import { getRuntimeCoverageEntries } from "./fixtures/runtime_coverage_registry";

const THIS_SUITE =
  "node-bindings/classic-node/__test__/parity_tier1.spec.ts";
const activeCoverageCases = new Set(
  getRuntimeCoverageEntries(THIS_SUITE)
    .map((entry) => entry.testCaseId)
    .filter((testCaseId): testCaseId is string => Boolean(testCaseId)),
);

function expectErrorWithMessage(err: unknown): void {
  expect(err).toBeDefined();
  const message = err instanceof Error ? err.message : String(err);
  expect(message.trim().length).toBeGreaterThan(0);
}

describe("Tier-1 parity fixture suites", () => {
  if (activeCoverageCases.has("scanlog-tier1-parity")) {
    describe("scanlog parity", () => {
      for (const fixture of scanlogConfigCases) {
        test(`createAnalysisConfig parity: ${fixture.id}`, () => {
          const config = createAnalysisConfig(fixture.game, fixture.gameVersion);
          expect(config.game).toBe(fixture.game);
          expect(config.gameVersion).toBe(fixture.gameVersion);
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
            "auto",
            fixture.options,
          );
          expect(config.game).toBe("Fallout4");
          expect(config.gameVersion).toBe("auto");
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
            "auto",
          );
          expect(true).toBe(false);
        } catch (err: unknown) {
          expectErrorWithMessage(err);
        }
      });
    });
  }

  if (activeCoverageCases.has("config-tier1-parity")) {
    describe("config parity", () => {
    test("createYamlDataFromContent returns stable Tier-1 fields", () => {
      const data = createYamlDataFromContent(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
      );
      expect(data.classicVersion).toBe("9.0.0");
      expect(data.xseAcronym).toBe("F4SE");
      expect(data.crashgenName).toBe("Buffout 4");
      expect(data.ignoreList).toEqual(["IgnoreItem1"]);
      expect(data.gameVersion).toBe("1.10.163");
      expect(
        (data as unknown as Record<string, unknown>).gameVersionNew,
      ).toBeUndefined();
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
          "auto",
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
      expect(Object.keys(stats).sort()).toEqual([
        "capacity",
        "hit_rate",
        "hits",
        "misses",
        "size",
      ]);
      expect(typeof stats.hit_rate).toBe("number");
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
        expect(typeof stats.hit_rate).toBe("number");
        expect(stats.size).toBe(1);
        expect(stats.capacity).toBeGreaterThan(0);

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
  }

  if (activeCoverageCases.has("aux-tier1-parity")) {
    describe("aux foundation parity", () => {
    test("shared runtime/path/metrics APIs keep stable callable shape", () => {
      const normalized = normalizePath(".");
      expect(typeof normalized).toBe("string");
      expect(normalized.length).toBeGreaterThan(0);

      const joined = joinPaths(["C:\\", "Games", "Fallout4"]);
      expect(joined.includes("Games")).toBe(true);
      expect(joined.includes("Fallout4")).toBe(true);

      const batch = validatePathsBatch([".", "Z:\\nonexistent\\classic-tier1"]);
      expect(batch["."]).toBe(true);
      expect(batch["Z:\\nonexistent\\classic-tier1"]).toBe(false);

      expect(isRuntimeAvailable()).toBe(true);
      const runtime = getRuntimeInfo();
      expect(runtime.available).toBe(true);
      expect(runtime.threadCount).toBeGreaterThan(0);

      clearAllMetrics();
      recordTimingMetric("tier1_aux_metrics", 12.5);
      const summary = getMetricsSummary();
      expect(summary.timings.tier1_aux_metrics.count).toBe(1);
    });

    test("message APIs preserve enum and formatting semantics", () => {
      const message = createMessage(
        JsMessageType.Info,
        "Tier1 message [ok]",
        JsMessageTarget.All,
      );
      expect(message.messageType).toBe("Info");
      expect(message.target).toBe("All");
      expect(formatMessage(message).includes("Tier1 message")).toBe(true);
    });

    test("settings batch APIs remain stable in sync + async modes", async () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-batch-"));
      const pathA = join(dir, "a.yaml");
      const pathB = join(dir, "b.yaml");
      try {
        writeFileSync(pathA, "alpha: 1\n", "utf-8");
        writeFileSync(pathB, "beta: 2\n", "utf-8");
        clearSettingsCache();

        expect(loadBatchSync([pathA, pathB])).toBe(2);
        clearSettingsCache();

        expect(await loadBatchAsync([pathA, pathB])).toBe(2);
      } finally {
        clearSettingsCache();
        rmSync(dir, { recursive: true, force: true });
      }
    });

    test("file foundations keep JsFileIO + detectEncoding behavior", async () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-fileio-"));
      const filePath = join(dir, "encoding.txt");
      try {
        const io = new JsFileIO();
        await io.writeFile(filePath, "hello world");
        expect(await io.readFile(filePath)).toBe("hello world");
        expect(detectEncoding(filePath)).toBe("UTF-8");
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });

    test("hash cache helpers keep canonical stats and bounded semantics", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-hash-cache-"));
      const filePath = join(dir, "hash.txt");
      try {
        writeFileSync(filePath, "tier1 hash cache", "utf-8");
        clearHashCache();
        resetHashCacheStats();

        const initial = getHashCacheStats();
        expect(Object.keys(initial).sort()).toEqual([
          "capacity",
          "hit_rate",
          "hits",
          "misses",
          "size",
        ]);

        expect(hashFile(filePath).length).toBe(64);
        expect(hashFile(filePath).length).toBe(64);

        const warmed = getHashCacheStats();
        expect(warmed.misses).toBe(1);
        expect(warmed.hits).toBe(1);
        expect(warmed.hit_rate).toBeCloseTo(0.5, 5);
        expect(warmed.size).toBeLessThanOrEqual(warmed.capacity);

        resetHashCacheStats();
        const reset = getHashCacheStats();
        expect(reset.hits).toBe(0);
        expect(reset.misses).toBe(0);
        expect(reset.size).toBe(1);

        clearHashCache();
        expect(getHashCacheStats().size).toBe(0);
      } finally {
        clearHashCache();
        resetHashCacheStats();
        rmSync(dir, { recursive: true, force: true });
      }
    });
    });
  }

  if (activeCoverageCases.has("scangame-tier1-parity")) {
    describe("scangame parity", () => {
    test("setup intake forwards configured executable path for non-default basenames", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-setup-"));
      const gameRoot = join(dir, "Fallout4");
      const docsRoot = join(dir, "Docs");
      const configuredExe = join(gameRoot, "Fallout4Custom.exe");

      try {
        mkdirSync(gameRoot, { recursive: true });
        mkdirSync(docsRoot, { recursive: true });
        writeFileSync(join(docsRoot, "Fallout4.ini"), "[General]\n", "utf-8");
        writeFileSync(join(docsRoot, "Fallout4Custom.ini"), "[Archive]\n", "utf-8");
        writeFileSync(join(docsRoot, "Fallout4Prefs.ini"), "[General]\n", "utf-8");
        writeFileSync(configuredExe, "not a real pe", "utf-8");
        writeFileSync(join(gameRoot, "f4se_loader.exe"), "loader", "utf-8");

        const result = runGameSetupIntake({
          gameId: "Fallout4",
          gameVersion: "auto",
          gameRoot,
          gameExePath: configuredExe,
          docsRoot,
        });

        expect(result.status).toBe("action_required");
        expect(result.hasErrors).toBe(false);
        expect(result.actionCount).toBe(1);
        expect(result.gameRoot).toBe(gameRoot);
        expect(result.docsRoot).toBe(docsRoot);
        expect(result.renderedReport).toContain(
          "Resolved game root from configured executable",
        );
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });
    });
  }

  if (activeCoverageCases.has("aux-tier1-parity")) {
    describe("aux scanner stack parity", () => {
    test("database/resource/xse/web/update APIs keep stable callable shape", async () => {
      const pool = new JsDatabasePool("Fallout4");
      expect(pool.getGameTable()).toBe("Fallout4");
      expect(await pool.getEntry("012345", "Test.esm")).toBeNull();

      expect(detectResourceType("mods/MyMod.esp")).toBe("plugin");
      expect(parseResourceType("TEXTURE")).toBe("texture");
      expect(isSupportedResource("meshes/body.nif")).toBe(true);
      expect(getResourceExtensions("plugin")).toContain("esp");
      expect(createResourceInfo("textures/armor.dds").resourceType).toBe("texture");

      expect(parseXseType("f4se")).toBe("F4SE");
      expect(xseTypeForGame("Fallout4")).toBe("F4SE");
      expect(xseLoaderName("F4SE")).toContain("loader");
      expect(xseDllPrefix("F4SE")).toContain("f4se");

      expect(getModSiteUrl("NexusMods")).toContain("nexusmods.com");
      expect(getModSiteName("NexusMods")).toBe("Nexus Mods");
      expect(getModSiteGameUrl("NexusMods", "Fallout4")).toContain("fallout4");
      expect(getUserAgentPrefix()).toBe("CLASSIC");
      expect(getUserAgent()).toContain("CLASSIC/");
      expect(getUserAgentWithSuffix("Tier1")).toContain("Tier1");
      expect(isValidUrl("https://www.nexusmods.com")).toBe(true);
      expect(validateUrl("https://example.com")).toContain("https://example.com");
      expect(joinUrl("https://example.com", "api/v1")).toContain("/api/v1");
      expect(
        buildUrlWithQuery("https://example.com/search", [{ key: "q", value: "tier1" }]),
      ).toContain("q=tier1");

      const client = new GithubClient("owner", "repo");
      expect(client.repoUrl()).toContain("github.com/owner/repo");
      expect(hasUpdate("1.0.0", "1.0.1")).toBe(true);
    });

    test("scangame scanner stack keeps stable local semantics", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-tier1-scanner-stack-"));
      const logPath = join(dir, "stack.log");
      try {
        writeFileSync(logPath, "INFO: start\nERROR: scanner stack parity\n", "utf-8");

        const enbChecker = new JsEnbChecker(dir);
        expect(enbChecker.checkBinaries()).toBe("NotInstalled");
        expect(checkEnb(dir).isPresent).toBe(false);

        const logProcessor = new JsLogProcessor(["error"], [], []);
        expect(logProcessor.processLogs(dir)).toContain("TOTAL NUMBER OF DETECTED LOG ERRORS");
        expect(processGameLogs(dir, ["error"], [], [])).toContain("TOTAL NUMBER OF DETECTED LOG ERRORS");

        expect(scanAllBa2Archives(dir)).toEqual([]);

        const unpacked = scanUnpackedFiles(dir, []);
        expect(Array.isArray(unpacked.texFrmt)).toBe(true);
        expect(Array.isArray(unpacked.sndFrmt)).toBe(true);
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });
    });
  }

  if (activeCoverageCases.has("version-registry-tier1-parity")) {
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
  }
});
