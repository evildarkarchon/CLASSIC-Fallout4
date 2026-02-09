import { describe, test, expect } from "bun:test";
import {
  yamlParse,
  yamlStringify,
  yamlGetStringValue,
  yamlGetVecValue,
} from "../index.js";

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
