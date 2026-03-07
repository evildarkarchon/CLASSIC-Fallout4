import { describe, test, expect } from "bun:test";
import { readFileSync } from "fs";
import { join } from "path";
import {
  CRASH_AUTOSCAN_PATTERN,
  calculateTextSimilarity,
  checkDriveExists,
  createAnalysisConfigFromYamlContent,
  getAllVersionsForGame,
  getAllExeHashes,
  getAllGameIds,
  getGameName,
  getAllScriptHashes,
  matchVersion,
  getUnknownVersionHandling,
  checkCrashgenVersionStatus,
  getYamlSourceDisplayName,
} from "../index.js";
import {
  PARITY_MAIN_YAML,
  PARITY_GAME_YAML,
  PARITY_IGNORE_YAML,
} from "./fixtures/tier1_parity.fixtures";
import {
  dtsSignatureFragments,
  confidenceValues,
  unknownVersionStrategies,
  unknownVersionLogLevels,
  crashgenStatusCases,
  yamlDisplayNameCases,
} from "./fixtures/tier1_regression.fixtures";

describe("Tier-1 drift regression pack", () => {
  test("index.d.ts keeps drift-prone signature declarations", () => {
    const dtsPath = join(import.meta.dir, "..", "index.d.ts");
    const dts = readFileSync(dtsPath, "utf8");

    for (const signature of dtsSignatureFragments) {
      expect(dts.includes(signature)).toBe(true);
    }
  });

  test("optional scanlog options stay backward-compatible", () => {
    const omittedOptions = createAnalysisConfigFromYamlContent(
      PARITY_MAIN_YAML,
      PARITY_GAME_YAML,
      PARITY_IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    const nullOptions = createAnalysisConfigFromYamlContent(
      PARITY_MAIN_YAML,
      PARITY_GAME_YAML,
      PARITY_IGNORE_YAML,
      "Fallout4",
      "auto",
      null,
    );
    const emptyOptions = createAnalysisConfigFromYamlContent(
      PARITY_MAIN_YAML,
      PARITY_GAME_YAML,
      PARITY_IGNORE_YAML,
      "Fallout4",
      "auto",
      {},
    );

    expect(omittedOptions).toEqual(nullOptions);
    expect(omittedOptions).toEqual(emptyOptions);
  });

  test("optional version-registry parameters keep stable defaults", () => {
    const all = getAllVersionsForGame("Fallout4");
    const nonVr = getAllVersionsForGame("Fallout4", false);
    const vrOnly = getAllVersionsForGame("Fallout4", true);
    const exeHashesDefault = getAllExeHashes();
    const exeHashesNamedDefault = getAllExeHashes("Fallout4");
    const scriptHashesDefault = getAllScriptHashes();
    const scriptHashesNamedDefault = getAllScriptHashes("Fallout4");

    expect(all).toHaveLength(4);
    expect(nonVr).toHaveLength(3);
    expect(vrOnly).toHaveLength(1);
    expect(exeHashesDefault).toEqual(exeHashesNamedDefault);
    expect(scriptHashesDefault).toEqual(scriptHashesNamedDefault);
  });

  test("phase4c aux residual exports keep stable behavior", () => {
    expect(CRASH_AUTOSCAN_PATTERN).toContain("AUTOSCAN");

    const identicalRatio = calculateTextSimilarity("a\nb\nc", "a\nb\nc");
    const differentRatio = calculateTextSimilarity("a\nb\nc", "x\ny\nz");
    expect(identicalRatio).toBe(1);
    expect(differentRatio).toBeGreaterThanOrEqual(0);
    expect(differentRatio).toBeLessThanOrEqual(1);

    expect(() => checkDriveExists("C:\\Games")).not.toThrow();

    const ids = getAllGameIds();
    expect(ids).toContain("Fallout4");
    expect(ids).toContain("Fallout4VR");
    for (const id of ids) {
      expect(getGameName(id).length).toBeGreaterThan(0);
    }
  });

  test("matchVersion confidence string mapping remains stable", () => {
    const exact = matchVersion("1.10.163.0", "Fallout4", false);
    const nearest = matchVersion("1.10.500.0", "Fallout4", false);
    const range = matchVersion("1.11.140.0", "Fallout4", false);

    expect(confidenceValues).toContain(exact.confidence as (typeof confidenceValues)[number]);
    expect(confidenceValues).toContain(nearest.confidence as (typeof confidenceValues)[number]);
    expect(confidenceValues).toContain(range.confidence as (typeof confidenceValues)[number]);
  });

  test("unknown-version strategy and log-level string mapping remains stable", () => {
    const handling = getUnknownVersionHandling();
    expect(unknownVersionStrategies).toContain(
      handling.strategy as (typeof unknownVersionStrategies)[number],
    );
    expect(unknownVersionLogLevels).toContain(
      handling.logLevel as (typeof unknownVersionLogLevels)[number],
    );
  });

  for (const fixture of crashgenStatusCases) {
    test(`checkCrashgenVersionStatus mapping: ${fixture.expected}`, () => {
      const status = checkCrashgenVersionStatus(
        fixture.detected,
        fixture.validVersions as string[],
      );
      expect(status).toBe(fixture.expected);
    });
  }

  for (const fixture of yamlDisplayNameCases) {
    test(`getYamlSourceDisplayName mapping: ${fixture.source}`, () => {
      expect(getYamlSourceDisplayName(fixture.source)).toBe(fixture.expected);
    });
  }
});
