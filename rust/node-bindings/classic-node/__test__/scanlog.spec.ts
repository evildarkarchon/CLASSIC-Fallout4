import { describe, test, expect } from "bun:test";
import {
  createAnalysisConfig,
  getVersion,
} from "../index.js";

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
});
