import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { mkdirSync, writeFileSync, rmSync } from "fs";
import { join } from "path";
import {
  parseXseType,
  xseTypeForGame,
  xseTypeName,
  xseLoaderName,
  xseDllPrefix,
  isXseInstalled,
  detectXseVersion,
  getXseInfo,
} from "../index.js";

// ============================================================================
// Test fixture directory with mock XSE installation
// ============================================================================

const TEST_DIR = join(import.meta.dir, "__xse_test_data__");
const MOCK_GAME_DIR = join(TEST_DIR, "mock_game");
const EMPTY_GAME_DIR = join(TEST_DIR, "empty_game");

beforeAll(() => {
  // Create a mock game directory with F4SE files
  mkdirSync(MOCK_GAME_DIR, { recursive: true });
  mkdirSync(EMPTY_GAME_DIR, { recursive: true });

  // Create a fake F4SE loader and version DLL
  writeFileSync(join(MOCK_GAME_DIR, "f4se_loader.exe"), "fake-loader");
  writeFileSync(join(MOCK_GAME_DIR, "f4se_1_10_163.dll"), "fake-dll");
});

afterAll(() => {
  rmSync(TEST_DIR, { recursive: true, force: true });
});

// ============================================================================
// parseXseType
// ============================================================================

describe("parseXseType", () => {
  test("parses lowercase f4se", () => {
    expect(parseXseType("f4se")).toBe("F4SE");
  });

  test("parses uppercase F4SE", () => {
    expect(parseXseType("F4SE")).toBe("F4SE");
  });

  test("parses SKSE64", () => {
    expect(parseXseType("skse64")).toBe("SKSE64");
  });

  test("parses SFSE", () => {
    expect(parseXseType("sfse")).toBe("SFSE");
  });

  test("parses F4SEVR", () => {
    expect(parseXseType("f4sevr")).toBe("F4SEVR");
  });

  test("parses SKSE", () => {
    expect(parseXseType("skse")).toBe("SKSE");
  });

  test("parses SKSEVR", () => {
    expect(parseXseType("sksevr")).toBe("SKSEVR");
  });

  test("throws on invalid type name", () => {
    expect(() => parseXseType("invalid")).toThrow();
  });

  test("throws on empty string", () => {
    expect(() => parseXseType("")).toThrow();
  });
});

// ============================================================================
// xseTypeForGame
// ============================================================================

describe("xseTypeForGame", () => {
  test("returns F4SE for Fallout4", () => {
    expect(xseTypeForGame("Fallout4")).toBe("F4SE");
  });

  test("returns F4SEVR for Fallout4VR", () => {
    expect(xseTypeForGame("Fallout4VR")).toBe("F4SEVR");
  });

  test("returns SKSE64 for Skyrim", () => {
    expect(xseTypeForGame("Skyrim")).toBe("SKSE64");
  });

  test("returns SFSE for Starfield", () => {
    expect(xseTypeForGame("Starfield")).toBe("SFSE");
  });
});

// ============================================================================
// xseTypeName
// ============================================================================

describe("xseTypeName", () => {
  test("returns 'F4SE' for F4SE type", () => {
    expect(xseTypeName("F4SE")).toBe("F4SE");
  });

  test("returns 'SKSE64' for SKSE64 type", () => {
    expect(xseTypeName("SKSE64")).toBe("SKSE64");
  });

  test("returns 'SFSE' for SFSE type", () => {
    expect(xseTypeName("SFSE")).toBe("SFSE");
  });

  test("returns 'F4SEVR' for F4SEVR type", () => {
    expect(xseTypeName("F4SEVR")).toBe("F4SEVR");
  });

  test("returns 'SKSE' for SKSE type", () => {
    expect(xseTypeName("SKSE")).toBe("SKSE");
  });

  test("returns 'SKSEVR' for SKSEVR type", () => {
    expect(xseTypeName("SKSEVR")).toBe("SKSEVR");
  });
});

// ============================================================================
// xseLoaderName
// ============================================================================

describe("xseLoaderName", () => {
  test("returns f4se_loader.exe for F4SE", () => {
    expect(xseLoaderName("F4SE")).toBe("f4se_loader.exe");
  });

  test("returns skse64_loader.exe for SKSE64", () => {
    expect(xseLoaderName("SKSE64")).toBe("skse64_loader.exe");
  });

  test("returns sfse_loader.exe for SFSE", () => {
    expect(xseLoaderName("SFSE")).toBe("sfse_loader.exe");
  });

  test("returns f4sevr_loader.exe for F4SEVR", () => {
    expect(xseLoaderName("F4SEVR")).toBe("f4sevr_loader.exe");
  });

  test("returns skse_loader.exe for SKSE", () => {
    expect(xseLoaderName("SKSE")).toBe("skse_loader.exe");
  });

  test("returns sksevr_loader.exe for SKSEVR", () => {
    expect(xseLoaderName("SKSEVR")).toBe("sksevr_loader.exe");
  });
});

// ============================================================================
// xseDllPrefix
// ============================================================================

describe("xseDllPrefix", () => {
  test("returns f4se_ for F4SE", () => {
    expect(xseDllPrefix("F4SE")).toBe("f4se_");
  });

  test("returns skse64_ for SKSE64", () => {
    expect(xseDllPrefix("SKSE64")).toBe("skse64_");
  });

  test("returns sfse_ for SFSE", () => {
    expect(xseDllPrefix("SFSE")).toBe("sfse_");
  });

  test("returns f4sevr_ for F4SEVR", () => {
    expect(xseDllPrefix("F4SEVR")).toBe("f4sevr_");
  });

  test("returns skse_ for SKSE", () => {
    expect(xseDllPrefix("SKSE")).toBe("skse_");
  });

  test("returns sksevr_ for SKSEVR", () => {
    expect(xseDllPrefix("SKSEVR")).toBe("sksevr_");
  });
});

// ============================================================================
// isXseInstalled
// ============================================================================

describe("isXseInstalled", () => {
  test("returns true when loader exists", () => {
    expect(isXseInstalled(MOCK_GAME_DIR, "F4SE")).toBe(true);
  });

  test("returns false for wrong XSE type", () => {
    expect(isXseInstalled(MOCK_GAME_DIR, "SKSE64")).toBe(false);
  });

  test("returns false for empty directory", () => {
    expect(isXseInstalled(EMPTY_GAME_DIR, "F4SE")).toBe(false);
  });

  test("returns false for non-existent directory", () => {
    expect(isXseInstalled(join(TEST_DIR, "nonexistent"), "F4SE")).toBe(false);
  });
});

// ============================================================================
// detectXseVersion
// ============================================================================

describe("detectXseVersion", () => {
  test("detects version from DLL in same directory as loader", () => {
    const loaderPath = join(MOCK_GAME_DIR, "f4se_loader.exe");
    const version = detectXseVersion(loaderPath, "F4SE");
    expect(version).toBe("1.10.163");
  });

  test("returns null when loader does not exist", () => {
    const loaderPath = join(EMPTY_GAME_DIR, "f4se_loader.exe");
    const version = detectXseVersion(loaderPath, "F4SE");
    expect(version).toBeNull();
  });

  test("returns null for wrong XSE type (no matching DLL)", () => {
    const loaderPath = join(MOCK_GAME_DIR, "f4se_loader.exe");
    const version = detectXseVersion(loaderPath, "SKSE64");
    // The loader file exists, but there is no skse64_*.dll, so version detection fails
    expect(version).toBeNull();
  });

  test("returns null for non-existent path", () => {
    const version = detectXseVersion(join(TEST_DIR, "nonexistent", "f4se_loader.exe"), "F4SE");
    expect(version).toBeNull();
  });
});

// ============================================================================
// getXseInfo
// ============================================================================

describe("getXseInfo", () => {
  test("returns full info for installed XSE", () => {
    const info = getXseInfo(MOCK_GAME_DIR, "F4SE");
    expect(info.xseType).toBe("F4SE");
    expect(info.path).toBe(MOCK_GAME_DIR);
    expect(info.installed).toBe(true);
    expect(info.version).toBe("1.10.163");
    expect(info.loaderPath).toContain("f4se_loader.exe");
  });

  test("returns not-installed info for missing XSE", () => {
    const info = getXseInfo(EMPTY_GAME_DIR, "F4SE");
    expect(info.xseType).toBe("F4SE");
    expect(info.installed).toBe(false);
    expect(info.version).toBeUndefined();
  });

  test("returns not-installed info for wrong type", () => {
    const info = getXseInfo(MOCK_GAME_DIR, "SKSE64");
    expect(info.xseType).toBe("SKSE64");
    expect(info.installed).toBe(false);
    expect(info.version).toBeUndefined();
  });

  test("loader_path contains expected executable name", () => {
    const info = getXseInfo(MOCK_GAME_DIR, "SFSE");
    expect(info.loaderPath).toContain("sfse_loader.exe");
  });

  test("returns info for non-existent directory", () => {
    const info = getXseInfo(join(TEST_DIR, "nonexistent"), "F4SE");
    expect(info.installed).toBe(false);
    expect(info.version).toBeUndefined();
  });
});
