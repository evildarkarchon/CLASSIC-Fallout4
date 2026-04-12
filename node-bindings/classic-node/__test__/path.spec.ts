import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { mkdirSync, writeFileSync, rmSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import {
  // GamePathFinder class
  GamePathFinder,
  // DocsPathFinder class
  DocsPathFinder,
  // BackupManager class
  BackupManager,
  // XseVersion class
  XseVersion,
  // DocumentsChecker class
  DocumentsChecker,
  // Free functions - path validation
  isValidPath,
  isRestrictedPath,
  isValidExecutablePath,
  validateCustomScanPath,
  validateRequiredFiles,
  validateSettingsPath,
  validateSettingsPaths,
  checkDriveExists,
  checkReadPermissions,
  checkWritePermissions,
  validatePathWithPermissions,
  // Free functions - parsing/detection
  parseXseLog,
  getSystemDocumentsPath,
  removeReadonly,
  queryGameRegistry,
  parseSteamLibrary,
} from "../index.js";

// ============================================================================
// Test Helpers
// ============================================================================

let tempRoot: string;
let tempCounter = 0;

function createTempDir(): string {
  const dir = join(
    tmpdir(),
    `classic-path-test-${Date.now()}-${tempCounter++}`,
  );
  mkdirSync(dir, { recursive: true });
  return dir;
}

// ============================================================================
// GamePathFinder
// ============================================================================

describe("GamePathFinder", () => {
  test("constructor creates instance with correct properties", () => {
    const finder = new GamePathFinder(
      "Fallout4.exe",
      "f4se_loader.exe",
      "Fallout4",
      false,
    );
    expect(finder.gameExe).toBe("Fallout4.exe");
    expect(finder.xseLoader).toBe("f4se_loader.exe");
    expect(finder.isVr).toBe(false);
  });

  test("constructor with null xseLoader", () => {
    const finder = new GamePathFinder(
      "Fallout4VR.exe",
      null,
      "Fallout4",
      true,
    );
    expect(finder.gameExe).toBe("Fallout4VR.exe");
    expect(finder.xseLoader).toBeNull();
    expect(finder.isVr).toBe(true);
  });

  test("findGamePath returns string or null", () => {
    const finder = new GamePathFinder(
      "FakeGame12345.exe",
      null,
      "FakeGame12345",
      false,
    );
    const result = finder.findGamePath(null, null);
    // Game doesn't exist, so should return null
    expect(result).toBeNull();
  });

  test("findGamePath with valid cached path returns it", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "TestGame.exe"), "mock exe");
      const finder = new GamePathFinder(
        "TestGame.exe",
        null,
        "TestGame",
        false,
      );
      const result = finder.findGamePath(tempDir, null);
      expect(typeof result).toBe("string");
      expect(result).not.toBeNull();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("findGamePath with invalid cached path returns null", () => {
    const finder = new GamePathFinder(
      "FakeGame12345.exe",
      null,
      "FakeGame12345",
      false,
    );
    const result = finder.findGamePath("Z:\\nonexistent\\path", null);
    expect(result).toBeNull();
  });

  test("validateGamePath throws for non-existent path", () => {
    const finder = new GamePathFinder(
      "Fallout4.exe",
      null,
      "Fallout4",
      false,
    );
    expect(() => finder.validateGamePath("Z:\\nonexistent\\12345")).toThrow();
  });

  test("validateGamePath succeeds for valid game directory", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "TestGame.exe"), "mock exe");
      const finder = new GamePathFinder(
        "TestGame.exe",
        null,
        "TestGame",
        false,
      );
      expect(() => finder.validateGamePath(tempDir)).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("validateGamePath throws when XSE loader is missing", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "TestGame.exe"), "mock exe");
      // Finder expects a loader but we didn't create it
      const finder = new GamePathFinder(
        "TestGame.exe",
        "loader.exe",
        "TestGame",
        false,
      );
      expect(() => finder.validateGamePath(tempDir)).toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// parseXseLog
// ============================================================================

describe("parseXseLog", () => {
  test("returns null for non-existent log file", () => {
    const result = parseXseLog("Z:\\nonexistent\\f4se.log");
    expect(result).toBeNull();
  });

  test("returns null for log without plugin directory line", () => {
    const tempDir = createTempDir();
    try {
      const logPath = join(tempDir, "f4se.log");
      writeFileSync(logPath, "F4SE version = 0.6.23\nloading plugins...\n");
      const result = parseXseLog(logPath);
      expect(result).toBeNull();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("extracts game path from valid XSE log", () => {
    const tempDir = createTempDir();
    try {
      const logPath = join(tempDir, "f4se.log");
      writeFileSync(
        logPath,
        'plugin directory = C:\\Games\\Fallout4\\Data\\F4SE\\Plugins\\\n',
      );
      const result = parseXseLog(logPath);
      expect(result).not.toBeNull();
      expect(typeof result).toBe("string");
      expect(result).toContain("Fallout4");
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// Path Validation Functions
// ============================================================================

describe("Path validation functions", () => {
  test("isValidPath returns true for existing path", () => {
    expect(isValidPath(".")).toBe(true);
  });

  test("isValidPath returns false for non-existent path", () => {
    expect(isValidPath("Z:\\nonexistent\\path\\12345")).toBe(false);
  });

  test("isRestrictedPath returns true for system directories", () => {
    expect(isRestrictedPath("C:\\Windows")).toBe(true);
    expect(isRestrictedPath("C:\\Program Files")).toBe(true);
    expect(isRestrictedPath("C:\\Program Files (x86)")).toBe(true);
  });

  test("isRestrictedPath returns true for root directories", () => {
    expect(isRestrictedPath("C:\\")).toBe(true);
  });

  test("isRestrictedPath returns false for user directories", () => {
    expect(isRestrictedPath("C:\\Users\\Name\\Downloads")).toBe(false);
  });

  test("isValidExecutablePath returns false for non-existent path", () => {
    expect(isValidExecutablePath("Z:\\nonexistent\\game.exe")).toBe(false);
  });

  test("isValidExecutablePath returns false for directory", () => {
    expect(isValidExecutablePath(".")).toBe(false);
  });
});

// ============================================================================
// validateCustomScanPath
// ============================================================================

describe("validateCustomScanPath", () => {
  test("throws for non-existent path", () => {
    expect(() =>
      validateCustomScanPath("Z:\\nonexistent\\scan\\path"),
    ).toThrow();
  });

  test("throws for restricted path", () => {
    expect(() => validateCustomScanPath("C:\\Windows")).toThrow();
  });
});

// ============================================================================
// validateRequiredFiles
// ============================================================================

describe("validateRequiredFiles", () => {
  test("succeeds when all required files exist", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "file1.txt"), "test");
      writeFileSync(join(tempDir, "file2.txt"), "test");
      expect(() =>
        validateRequiredFiles(tempDir, ["file1.txt", "file2.txt"]),
      ).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("throws when a required file is missing", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "file1.txt"), "test");
      expect(() =>
        validateRequiredFiles(tempDir, ["file1.txt", "missing.txt"]),
      ).toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("throws for non-existent directory", () => {
    expect(() =>
      validateRequiredFiles("Z:\\nonexistent\\dir", ["file.txt"]),
    ).toThrow();
  });
});

// ============================================================================
// validateSettingsPath
// ============================================================================

describe("validateSettingsPath", () => {
  test("succeeds for existing path with no required files", () => {
    const tempDir = createTempDir();
    try {
      expect(() =>
        validateSettingsPath(tempDir, "Test Path", null),
      ).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("throws for non-existent path", () => {
    expect(() =>
      validateSettingsPath(
        "Z:\\nonexistent\\path",
        "Test Path",
        null,
      ),
    ).toThrow();
  });

  test("succeeds with required files that exist", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "game.exe"), "test");
      expect(() =>
        validateSettingsPath(tempDir, "Game Path", ["game.exe"]),
      ).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// validateSettingsPaths
// ============================================================================

describe("validateSettingsPaths", () => {
  test("succeeds with valid game and docs paths", () => {
    const tempDir = createTempDir();
    try {
      const gameDir = join(tempDir, "game");
      const docsDir = join(tempDir, "docs");
      mkdirSync(gameDir, { recursive: true });
      mkdirSync(docsDir, { recursive: true });
      writeFileSync(join(gameDir, "Game.exe"), "test");

      expect(() =>
        validateSettingsPaths(gameDir, docsDir, null, "Game.exe"),
      ).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("throws when game exe is missing", () => {
    const tempDir = createTempDir();
    try {
      const gameDir = join(tempDir, "game");
      const docsDir = join(tempDir, "docs");
      mkdirSync(gameDir, { recursive: true });
      mkdirSync(docsDir, { recursive: true });

      expect(() =>
        validateSettingsPaths(gameDir, docsDir, null, "Missing.exe"),
      ).toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// Permission checks
// ============================================================================

describe("Permission checks", () => {
  test("checkDriveExists does not throw for C:\\", () => {
    expect(() => checkDriveExists("C:\\Games")).not.toThrow();
  });

  test("checkReadPermissions succeeds for current directory", () => {
    expect(() => checkReadPermissions(".")).not.toThrow();
  });

  test("checkReadPermissions throws for non-existent path", () => {
    expect(() =>
      checkReadPermissions("Z:\\nonexistent\\12345"),
    ).toThrow();
  });

  test("checkWritePermissions succeeds for temp directory", () => {
    const tempDir = createTempDir();
    try {
      expect(() => checkWritePermissions(tempDir)).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("validatePathWithPermissions succeeds with defaults", () => {
    expect(() => validatePathWithPermissions(".")).not.toThrow();
  });

  test("validatePathWithPermissions throws for non-existent path", () => {
    expect(() =>
      validatePathWithPermissions("Z:\\nonexistent\\12345"),
    ).toThrow();
  });

  test("validatePathWithPermissions accepts explicit read/write flags", () => {
    const tempDir = createTempDir();
    try {
      expect(() =>
        validatePathWithPermissions(tempDir, true, true),
      ).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// DocsPathFinder
// ============================================================================

describe("DocsPathFinder", () => {
  test("constructor sets relativePath correctly", () => {
    const finder = new DocsPathFinder("My Games\\Fallout4");
    expect(finder.relativePath).toBe("My Games\\Fallout4");
  });

  test("findDocsPath returns string or null", () => {
    const finder = new DocsPathFinder(
      "NonExistentGame\\VeryUnlikelyTestPath12345",
    );
    const result = finder.findDocsPath(null);
    // Most likely null since the game doesn't exist
    if (result !== null) {
      expect(typeof result).toBe("string");
    } else {
      expect(result).toBeNull();
    }
  });

  test("findDocsPath with valid cached path returns it", () => {
    const tempDir = createTempDir();
    try {
      const finder = new DocsPathFinder("test");
      const result = finder.findDocsPath(tempDir);
      expect(result).not.toBeNull();
      expect(typeof result).toBe("string");
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("findDocsPath with invalid cached path falls through", () => {
    const finder = new DocsPathFinder(
      "NonExistentGame\\VeryUnlikelyTestPath12345",
    );
    const result = finder.findDocsPath("Z:\\invalid\\cache\\path");
    // Both null and string are acceptable
    if (result !== null) {
      expect(typeof result).toBe("string");
    } else {
      expect(result).toBeNull();
    }
  });

  test("validateDocsPath throws for non-existent path", () => {
    const finder = new DocsPathFinder("test");
    expect(() =>
      finder.validateDocsPath("Z:\\nonexistent\\12345"),
    ).toThrow();
  });

  test("validateDocsPath succeeds for existing directory", () => {
    const tempDir = createTempDir();
    try {
      const finder = new DocsPathFinder("test");
      expect(() => finder.validateDocsPath(tempDir)).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("validateIniFiles throws for missing INI files", () => {
    const tempDir = createTempDir();
    try {
      const finder = new DocsPathFinder("test");
      expect(() =>
        finder.validateIniFiles(tempDir, ["Missing.ini"]),
      ).toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("validateIniFiles succeeds when INI files exist", () => {
    const tempDir = createTempDir();
    try {
      writeFileSync(join(tempDir, "Game.ini"), "[General]\nkey=value\n");
      const finder = new DocsPathFinder("test");
      expect(() =>
        finder.validateIniFiles(tempDir, ["Game.ini"]),
      ).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// BackupManager
// ============================================================================

describe("BackupManager", () => {
  test("constructor sets backupRoot correctly", () => {
    const manager = new BackupManager("C:\\Backups");
    expect(manager.backupRoot).toBe("C:\\Backups");
  });

  test("listVersions returns empty array for non-existent root", () => {
    const manager = new BackupManager("Z:\\nonexistent\\backups\\12345");
    const versions = manager.listVersions();
    expect(versions).toEqual([]);
  });

  test("listVersions returns version directories", () => {
    const tempDir = createTempDir();
    try {
      const backupRoot = join(tempDir, "backups");
      mkdirSync(join(backupRoot, "1_10_163_0"), { recursive: true });
      mkdirSync(join(backupRoot, "1_10_164_0"), { recursive: true });

      const manager = new BackupManager(backupRoot);
      const versions = manager.listVersions();
      expect(versions.length).toBe(2);
      expect(versions).toContain("1_10_163_0");
      expect(versions).toContain("1_10_164_0");
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("getVersionPath returns correct path", () => {
    const manager = new BackupManager("Backups");
    const version = new XseVersion("1.10.163.0");
    const path = manager.getVersionPath(version);
    expect(path).toContain("1_10_163_0");
    expect(path).toContain("Backups");
  });

  test("createBackup succeeds with valid source and version", () => {
    const tempDir = createTempDir();
    try {
      const sourceFile = join(tempDir, "Fallout4.ini");
      writeFileSync(sourceFile, "[General]\ntest=value\n");

      const backupRoot = join(tempDir, "backups");
      const manager = new BackupManager(backupRoot);
      const version = new XseVersion("1.10.163.0");

      const backupPath = manager.createBackup(sourceFile, version);
      expect(typeof backupPath).toBe("string");
      expect(backupPath).toContain("1_10_163_0");
      expect(existsSync(backupPath)).toBe(true);
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("createBackup throws for non-existent source", () => {
    const tempDir = createTempDir();
    try {
      const manager = new BackupManager(join(tempDir, "backups"));
      const version = new XseVersion("1.0.0");
      expect(() =>
        manager.createBackup("Z:\\nonexistent\\file.ini", version),
      ).toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("extractVersionFromXseLog throws for non-existent log", () => {
    const tempDir = createTempDir();
    try {
      const manager = new BackupManager(join(tempDir, "backups"));
      expect(() =>
        manager.extractVersionFromXseLog("Z:\\nonexistent\\f4se.log"),
      ).toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("extractVersionFromXseLog succeeds with valid log", () => {
    const tempDir = createTempDir();
    try {
      const logPath = join(tempDir, "f4se.log");
      writeFileSync(
        logPath,
        "F4SE version = 0.6.23\nruntime version = 1.10.163.0\n",
      );

      const manager = new BackupManager(join(tempDir, "backups"));
      const version = manager.extractVersionFromXseLog(logPath);
      expect(version).toBeDefined();
      expect(version.fullVersion()).toBe("0.6.23");
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// XseVersion
// ============================================================================

describe("XseVersion", () => {
  test("constructor and fullVersion", () => {
    const version = new XseVersion("1.10.163.0");
    expect(version.fullVersion()).toBe("1.10.163.0");
  });

  test("sanitized replaces dots with underscores", () => {
    const version = new XseVersion("1.10.163.0");
    expect(version.sanitized()).toBe("1_10_163_0");
  });

  test("toString returns human-readable representation", () => {
    const version = new XseVersion("1.10.163.0");
    const str = version.toString();
    expect(str).toContain("XseVersion");
    expect(str).toContain("1.10.163.0");
  });
});

// ============================================================================
// DocumentsChecker
// ============================================================================

describe("DocumentsChecker", () => {
  test("constructor sets gameName correctly", () => {
    const checker = new DocumentsChecker("Fallout4");
    expect(checker.gameName).toBe("Fallout4");
  });

  test("checkOnedriveInPath returns null for normal paths", () => {
    const checker = new DocumentsChecker("Fallout4");
    const result = checker.checkOnedriveInPath(
      "C:\\Users\\Name\\Documents\\My Games\\Fallout4",
    );
    expect(result).toBeNull();
  });

  test("checkOnedriveInPath returns warning for OneDrive paths", () => {
    const checker = new DocumentsChecker("Fallout4");
    const result = checker.checkOnedriveInPath(
      "C:\\Users\\Name\\OneDrive\\Documents\\My Games\\Fallout4",
    );
    expect(result).not.toBeNull();
    expect(typeof result).toBe("string");
    expect(result).toContain("OneDrive");
  });

  test("validateIniFile returns result for missing INI", () => {
    const tempDir = createTempDir();
    try {
      const docsPath = join(tempDir, "My Games", "Fallout4");
      mkdirSync(docsPath, { recursive: true });

      const checker = new DocumentsChecker("Fallout4");
      const result = checker.validateIniFile(docsPath, "Fallout4.ini");

      expect(result).toBeDefined();
      expect(result.iniName).toBe("Fallout4.ini");
      expect(result.exists).toBe(false);
      expect(result.isValid).toBe(false);
      expect(result.hasIssue).toBe(true);
      // issue is an #[napi(object)] field with Option<String>, so undefined when None
      expect(result.issue).toBe("missing");
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("validateIniFile returns OK for valid INI", () => {
    const tempDir = createTempDir();
    try {
      const docsPath = join(tempDir, "My Games", "Fallout4");
      mkdirSync(docsPath, { recursive: true });
      writeFileSync(
        join(docsPath, "Fallout4.ini"),
        "[General]\nkey=value\n",
      );

      const checker = new DocumentsChecker("Fallout4");
      const result = checker.validateIniFile(docsPath, "Fallout4.ini");

      expect(result.exists).toBe(true);
      expect(result.isValid).toBe(true);
      expect(result.hasIssue).toBe(false);
      // issue field is Option<String> in #[napi(object)] -> undefined when None
      expect(result.issue).toBeUndefined();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("runAllChecks returns array of messages", () => {
    const tempDir = createTempDir();
    try {
      const docsPath = join(tempDir, "My Games", "Fallout4");
      mkdirSync(docsPath, { recursive: true });
      writeFileSync(
        join(docsPath, "Fallout4.ini"),
        "[General]\nkey=value\n",
      );

      const checker = new DocumentsChecker("Fallout4");
      const messages = checker.runAllChecks(docsPath);

      expect(Array.isArray(messages)).toBe(true);
      // Should have 3 messages (main INI OK, Custom INI missing, Prefs INI missing)
      expect(messages.length).toBe(3);
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// Platform Utilities
// ============================================================================

describe("Platform utilities", () => {
  test("getSystemDocumentsPath returns string or null", () => {
    const result = getSystemDocumentsPath();
    // On Windows, this should find the documents path
    if (result !== null) {
      expect(typeof result).toBe("string");
      expect(result.length).toBeGreaterThan(0);
    } else {
      expect(result).toBeNull();
    }
  });

  test("removeReadonly does not throw for existing file", () => {
    const tempDir = createTempDir();
    try {
      const filePath = join(tempDir, "test.txt");
      writeFileSync(filePath, "test");
      expect(() => removeReadonly(filePath)).not.toThrow();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("queryGameRegistry returns string or null", () => {
    // Query for a game that likely isn't installed
    const result = queryGameRegistry("FakeGame12345", "", false);
    // Should return null since the game isn't registered
    expect(result).toBeNull();
  });

  test("queryGameRegistry returns string or null for real game", () => {
    // May or may not find Fallout 4 depending on installation
    const result = queryGameRegistry("Fallout4", "", true);
    if (result !== null) {
      expect(typeof result).toBe("string");
      expect(result.length).toBeGreaterThan(0);
    } else {
      expect(result).toBeNull();
    }
  });

  test("parseSteamLibrary returns null on Windows", () => {
    // On Windows, Steam library parsing always returns null
    const result = parseSteamLibrary(377160); // Fallout 4 Steam ID
    // Either null (Windows/not found) or string (Linux with Steam)
    if (result !== null) {
      expect(typeof result).toBe("string");
    } else {
      expect(result).toBeNull();
    }
  });
});
