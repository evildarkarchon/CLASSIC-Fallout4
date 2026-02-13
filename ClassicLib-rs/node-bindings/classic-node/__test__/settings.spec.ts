import { describe, test, expect, beforeEach } from "bun:test";
import { writeFileSync, mkdtempSync, unlinkSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  loadSettingsSync,
  loadSettingsAsync,
  loadBatchSync,
  loadBatchAsync,
  getCached,
  isCached,
  invalidateSettings,
  clearSettingsCache,
  settingsCacheSize,
  settingsCacheKeys,
  getSettingsCacheStats,
  resetSettingsCacheStats,
} from "../index.js";

/** Create a temporary YAML file and return its path. */
function createTempYaml(content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "classic-settings-test-"));
  const filePath = join(dir, "test.yaml");
  writeFileSync(filePath, content, "utf-8");
  return filePath;
}

/** Remove a temp file and its parent directory (best-effort). */
function cleanupTemp(filePath: string) {
  try {
    unlinkSync(filePath);
    rmSync(join(filePath, ".."), { recursive: true, force: true });
  } catch {
    // Ignore cleanup errors
  }
}

describe("Settings cache bindings", () => {
  beforeEach(() => {
    clearSettingsCache();
    resetSettingsCacheStats();
  });

  // ========================================================================
  // Sync loading
  // ========================================================================

  describe("loadSettingsSync", () => {
    test("loads a YAML file and returns parsed documents array", () => {
      const path = createTempYaml("game: Fallout4\nversion: 1.0\n");
      try {
        const docs = loadSettingsSync("test_sync", path);
        expect(Array.isArray(docs)).toBe(true);
        expect(docs.length).toBe(1);
        expect(docs[0].game).toBe("Fallout4");
        expect(docs[0].version).toBe(1.0);
      } finally {
        cleanupTemp(path);
      }
    });

    test("caches the loaded file", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("cached_key", path);
        expect(isCached("cached_key")).toBe(true);
        expect(settingsCacheSize()).toBe(1);
      } finally {
        cleanupTemp(path);
      }
    });

    test("throws on non-existent file", () => {
      expect(() =>
        loadSettingsSync("bad_path", "Z:\\nonexistent\\file.yaml")
      ).toThrow();
    });

    test("handles multi-document YAML", () => {
      const path = createTempYaml("doc1: value1\n---\ndoc2: value2\n");
      try {
        const docs = loadSettingsSync("multi_doc", path);
        expect(docs.length).toBe(2);
        expect(docs[0].doc1).toBe("value1");
        expect(docs[1].doc2).toBe("value2");
      } finally {
        cleanupTemp(path);
      }
    });

    test("handles complex nested structures", () => {
      const yaml = [
        "root:",
        "  nested:",
        "    deep: value",
        "  list:",
        "    - item1",
        "    - item2",
        "  number: 42",
        "  flag: true",
        "",
      ].join("\n");
      const path = createTempYaml(yaml);
      try {
        const docs = loadSettingsSync("complex", path);
        expect(docs[0].root.nested.deep).toBe("value");
        expect(docs[0].root.list).toEqual(["item1", "item2"]);
        expect(docs[0].root.number).toBe(42);
        expect(docs[0].root.flag).toBe(true);
      } finally {
        cleanupTemp(path);
      }
    });

    test("replaces cache entry on reload with same key", () => {
      const path1 = createTempYaml("version: 1\n");
      const path2 = createTempYaml("version: 2\n");
      try {
        loadSettingsSync("reload_key", path1);
        expect(getCached("reload_key")![0].version).toBe(1);

        loadSettingsSync("reload_key", path2);
        expect(getCached("reload_key")![0].version).toBe(2);
        expect(settingsCacheSize()).toBe(1);
      } finally {
        cleanupTemp(path1);
        cleanupTemp(path2);
      }
    });
  });

  // ========================================================================
  // Async loading
  // ========================================================================

  describe("loadSettingsAsync", () => {
    test("loads a YAML file asynchronously", async () => {
      const path = createTempYaml("async_key: async_value\n");
      try {
        const docs = await loadSettingsAsync("test_async", path);
        expect(Array.isArray(docs)).toBe(true);
        expect(docs.length).toBe(1);
        expect(docs[0].async_key).toBe("async_value");
        expect(isCached("test_async")).toBe(true);
      } finally {
        cleanupTemp(path);
      }
    });

    test("throws on non-existent file", async () => {
      await expect(
        loadSettingsAsync("bad_async", "Z:\\nonexistent\\async.yaml")
      ).rejects.toThrow();
    });
  });

  // ========================================================================
  // Batch loading
  // ========================================================================

  describe("loadBatchSync", () => {
    test("loads multiple files and returns count", () => {
      const path1 = createTempYaml("file: one\n");
      const path2 = createTempYaml("file: two\n");
      try {
        const count = loadBatchSync([path1, path2]);
        expect(count).toBe(2);
        expect(settingsCacheSize()).toBe(2);
      } finally {
        cleanupTemp(path1);
        cleanupTemp(path2);
      }
    });

    test("returns 0 for empty paths array", () => {
      const count = loadBatchSync([]);
      expect(count).toBe(0);
    });

    test("throws if any file is invalid", () => {
      const path1 = createTempYaml("valid: file\n");
      try {
        expect(() =>
          loadBatchSync([path1, "Z:\\nonexistent.yaml"])
        ).toThrow();
      } finally {
        cleanupTemp(path1);
      }
    });
  });

  describe("loadBatchAsync", () => {
    test("loads multiple files concurrently", async () => {
      const path1 = createTempYaml("async_file: one\n");
      const path2 = createTempYaml("async_file: two\n");
      try {
        const count = await loadBatchAsync([path1, path2]);
        expect(count).toBe(2);
        expect(settingsCacheSize()).toBe(2);
      } finally {
        cleanupTemp(path1);
        cleanupTemp(path2);
      }
    });

    test("returns 0 for empty paths array", async () => {
      const count = await loadBatchAsync([]);
      expect(count).toBe(0);
    });
  });

  // ========================================================================
  // Cache retrieval
  // ========================================================================

  describe("getCached", () => {
    test("returns documents for a cached key", () => {
      const path = createTempYaml("cached: data\n");
      try {
        loadSettingsSync("get_test", path);
        const docs = getCached("get_test");
        expect(docs).toBeDefined();
        expect(docs![0].cached).toBe("data");
      } finally {
        cleanupTemp(path);
      }
    });

    test("returns null for a non-existent key", () => {
      const result = getCached("nonexistent_key");
      expect(result).toBeNull();
    });
  });

  describe("isCached", () => {
    test("returns true for cached key", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("is_cached_test", path);
        expect(isCached("is_cached_test")).toBe(true);
      } finally {
        cleanupTemp(path);
      }
    });

    test("returns false for non-existent key", () => {
      expect(isCached("never_added")).toBe(false);
    });
  });

  // ========================================================================
  // Cache management
  // ========================================================================

  describe("invalidateSettings", () => {
    test("removes a cached entry and returns true", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("inv_key", path);
        expect(invalidateSettings("inv_key")).toBe(true);
        expect(isCached("inv_key")).toBe(false);
      } finally {
        cleanupTemp(path);
      }
    });

    test("returns false for non-existent key", () => {
      expect(invalidateSettings("never_existed")).toBe(false);
    });
  });

  describe("clearSettingsCache", () => {
    test("removes all entries", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("clear1", path);
        loadSettingsSync("clear2", path);
        expect(settingsCacheSize()).toBe(2);

        clearSettingsCache();
        expect(settingsCacheSize()).toBe(0);
      } finally {
        cleanupTemp(path);
      }
    });

    test("is safe to call on empty cache", () => {
      clearSettingsCache();
      expect(settingsCacheSize()).toBe(0);
    });
  });

  describe("settingsCacheSize", () => {
    test("returns 0 when empty", () => {
      expect(settingsCacheSize()).toBe(0);
    });

    test("reflects number of loaded entries", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("size1", path);
        loadSettingsSync("size2", path);
        loadSettingsSync("size3", path);
        expect(settingsCacheSize()).toBe(3);
      } finally {
        cleanupTemp(path);
      }
    });
  });

  describe("settingsCacheKeys", () => {
    test("returns empty array when cache is empty", () => {
      expect(settingsCacheKeys()).toEqual([]);
    });

    test("returns all cached keys", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("alpha", path);
        loadSettingsSync("beta", path);
        const keys = settingsCacheKeys();
        expect(keys.length).toBe(2);
        expect(keys).toContain("alpha");
        expect(keys).toContain("beta");
      } finally {
        cleanupTemp(path);
      }
    });
  });

  // ========================================================================
  // Statistics
  // ========================================================================

  describe("getSettingsCacheStats", () => {
    test("returns zeroed stats after reset", () => {
      const stats = getSettingsCacheStats();
      expect(stats.hits).toBe(0);
      expect(stats.misses).toBe(0);
      expect(stats.hitRate).toBe(0);
      expect(stats.size).toBe(0);
      expect(stats.keys).toEqual([]);
    });

    test("tracks cache hits", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("stats_key", path);
        getCached("stats_key"); // hit
        getCached("stats_key"); // hit

        const stats = getSettingsCacheStats();
        expect(stats.hits).toBe(2);
        expect(stats.size).toBe(1);
      } finally {
        cleanupTemp(path);
      }
    });

    test("tracks cache misses", () => {
      getCached("nonexistent"); // miss
      getCached("also_nonexistent"); // miss

      const stats = getSettingsCacheStats();
      expect(stats.misses).toBe(2);
      expect(stats.hitRate).toBe(0);
    });

    test("calculates hit rate correctly", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("rate_key", path);
        getCached("rate_key"); // hit
        getCached("rate_key"); // hit
        getCached("rate_key"); // hit
        getCached("missing");  // miss

        const stats = getSettingsCacheStats();
        expect(stats.hits).toBe(3);
        expect(stats.misses).toBe(1);
        expect(stats.hitRate).toBeCloseTo(0.75, 2);
      } finally {
        cleanupTemp(path);
      }
    });
  });

  describe("resetSettingsCacheStats", () => {
    test("clears hit and miss counters", () => {
      const path = createTempYaml("key: value\n");
      try {
        loadSettingsSync("reset_key", path);
        getCached("reset_key"); // hit
        getCached("no_key");    // miss

        resetSettingsCacheStats();

        const stats = getSettingsCacheStats();
        expect(stats.hits).toBe(0);
        expect(stats.misses).toBe(0);
        // Cache entries are still present though
        expect(stats.size).toBe(1);
      } finally {
        cleanupTemp(path);
      }
    });
  });

  // ========================================================================
  // Default value fallback via getCached
  // ========================================================================

  describe("default value fallback pattern", () => {
    test("getCached returns undefined for missing key (use ?? for default)", () => {
      const result = getCached("missing") ?? [{ setting: "default_value" }];
      expect(result[0].setting).toBe("default_value");
    });
  });
});
