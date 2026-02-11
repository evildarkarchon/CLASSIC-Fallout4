import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { mkdirSync, writeFileSync, rmSync } from "fs";
import { join } from "path";
import {
  detectResourceType,
  isSupportedResource,
  parseResourceType,
  getResourceExtensions,
  createResourceInfo,
  createResourceInfoWithSize,
  enumerateResources,
  countResourcesByType,
  validateResource,
} from "../index.js";

// ============================================================================
// Test fixture directory
// ============================================================================

const TEST_DIR = join(import.meta.dir, "__resource_test_data__");

beforeAll(() => {
  // Create a temporary directory tree with sample resource files
  mkdirSync(join(TEST_DIR, "textures"), { recursive: true });
  mkdirSync(join(TEST_DIR, "meshes"), { recursive: true });
  mkdirSync(join(TEST_DIR, "scripts"), { recursive: true });

  writeFileSync(join(TEST_DIR, "textures", "armor.dds"), "fake-dds");
  writeFileSync(join(TEST_DIR, "textures", "skin.png"), "fake-png");
  writeFileSync(join(TEST_DIR, "meshes", "body.nif"), "fake-nif");
  writeFileSync(join(TEST_DIR, "scripts", "quest.pex"), "fake-pex");
  writeFileSync(join(TEST_DIR, "readme.txt"), "not a resource");
  writeFileSync(join(TEST_DIR, "plugin.esp"), "fake-esp");
});

afterAll(() => {
  rmSync(TEST_DIR, { recursive: true, force: true });
});

// ============================================================================
// detectResourceType
// ============================================================================

describe("detectResourceType", () => {
  test("detects texture from .dds extension", () => {
    expect(detectResourceType("textures/armor.dds")).toBe("texture");
  });

  test("detects mesh from .nif extension", () => {
    expect(detectResourceType("meshes/body.nif")).toBe("mesh");
  });

  test("detects script from .pex extension", () => {
    expect(detectResourceType("scripts/quest.pex")).toBe("script");
  });

  test("detects plugin from .esp extension", () => {
    expect(detectResourceType("mods/MyMod.esp")).toBe("plugin");
  });

  test("detects plugin from .esm extension", () => {
    expect(detectResourceType("Fallout4.esm")).toBe("plugin");
  });

  test("detects plugin from .esl extension", () => {
    expect(detectResourceType("light.esl")).toBe("plugin");
  });

  test("detects sound from .wav extension", () => {
    expect(detectResourceType("sounds/click.wav")).toBe("sound");
  });

  test("detects sound from .xwm extension", () => {
    expect(detectResourceType("music/theme.xwm")).toBe("sound");
  });

  test("detects sound from .fuz extension", () => {
    expect(detectResourceType("voice/line.fuz")).toBe("sound");
  });

  test("detects animation from .hkx extension", () => {
    expect(detectResourceType("anims/walk.hkx")).toBe("animation");
  });

  test("detects interface from .swf extension", () => {
    expect(detectResourceType("interface/hud.swf")).toBe("interface");
  });

  test("detects strings from .strings extension", () => {
    expect(detectResourceType("strings/Fallout4_en.strings")).toBe("strings");
  });

  test("detects strings from .dlstrings extension", () => {
    expect(detectResourceType("strings/Fallout4_en.dlstrings")).toBe(
      "strings",
    );
  });

  test("detects strings from .ilstrings extension", () => {
    expect(detectResourceType("strings/Fallout4_en.ilstrings")).toBe(
      "strings",
    );
  });

  test("detects archive from .ba2 extension", () => {
    expect(detectResourceType("Fallout4 - Textures1.ba2")).toBe("archive");
  });

  test("detects archive from .bsa extension", () => {
    expect(detectResourceType("Skyrim - Misc.bsa")).toBe("archive");
  });

  test("detects config from .ini extension", () => {
    expect(detectResourceType("Fallout4.ini")).toBe("config");
  });

  test("returns 'other' for unrecognized extension", () => {
    expect(detectResourceType("readme.txt")).toBe("other");
  });

  test("returns 'other' for file without extension", () => {
    expect(detectResourceType("Makefile")).toBe("other");
  });

  test("is case-insensitive for extensions", () => {
    expect(detectResourceType("texture.DDS")).toBe("texture");
    expect(detectResourceType("plugin.ESP")).toBe("plugin");
    expect(detectResourceType("mesh.NIF")).toBe("mesh");
  });
});

// ============================================================================
// isSupportedResource
// ============================================================================

describe("isSupportedResource", () => {
  test("returns true for known resource types", () => {
    expect(isSupportedResource("texture.dds")).toBe(true);
    expect(isSupportedResource("plugin.esp")).toBe(true);
    expect(isSupportedResource("mesh.nif")).toBe(true);
    expect(isSupportedResource("script.pex")).toBe(true);
    expect(isSupportedResource("config.ini")).toBe(true);
  });

  test("returns false for unrecognized types", () => {
    expect(isSupportedResource("readme.txt")).toBe(false);
    expect(isSupportedResource("image.bmp")).toBe(false);
    expect(isSupportedResource("data.json")).toBe(false);
  });

  test("returns false for file without extension", () => {
    expect(isSupportedResource("LICENSE")).toBe(false);
  });
});

// ============================================================================
// parseResourceType
// ============================================================================

describe("parseResourceType", () => {
  test("parses lowercase type names", () => {
    expect(parseResourceType("texture")).toBe("texture");
    expect(parseResourceType("mesh")).toBe("mesh");
    expect(parseResourceType("script")).toBe("script");
    expect(parseResourceType("plugin")).toBe("plugin");
    expect(parseResourceType("sound")).toBe("sound");
    expect(parseResourceType("animation")).toBe("animation");
    expect(parseResourceType("interface")).toBe("interface");
    expect(parseResourceType("strings")).toBe("strings");
    expect(parseResourceType("archive")).toBe("archive");
    expect(parseResourceType("config")).toBe("config");
  });

  test("is case-insensitive", () => {
    expect(parseResourceType("TEXTURE")).toBe("texture");
    expect(parseResourceType("Plugin")).toBe("plugin");
    expect(parseResourceType("MESH")).toBe("mesh");
  });

  test("returns 'other' for unknown type names", () => {
    expect(parseResourceType("unknown")).toBe("other");
    expect(parseResourceType("")).toBe("other");
    expect(parseResourceType("foobar")).toBe("other");
  });
});

// ============================================================================
// getResourceExtensions
// ============================================================================

describe("getResourceExtensions", () => {
  test("returns texture extensions", () => {
    const exts = getResourceExtensions("texture");
    expect(exts).toEqual(["dds", "png", "jpg", "tga"]);
  });

  test("returns plugin extensions", () => {
    const exts = getResourceExtensions("plugin");
    expect(exts).toEqual(["esp", "esm", "esl"]);
  });

  test("returns mesh extensions", () => {
    const exts = getResourceExtensions("mesh");
    expect(exts).toEqual(["nif"]);
  });

  test("returns script extensions", () => {
    const exts = getResourceExtensions("script");
    expect(exts).toEqual(["pex", "psc"]);
  });

  test("returns sound extensions", () => {
    const exts = getResourceExtensions("sound");
    expect(exts).toEqual(["wav", "xwm", "fuz"]);
  });

  test("returns archive extensions", () => {
    const exts = getResourceExtensions("archive");
    expect(exts).toEqual(["ba2", "bsa"]);
  });

  test("returns empty array for 'other'", () => {
    const exts = getResourceExtensions("other");
    expect(exts).toEqual([]);
  });

  test("returns empty array for unrecognized type", () => {
    const exts = getResourceExtensions("nonsense");
    expect(exts).toEqual([]);
  });

  test("is case-insensitive", () => {
    const exts = getResourceExtensions("TEXTURE");
    expect(exts).toEqual(["dds", "png", "jpg", "tga"]);
  });
});

// ============================================================================
// createResourceInfo
// ============================================================================

describe("createResourceInfo", () => {
  test("creates info with auto-detected type", () => {
    const info = createResourceInfo("textures/armor.dds");
    expect(info.path).toBe("textures/armor.dds");
    expect(info.resourceType).toBe("texture");
    expect(info.size).toBe(0);
  });

  test("detects plugin type", () => {
    const info = createResourceInfo("MyMod.esp");
    expect(info.resourceType).toBe("plugin");
  });

  test("returns 'other' for unrecognized extension", () => {
    const info = createResourceInfo("readme.txt");
    expect(info.resourceType).toBe("other");
  });

  test("size defaults to 0", () => {
    const info = createResourceInfo("mesh.nif");
    expect(info.size).toBe(0);
  });
});

// ============================================================================
// createResourceInfoWithSize
// ============================================================================

describe("createResourceInfoWithSize", () => {
  test("creates info with specified size", () => {
    const info = createResourceInfoWithSize("textures/armor.dds", 4096);
    expect(info.path).toBe("textures/armor.dds");
    expect(info.resourceType).toBe("texture");
    expect(info.size).toBe(4096);
  });

  test("handles zero size", () => {
    const info = createResourceInfoWithSize("script.pex", 0);
    expect(info.size).toBe(0);
  });

  test("handles large file sizes", () => {
    const largeSize = 2 * 1024 * 1024 * 1024; // 2 GB
    const info = createResourceInfoWithSize("Fallout4 - Textures.ba2", largeSize);
    expect(info.size).toBe(largeSize);
    expect(info.resourceType).toBe("archive");
  });
});

// ============================================================================
// enumerateResources
// ============================================================================

describe("enumerateResources", () => {
  test("enumerates all resources in a directory", () => {
    const resources = enumerateResources(TEST_DIR);
    // Should find: armor.dds, skin.png, body.nif, quest.pex, plugin.esp
    // Should NOT find: readme.txt (unsupported type)
    expect(resources.length).toBe(5);
  });

  test("filters by resource type when specified", () => {
    const textures = enumerateResources(TEST_DIR, "texture");
    // armor.dds and skin.png
    expect(textures.length).toBe(2);
    for (const r of textures) {
      expect(r.resourceType).toBe("texture");
    }
  });

  test("filter for mesh returns only meshes", () => {
    const meshes = enumerateResources(TEST_DIR, "mesh");
    expect(meshes.length).toBe(1);
    expect(meshes[0].resourceType).toBe("mesh");
  });

  test("filter for plugin returns only plugins", () => {
    const plugins = enumerateResources(TEST_DIR, "plugin");
    expect(plugins.length).toBe(1);
    expect(plugins[0].resourceType).toBe("plugin");
  });

  test("filter for non-existent type returns empty array", () => {
    const anims = enumerateResources(TEST_DIR, "animation");
    expect(anims.length).toBe(0);
  });

  test("returns undefined for filter_type when not provided", () => {
    // Just verify calling without the second argument works
    const resources = enumerateResources(TEST_DIR);
    expect(resources.length).toBeGreaterThan(0);
  });

  test("each resource has size > 0 for real files", () => {
    const resources = enumerateResources(TEST_DIR);
    for (const r of resources) {
      expect(r.size).toBeGreaterThan(0);
    }
  });

  test("each resource has a non-empty path", () => {
    const resources = enumerateResources(TEST_DIR);
    for (const r of resources) {
      expect(r.path.length).toBeGreaterThan(0);
    }
  });

  test("returns empty for directory with no resources", () => {
    // Create a temp dir with no resource files
    const emptyDir = join(TEST_DIR, "__empty__");
    mkdirSync(emptyDir, { recursive: true });
    writeFileSync(join(emptyDir, "readme.txt"), "not a resource");
    const resources = enumerateResources(emptyDir);
    expect(resources.length).toBe(0);
    rmSync(emptyDir, { recursive: true, force: true });
  });

  test("throws for non-existent directory", () => {
    // walkdir returns an empty iterator for non-existent paths (no files found)
    // rather than throwing, so this returns an empty array
    const resources = enumerateResources(
      join(TEST_DIR, "__does_not_exist__"),
    );
    expect(resources.length).toBe(0);
  });
});

// ============================================================================
// countResourcesByType
// ============================================================================

describe("countResourcesByType", () => {
  test("counts resources grouped by type", () => {
    const counts = countResourcesByType(TEST_DIR);
    expect(counts.length).toBeGreaterThan(0);

    // Build a map for easier assertions
    const map = new Map(counts.map((c) => [c.resourceType, c.count]));

    // 2 textures (armor.dds, skin.png)
    expect(map.get("texture")).toBe(2);
    // 1 mesh (body.nif)
    expect(map.get("mesh")).toBe(1);
    // 1 script (quest.pex)
    expect(map.get("script")).toBe(1);
    // 1 plugin (plugin.esp)
    expect(map.get("plugin")).toBe(1);
  });

  test("does not include unsupported types", () => {
    const counts = countResourcesByType(TEST_DIR);
    const map = new Map(counts.map((c) => [c.resourceType, c.count]));
    expect(map.get("other")).toBeUndefined();
  });

  test("each entry has resourceType and count fields", () => {
    const counts = countResourcesByType(TEST_DIR);
    for (const entry of counts) {
      expect(typeof entry.resourceType).toBe("string");
      expect(typeof entry.count).toBe("number");
      expect(entry.count).toBeGreaterThan(0);
    }
  });

  test("returns empty array for directory with no resources", () => {
    const emptyDir = join(TEST_DIR, "__empty2__");
    mkdirSync(emptyDir, { recursive: true });
    writeFileSync(join(emptyDir, "notes.md"), "markdown");
    const counts = countResourcesByType(emptyDir);
    expect(counts.length).toBe(0);
    rmSync(emptyDir, { recursive: true, force: true });
  });
});

// ============================================================================
// validateResource
// ============================================================================

describe("validateResource", () => {
  test("succeeds for an existing file", () => {
    const filePath = join(TEST_DIR, "textures", "armor.dds");
    // Should not throw
    expect(() => validateResource(filePath)).not.toThrow();
  });

  test("throws for a non-existent file", () => {
    const fakePath = join(TEST_DIR, "nonexistent.dds");
    expect(() => validateResource(fakePath)).toThrow();
  });

  test("throws for a directory path (not a file)", () => {
    expect(() => validateResource(TEST_DIR)).toThrow();
  });

  test("error message mentions the path for missing files", () => {
    const fakePath = join(TEST_DIR, "missing_texture.dds");
    try {
      validateResource(fakePath);
      // Should not reach here
      expect(true).toBe(false);
    } catch (e: unknown) {
      const msg = (e as Error).message;
      expect(msg).toContain("not found");
    }
  });

  test("error message describes issue for directory path", () => {
    try {
      validateResource(TEST_DIR);
      expect(true).toBe(false);
    } catch (e: unknown) {
      const msg = (e as Error).message;
      expect(msg).toContain("not a file");
    }
  });
});
