import { describe, test, expect } from "bun:test";
import {
  // Mod site functions
  getModSiteUrl,
  getModSiteName,
  getModSiteGameUrl,
  // User agent
  getUserAgent,
  getUserAgentWithSuffix,
  // URL validation
  validateUrl,
  isValidUrl,
  extractDomain,
  // URL building
  joinUrl,
  buildUrlWithQuery,
  // Constants
  getClassicVersion,
  getUserAgentPrefix,
} from "../index.js";

// ============================================================================
// Mod Site Functions
// ============================================================================

describe("Mod site functions", () => {
  describe("getModSiteUrl", () => {
    test("returns Nexus Mods base URL", () => {
      expect(getModSiteUrl("NexusMods")).toBe(
        "https://www.nexusmods.com",
      );
    });

    test("returns Bethesda.net base URL", () => {
      expect(getModSiteUrl("BethesdaNet")).toBe("https://bethesda.net");
    });

    test("returns ModDB base URL", () => {
      expect(getModSiteUrl("ModDB")).toBe("https://www.moddb.com");
    });
  });

  describe("getModSiteName", () => {
    test("returns Nexus Mods display name", () => {
      expect(getModSiteName("NexusMods")).toBe("Nexus Mods");
    });

    test("returns Bethesda.net display name", () => {
      expect(getModSiteName("BethesdaNet")).toBe("Bethesda.net");
    });

    test("returns ModDB display name", () => {
      expect(getModSiteName("ModDB")).toBe("ModDB");
    });
  });

  describe("getModSiteGameUrl", () => {
    test("returns Nexus Mods Fallout 4 URL", () => {
      expect(getModSiteGameUrl("NexusMods", "Fallout4")).toBe(
        "https://www.nexusmods.com/fallout4",
      );
    });

    test("returns Nexus Mods Skyrim URL", () => {
      expect(getModSiteGameUrl("NexusMods", "Skyrim")).toBe(
        "https://www.nexusmods.com/skyrimspecialedition",
      );
    });

    test("returns Nexus Mods Fallout 4 VR URL", () => {
      expect(getModSiteGameUrl("NexusMods", "Fallout4VR")).toBe(
        "https://www.nexusmods.com/fallout4vr",
      );
    });

    test("returns Nexus Mods Starfield URL", () => {
      expect(getModSiteGameUrl("NexusMods", "Starfield")).toBe(
        "https://www.nexusmods.com/starfield",
      );
    });

    test("returns Bethesda.net mods URL for any game", () => {
      expect(getModSiteGameUrl("BethesdaNet", "Fallout4")).toBe(
        "https://bethesda.net/mods",
      );
    });

    test("returns ModDB games URL for any game", () => {
      expect(getModSiteGameUrl("ModDB", "Fallout4")).toBe(
        "https://www.moddb.com/games",
      );
    });
  });
});

// ============================================================================
// User Agent
// ============================================================================

describe("User agent functions", () => {
  describe("getUserAgent", () => {
    test("returns a string starting with CLASSIC/", () => {
      const ua = getUserAgent();
      expect(ua).toStartWith("CLASSIC/");
    });

    test("contains the version number", () => {
      const ua = getUserAgent();
      expect(ua).toContain("8.0.0");
    });
  });

  describe("getUserAgentWithSuffix", () => {
    test("appends suffix in parentheses", () => {
      const ua = getUserAgentWithSuffix("Windows");
      expect(ua).toBe("CLASSIC/8.0.0 (Windows)");
    });

    test("handles empty suffix", () => {
      const ua = getUserAgentWithSuffix("");
      expect(ua).toBe("CLASSIC/8.0.0 ()");
    });

    test("handles suffix with spaces", () => {
      const ua = getUserAgentWithSuffix("Test Suite");
      expect(ua).toBe("CLASSIC/8.0.0 (Test Suite)");
    });
  });
});

// ============================================================================
// URL Validation
// ============================================================================

describe("URL validation", () => {
  describe("validateUrl", () => {
    test("accepts valid https URL", () => {
      const result = validateUrl("https://www.nexusmods.com");
      expect(typeof result).toBe("string");
      expect(result).toContain("nexusmods.com");
    });

    test("accepts valid http URL", () => {
      const result = validateUrl("http://example.com");
      expect(typeof result).toBe("string");
      expect(result).toContain("example.com");
    });

    test("throws on FTP URL", () => {
      expect(() => validateUrl("ftp://example.com")).toThrow();
    });

    test("throws on invalid URL", () => {
      expect(() => validateUrl("not a url")).toThrow();
    });

    test("throws on empty string", () => {
      expect(() => validateUrl("")).toThrow();
    });

    test("accepts URL with port", () => {
      const result = validateUrl("http://example.com:8080");
      expect(result).toContain("example.com");
    });

    test("accepts URL with path and query", () => {
      const result = validateUrl("https://example.com/path?q=1");
      expect(result).toContain("example.com");
    });
  });

  describe("isValidUrl", () => {
    test("returns true for valid https URL", () => {
      expect(isValidUrl("https://www.nexusmods.com")).toBe(true);
    });

    test("returns true for valid http URL", () => {
      expect(isValidUrl("http://example.com")).toBe(true);
    });

    test("returns false for FTP URL", () => {
      expect(isValidUrl("ftp://example.com")).toBe(false);
    });

    test("returns false for invalid URL", () => {
      expect(isValidUrl("not a url")).toBe(false);
    });

    test("returns false for empty string", () => {
      expect(isValidUrl("")).toBe(false);
    });

    test("returns false for URL without scheme", () => {
      expect(isValidUrl("www.example.com")).toBe(false);
    });

    test("returns false for javascript scheme", () => {
      expect(isValidUrl("javascript:alert(1)")).toBe(false);
    });

    test("returns true for localhost", () => {
      expect(isValidUrl("http://localhost")).toBe(true);
    });

    test("returns true for IP address", () => {
      expect(isValidUrl("http://192.168.1.1")).toBe(true);
    });
  });

  describe("extractDomain", () => {
    test("extracts domain from standard URL", () => {
      expect(extractDomain("https://www.nexusmods.com/fallout4")).toBe(
        "www.nexusmods.com",
      );
    });

    test("extracts domain from URL with port", () => {
      expect(extractDomain("http://example.com:8080/path")).toBe(
        "example.com",
      );
    });

    test("extracts subdomain", () => {
      expect(extractDomain("https://api.example.com/v1")).toBe(
        "api.example.com",
      );
    });

    test("extracts IP address as domain", () => {
      expect(extractDomain("http://192.168.1.1/path")).toBe("192.168.1.1");
    });

    test("throws on invalid URL", () => {
      expect(() => extractDomain("not a url")).toThrow();
    });

    test("throws on non-http scheme", () => {
      expect(() => extractDomain("ftp://example.com")).toThrow();
    });
  });
});

// ============================================================================
// URL Building
// ============================================================================

describe("URL building", () => {
  describe("joinUrl", () => {
    test("joins base URL with path", () => {
      const result = joinUrl("https://example.com", "path/to/resource");
      expect(result).toBe("https://example.com/path/to/resource");
    });

    test("handles trailing slash on base", () => {
      const result = joinUrl("https://example.com/", "path");
      expect(result).toContain("path");
    });

    test("handles leading slash on path", () => {
      const result = joinUrl("https://example.com", "/path");
      expect(result).toContain("path");
    });

    test("throws on invalid base URL", () => {
      expect(() => joinUrl("not a url", "path")).toThrow();
    });

    test("throws on non-http base URL", () => {
      expect(() => joinUrl("ftp://example.com", "path")).toThrow();
    });
  });

  describe("buildUrlWithQuery", () => {
    test("appends single query parameter", () => {
      const result = buildUrlWithQuery("https://example.com/search", [
        { key: "q", value: "test" },
      ]);
      expect(result).toBe("https://example.com/search?q=test");
    });

    test("appends multiple query parameters", () => {
      const result = buildUrlWithQuery("https://example.com/search", [
        { key: "page", value: "1" },
        { key: "sort", value: "popular" },
      ]);
      expect(result).toBe(
        "https://example.com/search?page=1&sort=popular",
      );
    });

    test("handles empty params array", () => {
      const result = buildUrlWithQuery("https://example.com/search", []);
      expect(result).toStartWith("https://example.com/search");
    });

    test("URL-encodes special characters in values", () => {
      const result = buildUrlWithQuery("https://example.com/search", [
        { key: "q", value: "hello world" },
      ]);
      expect(result).toContain("q=hello");
    });

    test("throws on invalid base URL", () => {
      expect(() =>
        buildUrlWithQuery("not a url", [{ key: "q", value: "test" }]),
      ).toThrow();
    });

    test("throws on non-http base URL", () => {
      expect(() =>
        buildUrlWithQuery("ftp://example.com", [
          { key: "q", value: "test" },
        ]),
      ).toThrow();
    });
  });
});

// ============================================================================
// Constants
// ============================================================================

describe("Web constants", () => {
  test("getClassicVersion returns a non-empty version string", () => {
    const version = getClassicVersion();
    expect(typeof version).toBe("string");
    expect(version.length).toBeGreaterThan(0);
    expect(version).toContain(".");
  });

  test("getUserAgentPrefix returns CLASSIC", () => {
    expect(getUserAgentPrefix()).toBe("CLASSIC");
  });
});
