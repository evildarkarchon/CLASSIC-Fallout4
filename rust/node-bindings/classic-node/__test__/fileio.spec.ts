import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import {
  JsFileIO,
  hashFile,
  hashFilesParallel,
  detectEncoding,
  JsBackupManager,
} from "../index.js";

// ============================================================================
// Helper: create a temp directory that is cleaned up after each test
// ============================================================================

let tempDir: string;

beforeEach(() => {
  tempDir = mkdtempSync(join(tmpdir(), "classic-fileio-test-"));
});

afterEach(() => {
  rmSync(tempDir, { recursive: true, force: true });
});

// ============================================================================
// JsFileIO constructor
// ============================================================================

describe("JsFileIO constructor", () => {
  test("creates instance with no config", () => {
    const io = new JsFileIO();
    expect(io).toBeDefined();
  });

  test("creates instance with partial config", () => {
    const io = new JsFileIO({ cacheSize: 200 });
    expect(io).toBeDefined();
  });

  test("creates instance with full config", () => {
    const io = new JsFileIO({
      encoding: "utf-8",
      cacheSize: 50,
      maxConcurrentIo: 25,
    });
    expect(io).toBeDefined();
  });
});

// ============================================================================
// Async read/write round-trip
// ============================================================================

describe("JsFileIO readFile / writeFile", () => {
  test("writeFile then readFile round-trips content", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "round-trip.txt");

    await io.writeFile(filePath, "Hello from NAPI!");
    const content = await io.readFile(filePath);
    expect(content).toBe("Hello from NAPI!");
  });

  test("readFile throws for non-existent file", async () => {
    const io = new JsFileIO();
    const badPath = join(tempDir, "nonexistent.txt");

    await expect(io.readFile(badPath)).rejects.toThrow();
  });

  test("readFile reads pre-existing file", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "preexisting.txt");
    writeFileSync(filePath, "Pre-existing content");

    const content = await io.readFile(filePath);
    expect(content).toBe("Pre-existing content");
  });
});

// ============================================================================
// readLines / writeLines
// ============================================================================

describe("JsFileIO readLines / writeLines", () => {
  test("writeLines then readLines round-trips", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "lines.txt");
    const lines = ["Line 1", "Line 2", "Line 3"];

    await io.writeLines(filePath, lines);
    const result = await io.readLines(filePath);
    expect(result).toEqual(lines);
  });

  test("readLines returns empty array for empty file", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "empty.txt");
    writeFileSync(filePath, "");

    const result = await io.readLines(filePath);
    expect(result).toEqual([]);
  });
});

// ============================================================================
// readBytes / writeBytes
// ============================================================================

describe("JsFileIO readBytes / writeBytes", () => {
  test("writeBytes then readBytes round-trips binary data", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "binary.bin");
    const data = new Uint8Array([0x00, 0x01, 0x02, 0xff, 0xfe]);

    await io.writeBytes(filePath, Array.from(data));
    const result = await io.readBytes(filePath);

    // readBytes returns a regular array (Vec<u8>), compare element-by-element
    expect(result.length).toBe(data.length);
    for (let i = 0; i < data.length; i++) {
      expect(result[i]).toBe(data[i]);
    }
  });

  test("writeBytes creates parent directories", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "nested", "dir", "file.bin");

    await io.writeBytes(filePath, [0x48, 0x65, 0x6c, 0x6c, 0x6f]);
    const exists = io.fileExists(filePath);
    expect(exists).toBe(true);
  });
});

// ============================================================================
// appendFile
// ============================================================================

describe("JsFileIO appendFile", () => {
  test("appendFile adds content to existing file", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "append.txt");
    writeFileSync(filePath, "Initial\n");

    await io.appendFile(filePath, "Appended\n");
    const content = await io.readFile(filePath);
    expect(content).toBe("Initial\nAppended\n");
  });

  test("appendFile creates file if it does not exist", async () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "new-append.txt");

    await io.appendFile(filePath, "First\n");
    await io.appendFile(filePath, "Second\n");
    const content = await io.readFile(filePath);
    expect(content).toBe("First\nSecond\n");
  });
});

// ============================================================================
// clearCache
// ============================================================================

describe("JsFileIO clearCache", () => {
  test("clearCache does not throw", async () => {
    const io = new JsFileIO();
    // Populate some cache state
    const filePath = join(tempDir, "cache-test.txt");
    writeFileSync(filePath, "cached content");
    await io.readFile(filePath);

    // Clearing should not throw
    await io.clearCache();
  });
});

// ============================================================================
// fileExists
// ============================================================================

describe("JsFileIO fileExists", () => {
  test("returns true for existing file", () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "exists.txt");
    writeFileSync(filePath, "content");

    expect(io.fileExists(filePath)).toBe(true);
  });

  test("returns false for non-existent file", () => {
    const io = new JsFileIO();
    expect(io.fileExists(join(tempDir, "nope.txt"))).toBe(false);
  });

  test("returns true for directory", () => {
    const io = new JsFileIO();
    expect(io.fileExists(tempDir)).toBe(true);
  });
});

// ============================================================================
// getFileSize
// ============================================================================

describe("JsFileIO getFileSize", () => {
  test("returns file size for a file", () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "sized.txt");
    writeFileSync(filePath, "12345");

    const size = io.getFileSize(filePath);
    expect(size).toBe(5);
  });

  test("returns null for directory", () => {
    const io = new JsFileIO();
    const size = io.getFileSize(tempDir);
    expect(size).toBeNull();
  });

  test("returns null for non-existent path", () => {
    const io = new JsFileIO();
    const size = io.getFileSize(join(tempDir, "nonexistent.txt"));
    expect(size).toBeNull();
  });
});

// ============================================================================
// isDirectory
// ============================================================================

describe("JsFileIO isDirectory", () => {
  test("returns true for a directory", () => {
    const io = new JsFileIO();
    expect(io.isDirectory(tempDir)).toBe(true);
  });

  test("returns false for a file", () => {
    const io = new JsFileIO();
    const filePath = join(tempDir, "file.txt");
    writeFileSync(filePath, "content");

    expect(io.isDirectory(filePath)).toBe(false);
  });

  test("returns false for non-existent path", () => {
    const io = new JsFileIO();
    expect(io.isDirectory(join(tempDir, "nonexistent"))).toBe(false);
  });
});

// ============================================================================
// walkDirectory
// ============================================================================

describe("JsFileIO walkDirectory", () => {
  test("returns all files in directory", () => {
    const io = new JsFileIO();
    writeFileSync(join(tempDir, "a.txt"), "");
    writeFileSync(join(tempDir, "b.log"), "");

    const files = io.walkDirectory(tempDir);
    expect(files.length).toBe(2);
  });

  test("filters by regex pattern", () => {
    const io = new JsFileIO();
    writeFileSync(join(tempDir, "test.txt"), "");
    writeFileSync(join(tempDir, "test.log"), "");
    writeFileSync(join(tempDir, "other.txt"), "");

    const files = io.walkDirectory(tempDir, "\\.log$");
    expect(files.length).toBe(1);
    expect(files[0]).toContain("test.log");
  });

  test("respects maxDepth", () => {
    const io = new JsFileIO();
    writeFileSync(join(tempDir, "root.txt"), "");
    const subDir = join(tempDir, "sub");
    mkdirSync(subDir);
    writeFileSync(join(subDir, "nested.txt"), "");

    // depth 1 = only the root directory (not subdirectories)
    const shallow = io.walkDirectory(tempDir, undefined, 1);
    expect(shallow.length).toBe(1);

    // unlimited depth
    const deep = io.walkDirectory(tempDir);
    expect(deep.length).toBe(2);
  });

  test("returns empty array for empty directory", () => {
    const io = new JsFileIO();
    const emptyDir = join(tempDir, "empty");
    mkdirSync(emptyDir);

    const files = io.walkDirectory(emptyDir);
    expect(files).toEqual([]);
  });

  test("throws for invalid regex pattern", () => {
    const io = new JsFileIO();
    expect(() => io.walkDirectory(tempDir, "[invalid")).toThrow();
  });
});

// ============================================================================
// readMultipleFiles / writeMultipleFiles
// ============================================================================

describe("JsFileIO readMultipleFiles / writeMultipleFiles", () => {
  test("writeMultipleFiles then readMultipleFiles round-trips", async () => {
    const io = new JsFileIO();

    const files: Record<string, string> = {};
    for (let i = 0; i < 3; i++) {
      files[join(tempDir, `multi-${i}.txt`)] = `Content ${i}`;
    }

    await io.writeMultipleFiles(files);

    const paths = Object.keys(files);
    const results = await io.readMultipleFiles(paths);

    for (const [path, content] of Object.entries(results)) {
      expect(content).toBe(files[path]);
    }
  });

  test("readMultipleFiles returns empty string for failed files", async () => {
    const io = new JsFileIO();
    const existingPath = join(tempDir, "exists.txt");
    writeFileSync(existingPath, "hello");

    const results = await io.readMultipleFiles([
      existingPath,
      join(tempDir, "nonexistent.txt"),
    ]);

    expect(results[existingPath]).toBe("hello");
    // Failed reads map to empty string
    const failedKey = Object.keys(results).find((k) => k !== existingPath);
    expect(failedKey).toBeDefined();
    expect(results[failedKey!]).toBe("");
  });
});

// ============================================================================
// hashFile
// ============================================================================

describe("hashFile", () => {
  test("returns 64-character hex SHA256 hash", () => {
    const filePath = join(tempDir, "hash-test.txt");
    writeFileSync(filePath, "Hello, World!");

    const hash = hashFile(filePath);
    expect(hash.length).toBe(64);
    // Known SHA256 of "Hello, World!"
    expect(hash).toBe(
      "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    );
  });

  test("throws for non-existent file", () => {
    expect(() => hashFile(join(tempDir, "nope.txt"))).toThrow();
  });
});

// ============================================================================
// hashFilesParallel
// ============================================================================

describe("hashFilesParallel", () => {
  test("hashes multiple files in parallel", () => {
    const paths: string[] = [];
    for (let i = 0; i < 3; i++) {
      const p = join(tempDir, `parallel-${i}.txt`);
      writeFileSync(p, `Content ${i}`);
      paths.push(p);
    }

    const results = hashFilesParallel(paths);
    expect(Object.keys(results).length).toBe(3);

    for (const hash of Object.values(results)) {
      expect(hash.length).toBe(64);
    }
  });

  test("returns empty string for files that fail to hash", () => {
    const goodPath = join(tempDir, "good.txt");
    writeFileSync(goodPath, "data");

    const results = hashFilesParallel([
      goodPath,
      join(tempDir, "bad-path.txt"),
    ]);

    expect(results[goodPath].length).toBe(64);
    // Failed files get empty string
    const failedKey = Object.keys(results).find((k) => k !== goodPath);
    expect(failedKey).toBeDefined();
    expect(results[failedKey!]).toBe("");
  });
});

// ============================================================================
// detectEncoding
// ============================================================================

describe("detectEncoding", () => {
  test("detects UTF-8 for ASCII content", () => {
    const filePath = join(tempDir, "utf8.txt");
    writeFileSync(filePath, "Simple ASCII text");

    const encoding = detectEncoding(filePath);
    expect(encoding).toBe("UTF-8");
  });

  test("detects windows-1252 for invalid UTF-8 bytes", () => {
    const filePath = join(tempDir, "win1252.txt");
    // 0x80 is Euro sign in Windows-1252, invalid start byte in UTF-8
    writeFileSync(filePath, Buffer.from([0x80, 0x81, 0x82, 0x83]));

    const encoding = detectEncoding(filePath);
    expect(encoding).toBe("windows-1252");
  });

  test("throws for non-existent file", () => {
    expect(() => detectEncoding(join(tempDir, "missing.txt"))).toThrow();
  });
});

// ============================================================================
// JsBackupManager
// ============================================================================

describe("JsBackupManager", () => {
  test("constructor accepts a game root string", () => {
    const manager = new JsBackupManager(tempDir);
    expect(manager).toBeDefined();
  });

  test("backupExists returns false for empty directory", async () => {
    const manager = new JsBackupManager(tempDir);
    const exists = await manager.backupExists("xse");
    expect(exists).toBe(false);
  });

  test("backupExists rejects invalid backup type", async () => {
    const manager = new JsBackupManager(tempDir);
    await expect(manager.backupExists("invalid_type")).rejects.toThrow(
      /Unknown backup type/
    );
  });
});
