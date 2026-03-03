import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import {
  JsBa2Scanner,
  JsConfigDuplicateDetector,
  JsEnbChecker,
  JsIniValidator,
  JsGameIntegrityChecker,
  JsLogProcessor,
  JsCrashgenChecker,
  JsUnpackedScanner,
  JsXseChecker,
  JsWryeBashParser,
  checkEnb,
  detectConfigDuplicates,
  scanUnpackedFiles,
  processGameLogs,
  checkCrashgenConfig,
  checkCrashgenFull,
  scanModInis,
  migrateVrSetting,
  resolveEffectiveGameVersion,
  needsPathDetection,
  getAddressLibInfo,
  checkXsePlugins,
} from "../index.js";

// ============================================================================
// Helper: create a temp directory that is cleaned up after each test
// ============================================================================

let tempDir: string;

beforeEach(() => {
  tempDir = mkdtempSync(join(tmpdir(), "classic-scangame-test-"));
});

afterEach(() => {
  rmSync(tempDir, { recursive: true, force: true });
});

// ============================================================================
// BA2 Scanner
// ============================================================================

describe("JsBa2Scanner", () => {
  test("constructor creates instance", () => {
    const scanner = new JsBa2Scanner();
    expect(scanner).toBeDefined();
  });

  test("withXsePatterns factory creates scanner with custom patterns", () => {
    const scanner = JsBa2Scanner.withXsePatterns(["f4se"]);
    expect(scanner).toBeDefined();
  });

  test("findBa2Files returns empty array for directory with no BA2 files", () => {
    const files = new JsBa2Scanner().findBa2Files(tempDir);
    expect(files).toEqual([]);
  });

  test("findBa2Files finds .ba2 files", () => {
    // Create a fake BA2 file (will fail to parse but should be found)
    writeFileSync(join(tempDir, "test.ba2"), "fake ba2 content");
    const files = new JsBa2Scanner().findBa2Files(tempDir);
    expect(files.length).toBe(1);
    expect(files[0]).toContain("test.ba2");
  });

  test("scanArchive throws for non-existent file", () => {
    const scanner = new JsBa2Scanner();
    expect(() => scanner.scanArchive(join(tempDir, "nonexistent.ba2"))).toThrow();
  });

  test("scanArchive throws for invalid BA2 file", () => {
    const fakeBa2 = join(tempDir, "bad.ba2");
    writeFileSync(fakeBa2, "not a real ba2 file");
    expect(() => new JsBa2Scanner().scanArchive(fakeBa2)).toThrow();
  });
});

// ============================================================================
// Config Duplicate Detector
// ============================================================================

describe("JsConfigDuplicateDetector", () => {
  test("constructor creates instance", () => {
    const detector = new JsConfigDuplicateDetector();
    expect(detector).toBeDefined();
  });

  test("withWhitelist factory creates detector with custom whitelist", () => {
    const detector = JsConfigDuplicateDetector.withWhitelist(["F4EE", "custom"]);
    expect(detector).toBeDefined();
  });

  test("detectDuplicates returns empty array for empty directory", () => {
    const detector = new JsConfigDuplicateDetector();
    const result = detector.detectDuplicates(tempDir);
    expect(result).toEqual([]);
  });

  test("getDuplicateMap returns empty object for empty directory", () => {
    const detector = new JsConfigDuplicateDetector();
    const result = detector.getDuplicateMap(tempDir);
    expect(Object.keys(result).length).toBe(0);
  });
});

describe("detectConfigDuplicates convenience function", () => {
  test("returns empty array for empty directory", () => {
    const result = detectConfigDuplicates(tempDir);
    expect(result).toEqual([]);
  });
});

// ============================================================================
// ENB Checker
// ============================================================================

describe("JsEnbChecker", () => {
  test("constructor creates instance", () => {
    const checker = new JsEnbChecker(tempDir);
    expect(checker).toBeDefined();
  });

  test("checkBinaries returns NotInstalled for empty directory", () => {
    const checker = new JsEnbChecker(tempDir);
    expect(checker.checkBinaries()).toBe("NotInstalled");
  });

  test("checkConfig returns NotFound for empty directory", () => {
    const checker = new JsEnbChecker(tempDir);
    expect(checker.checkConfig()).toBe("NotFound");
  });

  test("validate returns not-installed state for empty directory", () => {
    const checker = new JsEnbChecker(tempDir);
    const result = checker.validate();

    expect(result.binaries).toBe("NotInstalled");
    expect(result.config).toBe("NotFound");
    expect(result.isPresent).toBe(false);
    expect(result.isFullyConfigured).toBe(false);
  });

  test("checkBinaries returns Present when both DLLs exist", () => {
    writeFileSync(join(tempDir, "d3d11.dll"), "fake");
    writeFileSync(join(tempDir, "d3dcompiler_46e.dll"), "fake");

    const checker = new JsEnbChecker(tempDir);
    expect(checker.checkBinaries()).toBe("Present");
  });

  test("checkBinaries returns Partial when only d3d11.dll exists", () => {
    writeFileSync(join(tempDir, "d3d11.dll"), "fake");

    const checker = new JsEnbChecker(tempDir);
    expect(checker.checkBinaries()).toBe("Partial");
  });

  test("validate returns fully configured when all files present", () => {
    writeFileSync(join(tempDir, "d3d11.dll"), "fake");
    writeFileSync(join(tempDir, "d3dcompiler_46e.dll"), "fake");
    writeFileSync(join(tempDir, "enbseries.ini"), "[GLOBAL]\n");

    const checker = new JsEnbChecker(tempDir);
    const result = checker.validate();

    expect(result.binaries).toBe("Present");
    expect(result.config).toBe("Valid");
    expect(result.isPresent).toBe(true);
    expect(result.isFullyConfigured).toBe(true);
  });

  test("formatMessage returns string for empty directory", () => {
    const checker = new JsEnbChecker(tempDir);
    const message = checker.formatMessage();
    expect(message).toContain("ENB is not installed");
  });

  test("formatMessage returns installed message when ENB present", () => {
    writeFileSync(join(tempDir, "d3d11.dll"), "fake");
    writeFileSync(join(tempDir, "d3dcompiler_46e.dll"), "fake");
    writeFileSync(join(tempDir, "enbseries.ini"), "[GLOBAL]\n");

    const checker = new JsEnbChecker(tempDir);
    const message = checker.formatMessage();
    expect(message).toContain("ENB is installed and configured");
  });
});

describe("checkEnb convenience function", () => {
  test("returns validation result for empty directory", () => {
    const result = checkEnb(tempDir);
    expect(result.binaries).toBe("NotInstalled");
    expect(result.isPresent).toBe(false);
  });
});

// ============================================================================
// INI Validator
// ============================================================================

describe("JsIniValidator", () => {
  test("constructor creates instance", () => {
    const validator = new JsIniValidator("Fallout4");
    expect(validator).toBeDefined();
  });

  test("validateInis returns empty report for empty directory", () => {
    const validator = new JsIniValidator("Fallout4");
    const report = validator.validateInis(tempDir);
    expect(typeof report).toBe("string");
  });

  test("detectAllIssues returns empty array for empty config map", () => {
    const validator = new JsIniValidator("Fallout4");
    const issues = validator.detectAllIssues({});
    expect(issues).toEqual([]);
  });

  test("scanConfigFiles returns map of found INI files", () => {
    writeFileSync(join(tempDir, "test.ini"), "[Section]\nkey=value\n");
    writeFileSync(join(tempDir, "other.conf"), "setting=true\n");

    const validator = new JsIniValidator("Fallout4");
    const files = validator.scanConfigFiles(tempDir);

    expect(typeof files).toBe("object");
    // Should find at least the .ini file
    expect(Object.keys(files).some((k) => k.endsWith(".ini"))).toBe(true);
  });

  test("detectAllIssues detects EPO particle count issue", () => {
    const epoPath = join(tempDir, "epo.ini");
    writeFileSync(epoPath, "[Particles]\niMaxDesired=10000\n");

    const validator = new JsIniValidator("Fallout4");
    // Load the INI first via validateInis which caches files
    validator.validateInis(tempDir);
    const issues = validator.detectAllIssues({ "epo.ini": epoPath });

    expect(issues.length).toBeGreaterThanOrEqual(1);
    const epoIssue = issues.find((i) => i.setting === "iMaxDesired");
    expect(epoIssue).toBeDefined();
    expect(epoIssue!.recommendedValue).toBe("5000");
    expect(epoIssue!.severity).toBe("Warning");
  });
});

// ============================================================================
// Integrity Checker
// ============================================================================

describe("JsGameIntegrityChecker", () => {
  test("constructor creates instance with config", () => {
    const checker = new JsGameIntegrityChecker({
      gameExePath: join(tempDir, "game.exe"),
      validExeHashes: ["hash1", "hash2"],
      rootName: "Test Game",
    });
    expect(checker).toBeDefined();
  });

  test("checkInstallationLocation passes for temp directory path", () => {
    // Create a fake exe in the temp directory (not in Program Files)
    const exePath = join(tempDir, "game.exe");
    writeFileSync(exePath, "fake executable content");

    const checker = new JsGameIntegrityChecker({
      gameExePath: exePath,
      validExeHashes: ["hash1"],
      rootName: "Test Game",
    });

    const result = checker.checkInstallationLocation();
    expect(result.isValid).toBe(true);
    expect(result.checkType).toBe("InstallationLocation");
    expect(result.message).toContain("outside of the Program Files folder");
  });

  test("checkExecutableVersion returns result for missing exe", () => {
    const checker = new JsGameIntegrityChecker({
      gameExePath: join(tempDir, "nonexistent.exe"),
      validExeHashes: ["hash1"],
      rootName: "Test Game",
    });

    const result = checker.checkExecutableVersion();
    expect(result.isValid).toBe(false);
    expect(result.checkType).toBe("ExecutableVersion");
    expect(result.message).toContain("not found");
  });

  test("runAllChecks returns array of results", () => {
    const exePath = join(tempDir, "game.exe");
    writeFileSync(exePath, "fake executable");

    const checker = new JsGameIntegrityChecker({
      gameExePath: exePath,
      validExeHashes: [],
      rootName: "Test Game",
    });

    const results = checker.runAllChecks();
    expect(results.length).toBe(2); // ExecutableVersion + InstallationLocation
  });

  test("runFullCheck returns combined message string", () => {
    const exePath = join(tempDir, "game.exe");
    writeFileSync(exePath, "fake executable");

    const checker = new JsGameIntegrityChecker({
      gameExePath: exePath,
      validExeHashes: [],
      rootName: "Test Game",
    });

    const message = checker.runFullCheck();
    expect(typeof message).toBe("string");
    expect(message.length).toBeGreaterThan(0);
  });

  test("config accepts optional steamIniPath and rootWarn", () => {
    const exePath = join(tempDir, "game.exe");
    writeFileSync(exePath, "fake");

    const checker = new JsGameIntegrityChecker({
      gameExePath: exePath,
      validExeHashes: ["hash1"],
      rootName: "Test Game",
      steamIniPath: join(tempDir, "steam_api.ini"),
      rootWarn: "Warning: Program Files detected",
    });

    expect(checker).toBeDefined();
  });

  test("config with undefined optional fields works", () => {
    const checker = new JsGameIntegrityChecker({
      gameExePath: join(tempDir, "game.exe"),
      validExeHashes: [],
      rootName: "Test Game",
      steamIniPath: undefined,
      rootWarn: undefined,
    });

    expect(checker).toBeDefined();
  });
});

// ============================================================================
// Log Processor
// ============================================================================

describe("JsLogProcessor", () => {
  test("constructor creates instance with patterns", () => {
    const processor = new JsLogProcessor(["error"], ["crash-"], ["warning"]);
    expect(processor).toBeDefined();
  });

  test("errorPatterns returns configured patterns", () => {
    const processor = new JsLogProcessor(["error", "fatal"], [], []);
    const patterns = processor.errorPatterns();
    expect(patterns).toEqual(["error", "fatal"]);
  });

  test("processLogs returns empty string for directory with no log files", () => {
    const processor = new JsLogProcessor(["error"], [], []);
    const report = processor.processLogs(tempDir);
    expect(report).toBe("");
  });

  test("processLogs detects errors in log files", () => {
    writeFileSync(
      join(tempDir, "test.log"),
      "INFO: Starting\nERROR: Something failed\nINFO: Done\n"
    );

    const processor = new JsLogProcessor(["error"], [], []);
    const report = processor.processLogs(tempDir);

    expect(report).toContain("ERROR > ERROR: Something failed");
    expect(report).toContain("TOTAL NUMBER OF DETECTED LOG ERRORS");
  });

  test("processLogs excludes crash log files", () => {
    writeFileSync(
      join(tempDir, "crash-2024.log"),
      "ERROR: Critical crash\n"
    );

    const processor = new JsLogProcessor(["error"], [], []);
    const report = processor.processLogs(tempDir);
    expect(report).toBe("");
  });

  test("processLogs applies error exclusion patterns", () => {
    writeFileSync(
      join(tempDir, "test.log"),
      "ERROR: Should catch this\nERROR: Warning - should ignore this\n"
    );

    const processor = new JsLogProcessor(["error"], [], ["warning"]);
    const report = processor.processLogs(tempDir);

    expect(report).toContain("Should catch this");
    expect(report).not.toContain("Warning - should ignore this");
  });

  test("processLogs throws for non-existent directory", () => {
    const processor = new JsLogProcessor(["error"], [], []);
    expect(() =>
      processor.processLogs(join(tempDir, "nonexistent"))
    ).toThrow();
  });
});

describe("processGameLogs convenience function", () => {
  test("returns empty string for empty directory", () => {
    const report = processGameLogs(tempDir, ["error"], [], []);
    expect(report).toBe("");
  });
});

// ============================================================================
// Crashgen / TOML Checker
// ============================================================================

describe("JsCrashgenChecker", () => {
  test("constructor creates instance", () => {
    const checker = new JsCrashgenChecker(tempDir, "Buffout4");
    expect(checker).toBeDefined();
  });

  test("check returns report when no config file exists", () => {
    const checker = new JsCrashgenChecker(tempDir, "Buffout4");
    const result = checker.check();

    expect(typeof result.report).toBe("string");
    // Should mention unable to find the config file
    expect(result.report).toContain("Unable to find");
    expect(result.issues.length).toBe(0);
  });

  test("check detects plugin conflicts", () => {
    // Create Buffout4 config directory with config.toml
    const buffoutDir = join(tempDir, "Buffout4");
    mkdirSync(buffoutDir);
    writeFileSync(
      join(buffoutDir, "config.toml"),
      "[Patches]\nAchievements = true\n"
    );

    // Create achievements.dll to trigger condition
    writeFileSync(join(tempDir, "achievements.dll"), "");

    const checker = new JsCrashgenChecker(tempDir, "Buffout4");
    const result = checker.check();

    expect(result.issues.length).toBeGreaterThanOrEqual(1);
    const achievementIssue = result.issues.find(
      (i) => i.setting === "Achievements"
    );
    expect(achievementIssue).toBeDefined();
    expect(achievementIssue!.severity).toBe("Warning");
  });
});

describe("checkCrashgenConfig convenience function", () => {
  test("returns report for empty directory", () => {
    const result = checkCrashgenConfig(tempDir, "Buffout4");
    expect(typeof result.report).toBe("string");
    expect(result.issues).toEqual([]);
  });
});

// ============================================================================
// Unpacked Scanner
// ============================================================================

describe("JsUnpackedScanner", () => {
  test("constructor creates instance", () => {
    const scanner = new JsUnpackedScanner();
    expect(scanner).toBeDefined();
  });

  test("scanDirectory returns empty issues for empty directory", () => {
    const scanner = new JsUnpackedScanner();
    const issues = scanner.scanDirectory(tempDir, []);

    expect(issues.animdata).toEqual([]);
    expect(issues.texFrmt).toEqual([]);
    expect(issues.sndFrmt).toEqual([]);
    expect(issues.xseFile).toEqual([]);
    expect(issues.previs).toEqual([]);
    expect(issues.ddsFiles).toEqual([]);
  });

  test("scanDirectory detects TGA texture files", () => {
    writeFileSync(join(tempDir, "texture.tga"), "fake tga data");

    const scanner = new JsUnpackedScanner();
    const issues = scanner.scanDirectory(tempDir, []);

    expect(issues.texFrmt.length).toBeGreaterThanOrEqual(1);
  });

  test("scanDirectory detects MP3 sound files", () => {
    writeFileSync(join(tempDir, "sound.mp3"), "fake mp3 data");

    const scanner = new JsUnpackedScanner();
    const issues = scanner.scanDirectory(tempDir, []);

    expect(issues.sndFrmt.length).toBeGreaterThanOrEqual(1);
  });

  test("scanDirectory collects DDS files", () => {
    writeFileSync(join(tempDir, "texture.dds"), "fake dds data");

    const scanner = new JsUnpackedScanner();
    const issues = scanner.scanDirectory(tempDir, []);

    expect(issues.ddsFiles.length).toBe(1);
  });

  test("scanDirectory throws for non-existent directory", () => {
    const scanner = new JsUnpackedScanner();
    expect(() =>
      scanner.scanDirectory(join(tempDir, "nonexistent"), [])
    ).toThrow();
  });

  test("scanDirectory excludes BodySlide TGA files", () => {
    const bodySlideDir = join(tempDir, "BodySlide");
    mkdirSync(bodySlideDir);
    writeFileSync(join(bodySlideDir, "texture.tga"), "fake");

    const scanner = new JsUnpackedScanner();
    const issues = scanner.scanDirectory(tempDir, []);

    // TGA in BodySlide should be excluded
    expect(issues.texFrmt.length).toBe(0);
  });
});

describe("scanUnpackedFiles convenience function", () => {
  test("returns issues for directory with problems", () => {
    writeFileSync(join(tempDir, "test.mp3"), "fake");

    const issues = scanUnpackedFiles(tempDir, []);
    expect(issues.sndFrmt.length).toBeGreaterThanOrEqual(1);
  });
});

// ============================================================================
// XSE Checker
// ============================================================================

describe("JsXseChecker", () => {
  test("constructor creates instance with default options", () => {
    const checker = new JsXseChecker(tempDir);
    expect(checker).toBeDefined();
  });

  test("constructor creates instance with VR version", () => {
    const checker = new JsXseChecker(tempDir, "Vr");
    expect(checker).toBeDefined();
  });

  test("constructor throws for non-existent path", () => {
    expect(
      () => new JsXseChecker(join(tempDir, "nonexistent"))
    ).toThrow();
  });

  test("check returns NotFound for empty plugins directory", () => {
    const checker = new JsXseChecker(tempDir, "Original");
    const result = checker.check();
    expect(result).toBe("NotFound");
  });

  test("check returns VersionNotDetected for Null version", () => {
    const checker = new JsXseChecker(tempDir, "Null");
    const result = checker.check();
    expect(result).toBe("VersionNotDetected");
  });

  test("check returns CorrectVersion when OG address lib exists (non-VR)", () => {
    writeFileSync(join(tempDir, "version-1-10-163-0.bin"), "fake");
    const checker = new JsXseChecker(tempDir, "Original");
    const result = checker.check();
    expect(result).toBe("CorrectVersion");
  });

  test("check returns WrongVersion when VR lib exists in non-VR mode", () => {
    writeFileSync(join(tempDir, "version-1-2-72-0.csv"), "fake");
    const checker = new JsXseChecker(tempDir, "Original");
    const result = checker.check();
    expect(result).toBe("WrongVersion");
  });

  test("check returns CorrectVersion for VR lib in VR mode", () => {
    writeFileSync(join(tempDir, "version-1-2-72-0.csv"), "fake");
    const checker = new JsXseChecker(tempDir, "Vr");
    const result = checker.check();
    expect(result).toBe("CorrectVersion");
  });

  test("validate returns formatted message string", () => {
    const checker = new JsXseChecker(tempDir, "Original");
    const message = checker.validate();
    expect(typeof message).toBe("string");
    expect(message.length).toBeGreaterThan(0);
    // No address lib found, should mention "not found"
    expect(message).toContain("not found");
  });

  test("validate returns correct version message", () => {
    writeFileSync(join(tempDir, "version-1-10-163-0.bin"), "fake");
    const checker = new JsXseChecker(tempDir, "Original");
    const message = checker.validate();
    expect(message).toContain("correct version");
  });
});

describe("getAddressLibInfo", () => {
  test("returns info for Original version", () => {
    const info = getAddressLibInfo("Original");
    expect(info.version).toBe("Original");
    expect(info.filename).toBe("version-1-10-163-0.bin");
    expect(info.url).toBeTruthy();
    expect(info.description).toBeTruthy();
  });

  test("returns info for VR version", () => {
    const info = getAddressLibInfo("Vr");
    expect(info.filename).toBe("version-1-2-72-0.csv");
  });

  test("returns info for NextGen version", () => {
    const info = getAddressLibInfo("NextGen");
    expect(info.filename).toBe("version-1-10-984-0.bin");
  });

  test("returns info for AnniversaryEdition version", () => {
    const info = getAddressLibInfo("AnniversaryEdition");
    expect(info.filename).toBe("version-1-11-191-0.bin");
  });

  test("returns info for AE alias", () => {
    const info = getAddressLibInfo("AE");
    expect(info.filename).toBe("version-1-11-191-0.bin");
  });

  test("returns Original info for unknown version string", () => {
    const info = getAddressLibInfo("UnknownVersion");
    // Falls back to Original
    expect(info.filename).toBe("version-1-10-163-0.bin");
  });
});

describe("checkXsePlugins convenience function", () => {
  test("returns formatted message for empty directory", () => {
    const message = checkXsePlugins(tempDir, "Original");
    expect(typeof message).toBe("string");
    expect(message).toContain("not found");
  });

  test("throws for non-existent path", () => {
    expect(() =>
      checkXsePlugins(join(tempDir, "nonexistent"), "Original")
    ).toThrow();
  });
});

// ============================================================================
// Crashgen Full Check Orchestrator
// ============================================================================

describe("checkCrashgenFull", () => {
  test("returns report for empty plugins directory", () => {
    const report = checkCrashgenFull(tempDir, "Buffout4");

    expect(typeof report.message).toBe("string");
    expect(report.crashgenName).toBe("Buffout4");
    expect(report.message).toContain("Unable to find");
    expect(report.issues).toEqual([]);
  });

  test("detects achievements plugin conflict", () => {
    const buffoutDir = join(tempDir, "Buffout4");
    mkdirSync(buffoutDir);
    writeFileSync(
      join(buffoutDir, "config.toml"),
      "[Patches]\nAchievements = true\n"
    );
    writeFileSync(join(tempDir, "achievements.dll"), "");

    const report = checkCrashgenFull(tempDir, "Buffout4");

    expect(report.configPath).toBeTruthy();
    expect(report.issues.length).toBeGreaterThanOrEqual(1);
    expect(report.issues.some((i) => i.setting === "Achievements")).toBe(true);
    expect(report.installedPlugins.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Wrye Bash Parser
// ============================================================================

describe("JsWryeBashParser", () => {
  test("constructor creates instance", () => {
    const parser = new JsWryeBashParser({});
    expect(parser).toBeDefined();
  });

  test("parse returns empty array for empty HTML", () => {
    const parser = new JsWryeBashParser({});
    const issues = parser.parse("");
    expect(issues).toEqual([]);
  });

  test("parse extracts h3 sections from HTML", () => {
    const parser = new JsWryeBashParser({});
    const html = `<html><body>
      <h3>Missing Masters</h3>
      <p>\u2022\u00a0 ArmorKeywords.esm</p>
      <p>\u2022\u00a0 AWKCR.esp</p>
      <h3>ESL Capable</h3>
      <p>\u2022\u00a0 SmallMod.esp</p>
      <h3>Active Plugins:</h3>
      <p>\u2022\u00a0 Fallout4.esm</p>
    </body></html>`;

    const issues = parser.parse(html);

    // Active Plugins is skipped, so 2 sections
    expect(issues.length).toBe(2);
    expect(issues[0].sectionTitle).toBe("Missing Masters");
    expect(issues[0].plugins.length).toBe(2);
    expect(issues[1].sectionTitle).toBe("ESL Capable");
    expect(issues[1].plugins.length).toBe(1);
  });

  test("parse applies warning messages", () => {
    const parser = new JsWryeBashParser({
      "Missing Masters": "  WARNING: Fix your load order!\n",
    });
    const html =
      '<html><body><h3>Missing Masters</h3><p>\u2022\u00a0 Mod.esp</p></body></html>';

    const issues = parser.parse(html);

    expect(issues.length).toBe(1);
    expect(issues[0].warningMessage).toBe(
      "  WARNING: Fix your load order!\n"
    );
    expect(issues[0].severity).toBe("Warning");
  });

  test("formatReport produces formatted string", () => {
    const issues = [
      {
        sectionTitle: "Missing Masters",
        plugins: ["AWKCR.esp"],
        warningMessage: "  Fix your load order!\n",
        severity: "Warning",
      },
    ];

    const report = JsWryeBashParser.formatReport(issues);

    expect(report).toContain("Missing Masters");
    expect(report).toContain("> AWKCR.esp");
    expect(report).toContain("Fix your load order!");
  });

  test("formatReport handles ESL Capable section", () => {
    const issues = [
      {
        sectionTitle: "ESL Capable",
        plugins: ["SmallMod.esp", "TinyPatch.esl"],
        warningMessage: undefined,
        severity: "Info",
      },
    ];

    const report = JsWryeBashParser.formatReport(issues);

    expect(report).toContain("2 plugins");
    expect(report).toContain("SimpleESLify");
    // ESL Capable section should NOT list individual plugins
    expect(report).not.toContain("> SmallMod.esp");
  });

  test("formatReport returns empty string for no issues", () => {
    const report = JsWryeBashParser.formatReport([]);
    expect(report).toBe("");
  });
});

// ============================================================================
// Mod INI Scanner
// ============================================================================

describe("scanModInis", () => {
  test("returns empty result for empty directory", () => {
    const result = scanModInis(tempDir, "Fallout4");

    expect(result.message).toBe("");
    expect(result.issues).toEqual([]);
    expect(result.vsyncFiles).toEqual([]);
    expect(result.duplicates).toEqual([]);
  });

  test("throws for non-existent game root", () => {
    expect(() =>
      scanModInis(join(tempDir, "nonexistent"), "Fallout4")
    ).toThrow();
  });

  test("detects EPO particle count issue", () => {
    writeFileSync(
      join(tempDir, "epo.ini"),
      "[Particles]\niMaxDesired=10000\n"
    );

    const result = scanModInis(tempDir, "Fallout4");

    expect(result.issues.length).toBeGreaterThanOrEqual(1);
    const epoIssue = result.issues.find((i) => i.setting === "iMaxDesired");
    expect(epoIssue).toBeDefined();
    expect(epoIssue!.recommendedValue).toBe("5000");
  });

  test("detects VSync settings", () => {
    writeFileSync(
      join(tempDir, "enblocal.ini"),
      "[ENGINE]\nForceVSync=true\n"
    );

    const result = scanModInis(tempDir, "Fallout4");

    expect(result.vsyncFiles.length).toBe(1);
    expect(result.vsyncFiles[0].setting).toBe("ForceVSync");
    expect(result.message).toContain("VSYNC");
  });
});

// ============================================================================
// VR Setting Migration
// ============================================================================

describe("migrateVrSetting", () => {
  test("preserves explicit original mode", () => {
    const result = migrateVrSetting("Original");
    expect(result).toBe("Original");
  });

  test("returns null when no setting is provided", () => {
    const result = migrateVrSetting(null);
    expect(result).toBeNull();
  });

  test("preserves auto mode", () => {
    const result = migrateVrSetting("auto");
    expect(result).toBe("auto");
  });

  test("normalizes AE alias to AnniversaryEdition", () => {
    const result = migrateVrSetting("AE");
    expect(result).toBe("AnniversaryEdition");
  });
});

// ============================================================================
// Game Version Resolution
// ============================================================================

describe("resolveEffectiveGameVersion", () => {
  test("returns VR for VR", () => {
    expect(resolveEffectiveGameVersion("VR")).toBe("VR");
  });

  test("returns Original for Original", () => {
    expect(resolveEffectiveGameVersion("Original")).toBe("Original");
  });

  test("returns NextGen for NextGen", () => {
    expect(resolveEffectiveGameVersion("NextGen")).toBe("NextGen");
  });

  test("returns AnniversaryEdition for AE alias", () => {
    expect(resolveEffectiveGameVersion("AE")).toBe("AnniversaryEdition");
  });

  test("returns auto for unknown value", () => {
    expect(resolveEffectiveGameVersion("invalid")).toBe("auto");
  });

  test("returns auto for null", () => {
    expect(resolveEffectiveGameVersion(null)).toBe("auto");
  });

  test("returns auto for auto", () => {
    expect(resolveEffectiveGameVersion("auto")).toBe("auto");
  });
});

// ============================================================================
// Path Detection
// ============================================================================

describe("needsPathDetection", () => {
  test("both missing (null) returns both true", () => {
    const result = needsPathDetection(null, null);
    expect(result.needsGamePath).toBe(true);
    expect(result.needsDocsPath).toBe(true);
  });

  test("game path set returns only docs needed", () => {
    const result = needsPathDetection("C:\\Games\\Fallout4", null);
    expect(result.needsGamePath).toBe(false);
    expect(result.needsDocsPath).toBe(true);
  });

  test("both set returns both false", () => {
    const result = needsPathDetection("C:\\Games", "C:\\Docs");
    expect(result.needsGamePath).toBe(false);
    expect(result.needsDocsPath).toBe(false);
  });

  test("empty strings treated as missing", () => {
    const result = needsPathDetection("", "");
    expect(result.needsGamePath).toBe(true);
    expect(result.needsDocsPath).toBe(true);
  });

  test("docs path set returns only game needed", () => {
    const result = needsPathDetection(null, "C:\\Docs");
    expect(result.needsGamePath).toBe(true);
    expect(result.needsDocsPath).toBe(false);
  });
});
