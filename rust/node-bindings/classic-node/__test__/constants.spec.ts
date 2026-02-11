import { describe, test, expect } from "bun:test";
import {
  getAllGameIds,
  getAllYamlFiles,
  getAllFallout4Versions,
  getGameName,
  getYamlFileDescription,
  getFallout4VersionInfo,
  JsGameId,
  JsYamlFile,
  JsFallout4Version,
} from "../index.js";

describe("Constants bindings", () => {
  describe("getAllGameIds", () => {
    test("returns exactly 4 game identifiers", () => {
      const ids = getAllGameIds();
      expect(ids).toHaveLength(4);
    });

    test("contains all expected game IDs", () => {
      const ids = getAllGameIds();
      expect(ids).toContain("Fallout4");
      expect(ids).toContain("Fallout4VR");
      expect(ids).toContain("Skyrim");
      expect(ids).toContain("Starfield");
    });
  });

  describe("getAllYamlFiles", () => {
    test("returns exactly 7 YAML file types", () => {
      const files = getAllYamlFiles();
      expect(files).toHaveLength(7);
    });

    test("contains all expected YAML file types", () => {
      const files = getAllYamlFiles();
      expect(files).toContain("Main");
      expect(files).toContain("Settings");
      expect(files).toContain("Ignore");
      expect(files).toContain("Game");
      expect(files).toContain("GameLocal");
      expect(files).toContain("Test");
      expect(files).toContain("Cache");
    });
  });

  describe("getAllFallout4Versions", () => {
    test("returns exactly 4 version variants", () => {
      const versions = getAllFallout4Versions();
      expect(versions).toHaveLength(4);
    });

    test("contains all expected version variants", () => {
      const versions = getAllFallout4Versions();
      expect(versions).toContain("Original");
      expect(versions).toContain("NextGen");
      expect(versions).toContain("AnniversaryEdition");
      expect(versions).toContain("VR");
    });
  });

  describe("getGameName", () => {
    test("returns human-readable name for Fallout4", () => {
      expect(getGameName("Fallout4")).toBe("Fallout 4");
    });

    test("returns human-readable name for Fallout4VR", () => {
      expect(getGameName("Fallout4VR")).toBe("Fallout 4 VR");
    });

    test("returns human-readable name for Skyrim", () => {
      expect(getGameName("Skyrim")).toBe("Skyrim");
    });

    test("returns human-readable name for Starfield", () => {
      expect(getGameName("Starfield")).toBe("Starfield");
    });
  });

  describe("getYamlFileDescription", () => {
    test("returns description containing the file path for Main", () => {
      const desc = getYamlFileDescription("Main");
      expect(desc).toContain("CLASSIC Main.yaml");
    });

    test("returns description for Settings", () => {
      const desc = getYamlFileDescription("Settings");
      expect(desc).toContain("CLASSIC Settings.yaml");
    });
  });

  describe("getFallout4VersionInfo", () => {
    test("returns correct info for Original", () => {
      const info = getFallout4VersionInfo("Original");
      expect(info.name).toBe("Fallout 4 Original");
      expect(info.steamId).toBe(377160);
      expect(info.isVr).toBe(false);
      expect(info.exeName).toBe("Fallout4.exe");
    });

    test("returns correct info for NextGen", () => {
      const info = getFallout4VersionInfo("NextGen");
      expect(info.name).toBe("Fallout 4 Next-Gen");
      expect(info.steamId).toBe(377160);
      expect(info.isVr).toBe(false);
      expect(info.exeName).toBe("Fallout4.exe");
    });

    test("returns correct info for AnniversaryEdition", () => {
      const info = getFallout4VersionInfo("AnniversaryEdition");
      expect(info.name).toBe("Fallout 4 Anniversary Edition");
      expect(info.steamId).toBe(377160);
      expect(info.isVr).toBe(false);
      expect(info.exeName).toBe("Fallout4.exe");
    });

    test("returns correct info for VR", () => {
      const info = getFallout4VersionInfo("VR");
      expect(info.name).toBe("Fallout 4 VR");
      expect(info.steamId).toBe(611660);
      expect(info.isVr).toBe(true);
      expect(info.exeName).toBe("Fallout4VR.exe");
    });
  });
});
