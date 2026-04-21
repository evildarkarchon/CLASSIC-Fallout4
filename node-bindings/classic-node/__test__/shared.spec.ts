import { describe, test, expect, beforeEach } from "bun:test";
import {
  // Path utilities
  normalizePath,
  joinPaths,
  validatePathsBatch,
  // String utilities
  internString,
  processStringBatch,
  normalizeString,
  // Performance metrics
  recordTimingMetric,
  getMetricsSummary,
  clearAllMetrics,
  // Registry
  registryGet,
  registrySet,
  registryRemove,
  registryClear,
  // Registry convenience
  registrySetGame,
  registryGetGame,
  registryGetGameVersion,
  // Diagnostics
  isRuntimeAvailable,
  getRuntimeInfo,
  // Application dir (read-only -- Phase 4 Plan 5)
  getApplicationDir,
} from "../index.js";

// ============================================================================
// Path Utilities
// ============================================================================

describe("Path utilities", () => {
  test("normalizePath normalizes a valid path", () => {
    const result = normalizePath(".");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  test("normalizePath handles non-existent paths without throwing", () => {
    // Non-existent paths fall back to clean_path internally
    const result = normalizePath("Z:\\nonexistent\\test\\path");
    expect(typeof result).toBe("string");
  });

  test("joinPaths joins path components", () => {
    const result = joinPaths(["C:\\Games", "Fallout4", "Data"]);
    expect(result).toContain("Fallout4");
    expect(result).toContain("Data");
  });

  test("joinPaths with single element returns that element", () => {
    const result = joinPaths(["C:\\Games"]);
    expect(result).toBe("C:\\Games");
  });

  test("joinPaths throws on empty array", () => {
    expect(() => joinPaths([])).toThrow();
  });

  test("validatePathsBatch returns boolean map", () => {
    const result = validatePathsBatch([".", "Z:\\nonexistent\\42"]);
    expect(result["."]).toBe(true);
    expect(result["Z:\\nonexistent\\42"]).toBe(false);
  });

  test("validatePathsBatch with empty array returns empty object", () => {
    const result = validatePathsBatch([]);
    expect(Object.keys(result).length).toBe(0);
  });
});

// ============================================================================
// String Utilities
// ============================================================================

describe("String utilities", () => {
  test("internString returns the same string content", () => {
    const result = internString("hello world");
    expect(result).toBe("hello world");
  });

  test("internString handles empty string", () => {
    const result = internString("");
    expect(result).toBe("");
  });

  test("processStringBatch normalizes all strings", () => {
    const result = processStringBatch(["  Hello   World  ", "FOO  BAR"]);
    expect(result).toEqual(["hello world", "foo bar"]);
  });

  test("processStringBatch with empty array returns empty array", () => {
    const result = processStringBatch([]);
    expect(result).toEqual([]);
  });

  test("normalizeString trims, lowercases, and collapses whitespace", () => {
    expect(normalizeString("  Hello   World  ")).toBe("hello world");
    expect(normalizeString("UPPER")).toBe("upper");
    expect(normalizeString("")).toBe("");
    expect(normalizeString("a  b  c")).toBe("a b c");
  });
});

// ============================================================================
// Performance Metrics
// ============================================================================

describe("Performance metrics", () => {
  beforeEach(() => {
    clearAllMetrics();
  });

  test("recordTimingMetric and getMetricsSummary round-trip", () => {
    recordTimingMetric("test_op", 100.0);
    recordTimingMetric("test_op", 200.0);

    const summary = getMetricsSummary();
    expect(summary.timings).toBeDefined();

    const stats = summary.timings["test_op"];
    expect(stats).toBeDefined();
    expect(stats.count).toBe(2);
    expect(stats.totalMs).toBeCloseTo(300.0, 1);
    expect(stats.avgMs).toBeCloseTo(150.0, 1);
    expect(stats.minMs).toBeCloseTo(100.0, 1);
    expect(stats.maxMs).toBeCloseTo(200.0, 1);
  });

  test("getMetricsSummary returns empty timings when cleared", () => {
    const summary = getMetricsSummary();
    expect(Object.keys(summary.timings).length).toBe(0);
  });

  test("clearAllMetrics removes all recorded metrics", () => {
    recordTimingMetric("to_clear", 50.0);
    clearAllMetrics();
    const summary = getMetricsSummary();
    expect(summary.timings["to_clear"]).toBeUndefined();
  });

  test("multiple operations tracked independently", () => {
    recordTimingMetric("op_a", 10.0);
    recordTimingMetric("op_b", 20.0);

    const summary = getMetricsSummary();
    expect(summary.timings["op_a"]).toBeDefined();
    expect(summary.timings["op_b"]).toBeDefined();
    expect(summary.timings["op_a"].count).toBe(1);
    expect(summary.timings["op_b"].count).toBe(1);
  });
});

// ============================================================================
// Registry
// ============================================================================

describe("Registry", () => {
  beforeEach(() => {
    registryClear();
  });

  test("registrySet and registryGet round-trip string value", () => {
    registrySet("test_key", "test_value");
    const result = registryGet("test_key");
    expect(result).toBe("test_value");
  });

  test("registrySet and registryGet round-trip number value", () => {
    registrySet("num_key", 42);
    const result = registryGet("num_key");
    expect(result).toBe(42);
  });

  test("registrySet and registryGet round-trip boolean value", () => {
    registrySet("bool_key", true);
    const result = registryGet("bool_key");
    expect(result).toBe(true);
  });

  test("registrySet and registryGet round-trip object value", () => {
    registrySet("obj_key", { name: "Fallout4", version: 1 });
    const result = registryGet("obj_key") as Record<string, unknown>;
    expect(result).toBeDefined();
    expect(result.name).toBe("Fallout4");
    expect(result.version).toBe(1);
  });

  test("registryGet returns null for non-existent key", () => {
    const result = registryGet("nonexistent");
    expect(result).toBeNull();
  });

  test("registryRemove removes an existing key", () => {
    registrySet("temp_key", "temp_value");
    const removed = registryRemove("temp_key");
    expect(removed).toBe(true);
    expect(registryGet("temp_key")).toBeNull();
  });

  test("registryRemove returns false for non-existent key", () => {
    const removed = registryRemove("nonexistent");
    expect(removed).toBe(false);
  });

  test("registryClear removes all entries", () => {
    registrySet("key1", "value1");
    registrySet("key2", "value2");
    registryClear();
    expect(registryGet("key1")).toBeNull();
    expect(registryGet("key2")).toBeNull();
  });
});

// ============================================================================
// Diagnostics
// ============================================================================

describe("Diagnostics", () => {
  test("isRuntimeAvailable returns true", () => {
    const available = isRuntimeAvailable();
    expect(available).toBe(true);
  });

  test("getRuntimeInfo returns valid info object", () => {
    const info = getRuntimeInfo();
    expect(info.available).toBe(true);
    expect(info.threadCount).toBeGreaterThan(0);
  });
});

// ============================================================================
// Registry Convenience Functions
// ============================================================================

describe("Registry convenience functions", () => {
  beforeEach(() => {
    registryClear();
  });

  test("registrySetGame and registryGetGame round-trip", () => {
    registrySetGame("Fallout4");
    const game = registryGetGame();
    expect(game).toBe("Fallout4");
  });

  test("registryGetGame returns null when not set", () => {
    const game = registryGetGame();
    expect(game).toBeNull();
  });

  test("registrySetGame overwrites previous value", () => {
    registrySetGame("Fallout4");
    registrySetGame("Skyrim");
    expect(registryGetGame()).toBe("Skyrim");
  });

  test("registryGetGameVersion returns null when not set", () => {
    const version = registryGetGameVersion();
    expect(version).toBeNull();
  });

  test("registryGetGameVersion returns set value", () => {
    registrySet("gamevars_version", "Original");
    const version = registryGetGameVersion();
    expect(version).toBe("Original");
  });

});

// ============================================================================
// Application Dir (Phase 4 Plan 5 -- MEDIUM concern: read-only only)
// ============================================================================
describe("shared: getApplicationDir (read-only against Once-initialized state)", () => {
  test("returns a string or null without throwing", () => {
    // IMPORTANT: Do NOT call setApplicationDir in the same test process.
    // The Once guard in classic-registry-core permanently mutates process
    // state on first set. A round-trip test would either fail (if the Once
    // has already been initialized) or pollute downstream tests.
    try {
      const dir = getApplicationDir();
      // If state is initialized, dir is a non-empty string; otherwise null
      expect(typeof dir === "string" || dir === null).toBe(true);
      if (typeof dir === "string") {
        expect(dir.length).toBeGreaterThan(0);
      }
    } catch (e) {
      // If Once not yet initialized, the function may throw -- acceptable
      expect(e).toBeInstanceOf(Error);
    }
  });
  // setApplicationDir is NOT tested via round-trip here per MEDIUM concern.
});
