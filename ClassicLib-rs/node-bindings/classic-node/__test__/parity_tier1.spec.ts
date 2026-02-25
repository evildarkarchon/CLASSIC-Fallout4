import { describe, test, expect } from "bun:test";
import {
  createAnalysisConfig,
  createAnalysisConfigFromYamlContent,
  processLogWithYamlContent,
  createYamlDataFromContent,
  getYamlSourcePath,
  getYamlSourceDisplayNameWithGame,
  getVersionById,
  getAllVersionsForGame,
  getVersionByVersionString,
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
