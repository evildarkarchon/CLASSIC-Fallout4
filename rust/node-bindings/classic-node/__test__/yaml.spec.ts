import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { existsSync, unlinkSync, mkdirSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import {
  yamlParse,
  yamlStringify,
  yamlGetStringValue,
  yamlGetVecValue,
  yamlGetValue,
  yamlGetHashmapValue,
  yamlLoadFile,
  yamlSaveFile,
  yamlSetSetting,
  yamlGetSettingsBatch,
  yamlSetSettingsBatch,
  yamlGetIndexmapValue,
  yamlGetHashmapVecValue,
  yamlClearCache,
  yamlGetCacheStats,
  YamlDocument,
} from "../index.js";

// ---------------------------------------------------------------------------
// Existing free-function tests
// ---------------------------------------------------------------------------

describe("YAML bindings", () => {
  test("yamlParse parses simple YAML to JSON-compatible object", () => {
    const result = yamlParse("key: value\nnumber: 42\nflag: true");
    expect(result).toBeDefined();
    expect(result.key).toBe("value");
    expect(result.number).toBe(42);
    expect(result.flag).toBe(true);
  });

  test("yamlParse handles nested structures", () => {
    const yaml = "parent:\n  child: hello\n  list:\n    - one\n    - two";
    const result = yamlParse(yaml);
    expect(result.parent.child).toBe("hello");
    expect(result.parent.list).toEqual(["one", "two"]);
  });

  test("yamlParse returns null for null values", () => {
    const result = yamlParse("key: null");
    expect(result.key).toBeNull();
  });

  test("yamlStringify converts object back to YAML string", () => {
    const yaml = "key: value\n";
    const parsed = yamlParse(yaml);
    const result = yamlStringify(parsed);
    expect(typeof result).toBe("string");
    expect(result).toContain("key");
    expect(result).toContain("value");
  });

  test("yamlGetStringValue extracts nested string with dot notation", () => {
    const yaml = "game:\n  name: Fallout4\n  version: '1.10.163'";
    const result = yamlGetStringValue(yaml, "game.name", "Unknown");
    expect(result).toBe("Fallout4");
  });

  test("yamlGetStringValue returns default for missing key", () => {
    const yaml = "game:\n  name: Fallout4";
    const result = yamlGetStringValue(yaml, "game.missing", "default_val");
    expect(result).toBe("default_val");
  });

  test("yamlGetVecValue extracts string arrays", () => {
    const yaml = "plugins:\n  - plugin1.esp\n  - plugin2.esp";
    const result = yamlGetVecValue(yaml, "plugins");
    expect(result).toEqual(["plugin1.esp", "plugin2.esp"]);
  });

  test("yamlGetVecValue returns empty array for missing key", () => {
    const yaml = "key: value";
    const result = yamlGetVecValue(yaml, "missing");
    expect(result).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// yamlSaveFile / yamlLoadFile round-trip
// ---------------------------------------------------------------------------

describe("yamlSaveFile and yamlLoadFile", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = join(tmpdir(), `classic-yaml-test-${Date.now()}`);
    mkdirSync(tmpDir, { recursive: true });
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  test("round-trips data through a file", () => {
    const filePath = join(tmpDir, "round-trip.yaml");
    const data = { game: "Fallout4", version: 42, enabled: true };

    yamlSaveFile(filePath, data);
    expect(existsSync(filePath)).toBe(true);

    const loaded = yamlLoadFile(filePath);
    expect(loaded.game).toBe("Fallout4");
    expect(loaded.version).toBe(42);
    expect(loaded.enabled).toBe(true);
  });

  test("saves nested data correctly", () => {
    const filePath = join(tmpDir, "nested.yaml");
    const data = {
      settings: {
        debug: false,
        level: 10,
        tags: ["alpha", "beta"],
      },
    };

    yamlSaveFile(filePath, data);
    const loaded = yamlLoadFile(filePath);
    expect(loaded.settings.debug).toBe(false);
    expect(loaded.settings.level).toBe(10);
    expect(loaded.settings.tags).toEqual(["alpha", "beta"]);
  });
});

// ---------------------------------------------------------------------------
// yamlSetSetting
// ---------------------------------------------------------------------------

describe("yamlSetSetting", () => {
  const yaml = "game:\n  name: Fallout4\n  debug: false";

  test("sets an existing key to a new value", () => {
    const result = yamlSetSetting(yaml, "game.debug", true);
    expect(typeof result).toBe("string");
    // Verify the change stuck by re-parsing
    const parsed = yamlParse(result);
    expect(parsed.game.debug).toBe(true);
    // Original value preserved
    expect(parsed.game.name).toBe("Fallout4");
  });

  test("creates a new nested key", () => {
    const result = yamlSetSetting(yaml, "game.version", "1.10.163");
    const parsed = yamlParse(result);
    expect(parsed.game.version).toBe("1.10.163");
  });

  test("sets a value at a brand-new top-level path", () => {
    const result = yamlSetSetting(yaml, "newSection.key", 99);
    const parsed = yamlParse(result);
    expect(parsed.newSection.key).toBe(99);
  });

  test("throws on empty key path", () => {
    expect(() => yamlSetSetting(yaml, "", "value")).toThrow();
  });
});

// ---------------------------------------------------------------------------
// yamlGetSettingsBatch
// ---------------------------------------------------------------------------

describe("yamlGetSettingsBatch", () => {
  const yaml =
    "game:\n  name: Fallout4\n  version: '1.10'\nsettings:\n  debug: true";

  test("retrieves multiple settings at once", () => {
    const result = yamlGetSettingsBatch(yaml, [
      "game.name",
      "settings.debug",
    ]);
    expect(result["game.name"]).toBe("Fallout4");
    expect(result["settings.debug"]).toBe(true);
  });

  test("omits missing keys", () => {
    const result = yamlGetSettingsBatch(yaml, [
      "game.name",
      "game.missing",
    ]);
    expect(result["game.name"]).toBe("Fallout4");
    expect(result["game.missing"]).toBeUndefined();
  });

  test("returns empty object for all-missing keys", () => {
    const result = yamlGetSettingsBatch(yaml, ["no.such.key"]);
    expect(Object.keys(result).length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// yamlSetSettingsBatch
// ---------------------------------------------------------------------------

describe("yamlSetSettingsBatch", () => {
  const yaml =
    "game:\n  name: Fallout4\n  debug: false\nsettings:\n  level: 1";

  test("sets multiple settings at once", () => {
    const result = yamlSetSettingsBatch(yaml, {
      "game.debug": true,
      "settings.level": 42,
    });
    const parsed = yamlParse(result);
    expect(parsed.game.debug).toBe(true);
    expect(parsed.settings.level).toBe(42);
    // Untouched value preserved
    expect(parsed.game.name).toBe("Fallout4");
  });

  test("creates new keys in batch", () => {
    const result = yamlSetSettingsBatch(yaml, {
      "game.version": "1.10.163",
      "new.path": "hello",
    });
    const parsed = yamlParse(result);
    expect(parsed.game.version).toBe("1.10.163");
    expect(parsed.new.path).toBe("hello");
  });

  test("throws when settings is not an object", () => {
    expect(() => yamlSetSettingsBatch(yaml, "not an object" as any)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// yamlGetIndexmapValue
// ---------------------------------------------------------------------------

describe("yamlGetIndexmapValue", () => {
  test("returns a string-to-string record", () => {
    const yaml = "mods:\n  mod_a: Description A\n  mod_b: Description B";
    const result = yamlGetIndexmapValue(yaml, "mods");
    expect(result.mod_a).toBe("Description A");
    expect(result.mod_b).toBe("Description B");
  });

  test("returns all key-value pairs", () => {
    const yaml =
      "items:\n  zebra: z\n  apple: a\n  mango: m";
    const result = yamlGetIndexmapValue(yaml, "items");
    const keys = Object.keys(result);
    expect(keys.length).toBe(3);
    expect(result.zebra).toBe("z");
    expect(result.apple).toBe("a");
    expect(result.mango).toBe("m");
  });

  test("returns empty object for missing key path", () => {
    const yaml = "key: value";
    const result = yamlGetIndexmapValue(yaml, "missing");
    expect(Object.keys(result).length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// yamlGetHashmapVecValue
// ---------------------------------------------------------------------------

describe("yamlGetHashmapVecValue", () => {
  test("extracts map with array values", () => {
    const yaml =
      "checks:\n  crash_a:\n    - pattern1\n    - pattern2\n  crash_b:\n    - pattern3";
    const result = yamlGetHashmapVecValue(yaml, "checks");
    expect(result.crash_a).toEqual(["pattern1", "pattern2"]);
    expect(result.crash_b).toEqual(["pattern3"]);
  });

  test("wraps single string values into arrays", () => {
    const yaml = "checks:\n  simple_crash: single_pattern";
    const result = yamlGetHashmapVecValue(yaml, "checks");
    expect(result.simple_crash).toEqual(["single_pattern"]);
  });

  test("returns empty object for missing key path", () => {
    const yaml = "key: value";
    const result = yamlGetHashmapVecValue(yaml, "missing");
    expect(Object.keys(result).length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// yamlClearCache & yamlGetCacheStats
// ---------------------------------------------------------------------------

describe("yamlClearCache and yamlGetCacheStats", () => {
  test("yamlGetCacheStats returns an object with expected fields", () => {
    const stats = yamlGetCacheStats();
    expect(typeof stats.cachedFiles).toBe("number");
    expect(typeof stats.totalBytes).toBe("number");
  });

  test("yamlClearCache does not throw", () => {
    expect(() => yamlClearCache()).not.toThrow();
  });

  test("cache stats after clear shows zero or unchanged", () => {
    yamlClearCache();
    const stats = yamlGetCacheStats();
    expect(stats.cachedFiles).toBe(0);
    expect(stats.totalBytes).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// YamlDocument class
// ---------------------------------------------------------------------------

describe("YamlDocument class", () => {
  const yamlContent =
    "game:\n  name: Fallout4\n  version: '1.10.163'\n  debug: false\n  plugins:\n    - plugin1.esp\n    - plugin2.esp\n  mods:\n    mod_a: Desc A\n    mod_b: Desc B";

  test("constructor parses valid YAML", () => {
    const doc = new YamlDocument(yamlContent);
    expect(doc).toBeDefined();
  });

  test("constructor throws on invalid YAML", () => {
    // Unbalanced mapping colon sequences are invalid
    expect(() => new YamlDocument(":\n  :\n    :\n [invalid")).toThrow();
  });

  test("getValue retrieves nested values", () => {
    const doc = new YamlDocument(yamlContent);
    expect(doc.getValue("game.name")).toBe("Fallout4");
    expect(doc.getValue("game.debug")).toBe(false);
  });

  test("getValue returns null for missing key", () => {
    const doc = new YamlDocument(yamlContent);
    expect(doc.getValue("game.nonexistent")).toBeNull();
  });

  test("getStringValue retrieves string with default", () => {
    const doc = new YamlDocument(yamlContent);
    expect(doc.getStringValue("game.name", "Unknown")).toBe("Fallout4");
    expect(doc.getStringValue("game.missing", "fallback")).toBe("fallback");
  });

  test("getVecValue retrieves arrays", () => {
    const doc = new YamlDocument(yamlContent);
    expect(doc.getVecValue("game.plugins")).toEqual([
      "plugin1.esp",
      "plugin2.esp",
    ]);
  });

  test("getVecValue returns empty array for missing key", () => {
    const doc = new YamlDocument(yamlContent);
    expect(doc.getVecValue("game.missing")).toEqual([]);
  });

  test("getHashmapValue retrieves string-to-string maps", () => {
    const doc = new YamlDocument(yamlContent);
    const mods = doc.getHashmapValue("game.mods");
    expect(mods.mod_a).toBe("Desc A");
    expect(mods.mod_b).toBe("Desc B");
  });

  test("getHashmapValue returns empty object for missing key", () => {
    const doc = new YamlDocument(yamlContent);
    const result = doc.getHashmapValue("game.missing");
    expect(Object.keys(result).length).toBe(0);
  });

  test("setValue mutates internal state", () => {
    const doc = new YamlDocument(yamlContent);
    doc.setValue("game.debug", true);
    expect(doc.getValue("game.debug")).toBe(true);
    // Other values unaffected
    expect(doc.getValue("game.name")).toBe("Fallout4");
  });

  test("setValue creates new keys", () => {
    const doc = new YamlDocument(yamlContent);
    doc.setValue("game.newKey", "newValue");
    expect(doc.getValue("game.newKey")).toBe("newValue");
  });

  test("setValue throws on empty key path", () => {
    const doc = new YamlDocument(yamlContent);
    expect(() => doc.setValue("", "value")).toThrow();
  });

  test("toString serializes back to valid YAML", () => {
    const doc = new YamlDocument(yamlContent);
    const output = doc.toString();
    expect(typeof output).toBe("string");
    expect(output).toContain("Fallout4");
    expect(output).toContain("plugin1.esp");
  });

  test("round-trip: parse -> mutate -> toString -> re-parse preserves data", () => {
    const doc = new YamlDocument(yamlContent);
    doc.setValue("game.debug", true);
    doc.setValue("game.level", 99);

    const serialized = doc.toString();
    const doc2 = new YamlDocument(serialized);

    expect(doc2.getValue("game.debug")).toBe(true);
    expect(doc2.getValue("game.level")).toBe(99);
    expect(doc2.getValue("game.name")).toBe("Fallout4");
    expect(doc2.getVecValue("game.plugins")).toEqual([
      "plugin1.esp",
      "plugin2.esp",
    ]);
  });

  test("setValue with complex types (arrays, objects)", () => {
    const doc = new YamlDocument("root:\n  key: old");
    doc.setValue("root.list", ["a", "b", "c"]);
    const list = doc.getValue("root.list");
    expect(list).toEqual(["a", "b", "c"]);

    doc.setValue("root.nested", { x: 1, y: 2 });
    const nested = doc.getValue("root.nested");
    expect(nested.x).toBe(1);
    expect(nested.y).toBe(2);
  });
});
