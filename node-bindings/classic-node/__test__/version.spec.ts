import { describe, test, expect } from "bun:test";
import {
  parseVersion,
  tryParseVersion,
  compareVersions,
  isKnownFallout4Version,
  extractVersionFromFilename,
  extractVersionFromLog,
  extractAllVersions,
  formatVersion,
  extractPeVersion,
  isValidPePath,
} from "../index.js";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Version bindings", () => {
  // ── parseVersion ──────────────────────────────────────────────────────

  describe("parseVersion", () => {
    test("parses standard semver string", () => {
      expect(parseVersion("1.10.163")).toBe("1.10.163");
    });

    test("strips v prefix", () => {
      expect(parseVersion("v1.10.163")).toBe("1.10.163");
    });

    test("drops fourth component (build number)", () => {
      expect(parseVersion("1.10.163.0")).toBe("1.10.163");
    });

    test("parses two-part version with implicit patch 0", () => {
      expect(parseVersion("1.10")).toBe("1.10.0");
    });

    test("throws on invalid input", () => {
      expect(() => parseVersion("invalid")).toThrow();
    });

    test("throws on empty string", () => {
      expect(() => parseVersion("")).toThrow();
    });
  });

  // ── tryParseVersion ───────────────────────────────────────────────────

  describe("tryParseVersion", () => {
    test("returns version string on valid input", () => {
      expect(tryParseVersion("1.10.163")).toBe("1.10.163");
    });

    test("returns null on invalid input", () => {
      expect(tryParseVersion("invalid")).toBeNull();
    });

    test("returns null on empty string", () => {
      expect(tryParseVersion("")).toBeNull();
    });
  });

  // ── compareVersions ───────────────────────────────────────────────────

  describe("compareVersions", () => {
    test("returns -1 when a < b", () => {
      expect(compareVersions("1.10.163", "1.10.984")).toBe(-1);
    });

    test("returns 0 when a == b", () => {
      expect(compareVersions("1.10.163", "1.10.163")).toBe(0);
    });

    test("returns 1 when a > b", () => {
      expect(compareVersions("1.10.984", "1.10.163")).toBe(1);
    });

    test("throws when first version is invalid", () => {
      expect(() => compareVersions("invalid", "1.10.163")).toThrow();
    });

    test("throws when second version is invalid", () => {
      expect(() => compareVersions("1.10.163", "invalid")).toThrow();
    });
  });

  // ── isKnownFallout4Version ────────────────────────────────────────────

  describe("isKnownFallout4Version", () => {
    test("returns false for an unknown version", () => {
      expect(isKnownFallout4Version("9.9.9")).toBe(false);
    });

    test("throws on invalid version string", () => {
      expect(() => isKnownFallout4Version("invalid")).toThrow();
    });
  });

  // ── extractVersionFromFilename ────────────────────────────────────────

  describe("extractVersionFromFilename", () => {
    test("extracts version with v prefix", () => {
      expect(extractVersionFromFilename("MyMod-v1.2.3.esp")).toBe("1.2.3");
    });

    test("extracts version with underscore separator", () => {
      expect(extractVersionFromFilename("MyMod_1.2.3.esp")).toBe("1.2.3");
    });

    test("extracts version with four components (drops build)", () => {
      expect(extractVersionFromFilename("MyMod-1.2.3.4-suffix.esp")).toBe(
        "1.2.3",
      );
    });

    test("returns null when no version found", () => {
      expect(extractVersionFromFilename("NoVersion.esp")).toBeNull();
    });
  });

  // ── extractVersionFromLog ─────────────────────────────────────────────

  describe("extractVersionFromLog", () => {
    test("extracts version from log content", () => {
      const log = "F4SE version: 0.6.23\nGame version: 1.10.163";
      expect(extractVersionFromLog(log)).toBe("0.6.23");
    });

    test("returns null when no version found", () => {
      expect(extractVersionFromLog("no version here")).toBeNull();
    });
  });

  // ── extractAllVersions ────────────────────────────────────────────────

  describe("extractAllVersions", () => {
    test("finds all version strings in content", () => {
      const result = extractAllVersions(
        "versions 1.10.163 and 1.10.984",
      );
      expect(result).toEqual(["1.10.163", "1.10.984"]);
    });

    test("returns empty array when no versions found", () => {
      expect(extractAllVersions("no versions here")).toEqual([]);
    });

    test("handles single version", () => {
      expect(extractAllVersions("only 1.2.3 here")).toEqual(["1.2.3"]);
    });
  });

  // ── formatVersion ─────────────────────────────────────────────────────

  describe("formatVersion", () => {
    test("formats a version without prefix", () => {
      expect(formatVersion("1.10.163")).toBe("1.10.163");
    });

    test("normalizes a prefixed version", () => {
      expect(formatVersion("v1.10.163")).toBe("1.10.163");
    });

    test("throws on invalid input", () => {
      expect(() => formatVersion("invalid")).toThrow();
    });
  });

  // ── isValidPePath ────────────────────────────────────────────────────

  describe("isValidPePath", () => {
    test("returns false for non-existent path", () => {
      expect(isValidPePath("/definitely/not/real.exe")).toBe(false);
    });

    test("returns false for wrong extension", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
      const txtPath = join(dir, "readme.txt");
      writeFileSync(txtPath, "not a pe file");
      try {
        expect(isValidPePath(txtPath)).toBe(false);
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });

    test("returns true for .exe file that exists", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
      const exePath = join(dir, "fake.exe");
      writeFileSync(exePath, Buffer.alloc(0));
      try {
        expect(isValidPePath(exePath)).toBe(true);
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });

    test("returns true for .dll file that exists (case-insensitive)", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
      const dllPath = join(dir, "fake.DLL");
      writeFileSync(dllPath, Buffer.alloc(0));
      try {
        expect(isValidPePath(dllPath)).toBe(true);
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });
  });

  // ── extractPeVersion ─────────────────────────────────────────────────

  describe("extractPeVersion", () => {
    test("throws on non-existent path", () => {
      expect(() => extractPeVersion("/definitely/not/real.exe")).toThrow();
    });

    test("throws on bytes that aren't a PE file", () => {
      const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
      const fakeExe = join(dir, "fake.exe");
      writeFileSync(fakeExe, Buffer.from("not a real PE file"));
      try {
        expect(() => extractPeVersion(fakeExe)).toThrow();
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    });

    if (process.platform === "win32") {
      test("extracts version from kernel32.dll (Windows integration)", () => {
        const version = extractPeVersion("C:\\Windows\\System32\\kernel32.dll");
        expect(version.major).toBeGreaterThanOrEqual(6);
        expect(typeof version.minor).toBe("number");
        expect(typeof version.patch).toBe("number");
        expect(typeof version.build).toBe("number");
      });
    }
  });
});
