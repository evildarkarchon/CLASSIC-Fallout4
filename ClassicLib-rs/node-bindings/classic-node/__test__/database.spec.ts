import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import {
  JsDatabasePool,
  getDefaultCacheTtl,
  getBatchCacheTtl,
  getMaxCacheTtl,
  DEFAULT_CACHE_TTL,
  BATCH_CACHE_TTL,
  MAX_CACHE_TTL,
} from "../index.js";

// ============================================================================
// Cache TTL Constants
// ============================================================================

describe("Database cache TTL constants", () => {
  test("DEFAULT_CACHE_TTL is 300 seconds (5 minutes)", () => {
    expect(DEFAULT_CACHE_TTL).toBe(300);
  });

  test("BATCH_CACHE_TTL is 1800 seconds (30 minutes)", () => {
    expect(BATCH_CACHE_TTL).toBe(1800);
  });

  test("MAX_CACHE_TTL is 3600 seconds (60 minutes)", () => {
    expect(MAX_CACHE_TTL).toBe(3600);
  });

  test("TTL constants are in ascending order", () => {
    expect(DEFAULT_CACHE_TTL).toBeLessThan(BATCH_CACHE_TTL);
    expect(BATCH_CACHE_TTL).toBeLessThan(MAX_CACHE_TTL);
  });
});

// ============================================================================
// Cache TTL Helper Functions
// ============================================================================

describe("Database cache TTL helper functions", () => {
  test("getDefaultCacheTtl returns 300", () => {
    expect(getDefaultCacheTtl()).toBe(300);
  });

  test("getBatchCacheTtl returns 1800", () => {
    expect(getBatchCacheTtl()).toBe(1800);
  });

  test("getMaxCacheTtl returns 3600", () => {
    expect(getMaxCacheTtl()).toBe(3600);
  });

  test("helper functions match constants", () => {
    expect(getDefaultCacheTtl()).toBe(DEFAULT_CACHE_TTL);
    expect(getBatchCacheTtl()).toBe(BATCH_CACHE_TTL);
    expect(getMaxCacheTtl()).toBe(MAX_CACHE_TTL);
  });
});

// ============================================================================
// DatabasePool Construction
// ============================================================================

describe("DatabasePool construction", () => {
  test("constructor creates pool with game table name", () => {
    const pool = new JsDatabasePool("Fallout4");
    expect(pool.getGameTable()).toBe("Fallout4");
  });

  test("constructor accepts custom max connections", () => {
    const pool = new JsDatabasePool("Skyrim", 16);
    expect(pool.getMaxConnections()).toBe(16);
  });

  test("constructor accepts custom cache TTL", () => {
    const pool = new JsDatabasePool("Fallout4", undefined, 600);
    // No direct getter for TTL, but construction should not throw
    expect(pool).toBeDefined();
  });

  test("constructor uses auto-calculated connections when omitted", () => {
    const pool = new JsDatabasePool("Fallout4");
    const maxConn = pool.getMaxConnections();
    expect(maxConn).toBeDefined();
    // Auto-calculated: CPU cores * 4, clamped to 8-64
    expect(maxConn!).toBeGreaterThanOrEqual(8);
    expect(maxConn!).toBeLessThanOrEqual(64);
  });

  test("pool is not available before initialization", () => {
    const pool = new JsDatabasePool("Fallout4");
    expect(pool.isAvailable()).toBe(false);
  });

  test("cache is empty on construction", () => {
    const pool = new JsDatabasePool("Fallout4");
    expect(pool.cacheSize()).toBe(0);
  });
});

// ============================================================================
// Game Table Management
// ============================================================================

describe("DatabasePool game table", () => {
  test("setGameTable updates the table name", () => {
    const pool = new JsDatabasePool("Fallout4");
    pool.setGameTable("Skyrim");
    expect(pool.getGameTable()).toBe("Skyrim");
  });

  test("setGameTable can be called multiple times", () => {
    const pool = new JsDatabasePool("Fallout4");
    pool.setGameTable("Skyrim");
    pool.setGameTable("FalloutNewVegas");
    expect(pool.getGameTable()).toBe("FalloutNewVegas");
  });
});

// ============================================================================
// Connection Settings
// ============================================================================

describe("DatabasePool connection settings", () => {
  test("setMaxConnections updates the value", () => {
    const pool = new JsDatabasePool("Fallout4", 4);
    expect(pool.getMaxConnections()).toBe(4);
    pool.setMaxConnections(32);
    expect(pool.getMaxConnections()).toBe(32);
  });

  test("recalculateMaxConnections updates to CPU-based value", () => {
    const pool = new JsDatabasePool("Fallout4", 4);
    pool.recalculateMaxConnections();
    const newMax = pool.getMaxConnections();
    expect(newMax).toBeDefined();
    expect(newMax!).toBeGreaterThanOrEqual(8);
    expect(newMax!).toBeLessThanOrEqual(64);
  });
});

// ============================================================================
// Cache Management
// ============================================================================

describe("DatabasePool cache management", () => {
  test("clearCache on empty pool returns 0", () => {
    const pool = new JsDatabasePool("Fallout4");
    const removed = pool.clearCache();
    expect(removed).toBe(0);
  });

  test("clearCache with expiredOnly on empty pool returns 0", () => {
    const pool = new JsDatabasePool("Fallout4");
    const removed = pool.clearCache(true);
    expect(removed).toBe(0);
  });

  test("setCacheTtl does not throw", () => {
    const pool = new JsDatabasePool("Fallout4");
    // Should not throw
    pool.setCacheTtl(600);
  });
});

// ============================================================================
// Statistics
// ============================================================================

describe("DatabasePool statistics", () => {
  test("getStats returns zero-initialized stats on fresh pool", () => {
    const pool = new JsDatabasePool("Fallout4");
    const stats = pool.getStats();

    expect(stats.totalQueries).toBe(0);
    expect(stats.cacheHits).toBe(0);
    expect(stats.cacheMisses).toBe(0);
    expect(stats.totalConnections).toBe(0);
    expect(stats.activeConnections).toBe(0);
    expect(stats.cacheHitRate).toBe(0);
  });

  test("getStats returns all expected fields", () => {
    const pool = new JsDatabasePool("Fallout4");
    const stats = pool.getStats();

    expect(typeof stats.totalQueries).toBe("number");
    expect(typeof stats.cacheHits).toBe("number");
    expect(typeof stats.cacheMisses).toBe("number");
    expect(typeof stats.totalConnections).toBe("number");
    expect(typeof stats.activeConnections).toBe("number");
    expect(typeof stats.cacheHitRate).toBe("number");
  });
});

// ============================================================================
// Async Operations on Uninitialized Pool
// ============================================================================

describe("DatabasePool async operations on uninitialized pool", () => {
  test("getEntry returns null on uninitialized pool", async () => {
    const pool = new JsDatabasePool("Fallout4");
    const result = await pool.getEntry("12345678", "Test.esp");
    expect(result).toBeNull();
  });

  test("getEntriesBatch returns empty object on uninitialized pool", async () => {
    const pool = new JsDatabasePool("Fallout4");
    const result = await pool.getEntriesBatch(
      [["12345678", "Test.esp"]],
    );
    expect(Object.keys(result).length).toBe(0);
  });

  test("getEntriesBatch with empty pairs returns empty object", async () => {
    const pool = new JsDatabasePool("Fallout4");
    const result = await pool.getEntriesBatch([]);
    expect(Object.keys(result).length).toBe(0);
  });

  test("batchLookup returns entries with undefined on uninitialized pool", async () => {
    const pool = new JsDatabasePool("Fallout4");
    const results = await pool.batchLookup([
      ["12345678", "Test.esp"],
      ["ABCDEF01", "Other.esp"],
    ]);

    expect(results.length).toBe(2);
    expect(results[0].formId).toBe("12345678");
    expect(results[0].plugin).toBe("Test.esp");
    expect(results[0].entry).toBeUndefined();
    expect(results[1].formId).toBe("ABCDEF01");
    expect(results[1].plugin).toBe("Other.esp");
    expect(results[1].entry).toBeUndefined();
  });

  test("batchLookup with empty pairs returns empty array", async () => {
    const pool = new JsDatabasePool("Fallout4");
    const results = await pool.batchLookup([]);
    expect(results.length).toBe(0);
  });

  test("close on uninitialized pool does not throw", async () => {
    const pool = new JsDatabasePool("Fallout4");
    await pool.close();
    // Should complete without error
    expect(pool.isAvailable()).toBe(false);
  });

  test("optimize on uninitialized pool does not throw", async () => {
    const pool = new JsDatabasePool("Fallout4");
    await pool.optimize();
    // Should complete without error (no pools to optimize)
  });
});

// ============================================================================
// Initialize with Missing Databases
// ============================================================================

describe("DatabasePool initialization with missing databases", () => {
  test("initialize with non-existent paths does not throw", async () => {
    const pool = new JsDatabasePool("Fallout4");
    // Non-existent paths are silently skipped (warned, not errored)
    await pool.initialize(["Z:\\nonexistent\\path\\database.db"]);
    expect(pool.isAvailable()).toBe(false);
  });

  test("initialize with empty array does not throw", async () => {
    const pool = new JsDatabasePool("Fallout4");
    await pool.initialize([]);
    expect(pool.isAvailable()).toBe(false);
  });
});

// ============================================================================
// Input Validation
// ============================================================================

describe("DatabasePool input validation", () => {
  test("getEntriesBatch rejects malformed pairs", async () => {
    const pool = new JsDatabasePool("Fallout4");
    // Each pair must have exactly 2 elements
    try {
      await pool.getEntriesBatch([["only_one_element"] as any]);
      // Should not reach here
      expect(true).toBe(false);
    } catch (e: any) {
      expect(e.message).toContain("exactly [formId, plugin]");
    }
  });

  test("batchLookup rejects malformed pairs", async () => {
    const pool = new JsDatabasePool("Fallout4");
    try {
      await pool.batchLookup([["a", "b", "c"] as any]);
      expect(true).toBe(false);
    } catch (e: any) {
      expect(e.message).toContain("exactly [formId, plugin]");
    }
  });
});
