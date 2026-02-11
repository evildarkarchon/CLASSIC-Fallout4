import { describe, test, expect } from "bun:test";
import {
  GithubClient,
  hasUpdate,
  // Async functions exist but will fail without network; we test they are callable
  getLatestRelease,
  checkForUpdates,
} from "../index.js";

// ============================================================================
// GithubClient class
// ============================================================================

describe("GithubClient", () => {
  // ── Constructor ─────────────────────────────────────────────────────────

  describe("constructor", () => {
    test("creates a client with owner and repo", () => {
      const client = new GithubClient("evildarkarchon", "CLASSIC-Fallout4");
      expect(client.owner).toBe("evildarkarchon");
      expect(client.repo).toBe("CLASSIC-Fallout4");
    });

    test("creates a client with explicit token", () => {
      const client = new GithubClient("owner", "repo", "ghp_faketoken");
      expect(client.owner).toBe("owner");
      expect(client.repo).toBe("repo");
    });

    test("creates a client with undefined token (falls back to env)", () => {
      const client = new GithubClient("owner", "repo", undefined);
      expect(client.owner).toBe("owner");
    });

    test("treats empty string token as undefined", () => {
      // Empty token should be filtered out, behaving like no token
      const client = new GithubClient("owner", "repo", "");
      expect(client.owner).toBe("owner");
    });
  });

  // ── Getters ─────────────────────────────────────────────────────────────

  describe("getters", () => {
    test("owner returns the repository owner", () => {
      const client = new GithubClient("testowner", "testrepo");
      expect(client.owner).toBe("testowner");
    });

    test("repo returns the repository name", () => {
      const client = new GithubClient("testowner", "testrepo");
      expect(client.repo).toBe("testrepo");
    });
  });

  // ── repoUrl ─────────────────────────────────────────────────────────────

  describe("repoUrl", () => {
    test("returns the full GitHub URL", () => {
      const client = new GithubClient("evildarkarchon", "CLASSIC-Fallout4");
      expect(client.repoUrl()).toBe(
        "https://github.com/evildarkarchon/CLASSIC-Fallout4",
      );
    });

    test("constructs URL from various owner/repo combinations", () => {
      const cases = [
        ["user", "repo", "https://github.com/user/repo"],
        [
          "org-name",
          "project_name",
          "https://github.com/org-name/project_name",
        ],
        ["owner123", "repo456", "https://github.com/owner123/repo456"],
      ] as const;

      for (const [owner, repo, expected] of cases) {
        const client = new GithubClient(owner, repo);
        expect(client.repoUrl()).toBe(expected);
      }
    });
  });

  // ── hasUpdate (instance method) ─────────────────────────────────────────

  describe("hasUpdate (method)", () => {
    const client = new GithubClient("test", "repo");

    test("returns true when latest > current", () => {
      expect(client.hasUpdate("8.0.0", "8.1.0")).toBe(true);
      expect(client.hasUpdate("v8.0.0", "v9.0.0")).toBe(true);
      expect(client.hasUpdate("1.0.0", "1.0.1")).toBe(true);
    });

    test("returns false when latest == current", () => {
      expect(client.hasUpdate("8.0.0", "8.0.0")).toBe(false);
      expect(client.hasUpdate("v1.2.3", "v1.2.3")).toBe(false);
    });

    test("returns false when latest < current", () => {
      expect(client.hasUpdate("9.0.0", "8.0.0")).toBe(false);
      expect(client.hasUpdate("v2.0.0", "v1.9.9")).toBe(false);
    });

    test("handles v prefix consistently", () => {
      expect(client.hasUpdate("v8.0.0", "8.1.0")).toBe(true);
      expect(client.hasUpdate("8.0.0", "v8.1.0")).toBe(true);
    });

    test("handles pre-release versions", () => {
      // Pre-release < release of same version
      expect(client.hasUpdate("1.0.0-alpha", "1.0.0")).toBe(true);
      expect(client.hasUpdate("1.0.0-beta", "1.0.0")).toBe(true);

      // Alpha < beta
      expect(client.hasUpdate("1.0.0-alpha", "1.0.0-beta")).toBe(true);
    });

    test("throws on invalid current version", () => {
      expect(() => client.hasUpdate("invalid", "1.0.0")).toThrow();
    });

    test("throws on invalid latest version", () => {
      expect(() => client.hasUpdate("1.0.0", "invalid")).toThrow();
    });

    test("throws on empty version strings", () => {
      expect(() => client.hasUpdate("", "1.0.0")).toThrow();
      expect(() => client.hasUpdate("1.0.0", "")).toThrow();
    });

    test("throws on both invalid", () => {
      expect(() => client.hasUpdate("bad", "also_bad")).toThrow();
    });
  });

  // ── getLatestRelease (async, network-dependent) ─────────────────────────

  describe("getLatestRelease", () => {
    test("is a function on the client", () => {
      const client = new GithubClient("test", "repo");
      expect(typeof client.getLatestRelease).toBe("function");
    });

    test("returns a promise", () => {
      const client = new GithubClient("test", "repo");
      const result = client.getLatestRelease();
      expect(result).toBeInstanceOf(Promise);
      // Suppress unhandled rejection -- we just want to verify it returns a Promise
      result.catch(() => {});
    });
  });

  // ── getAllReleases (async, network-dependent) ───────────────────────────

  describe("getAllReleases", () => {
    test("is a function on the client", () => {
      const client = new GithubClient("test", "repo");
      expect(typeof client.getAllReleases).toBe("function");
    });

    test("returns a promise", () => {
      const client = new GithubClient("test", "repo");
      const result = client.getAllReleases();
      expect(result).toBeInstanceOf(Promise);
      result.catch(() => {});
    });

    test("accepts optional boolean parameters", () => {
      const client = new GithubClient("test", "repo");
      // Should not throw for valid parameter combinations
      const r1 = client.getAllReleases(true, false);
      const r2 = client.getAllReleases(false, true);
      const r3 = client.getAllReleases(true, true);
      r1.catch(() => {});
      r2.catch(() => {});
      r3.catch(() => {});
    });
  });
});

// ============================================================================
// Free functions
// ============================================================================

describe("Update free functions", () => {
  // ── hasUpdate (free function) ──────────────────────────────────────────

  describe("hasUpdate", () => {
    test("returns true when latest > current", () => {
      expect(hasUpdate("8.0.0", "8.1.0")).toBe(true);
      expect(hasUpdate("v1.0.0", "v2.0.0")).toBe(true);
    });

    test("returns false when versions are equal", () => {
      expect(hasUpdate("8.0.0", "8.0.0")).toBe(false);
    });

    test("returns false when latest < current", () => {
      expect(hasUpdate("9.0.0", "8.0.0")).toBe(false);
    });

    test("handles v prefix", () => {
      expect(hasUpdate("v8.0.0", "v8.1.0")).toBe(true);
      expect(hasUpdate("v8.0.0", "8.1.0")).toBe(true);
      expect(hasUpdate("8.0.0", "v8.1.0")).toBe(true);
    });

    test("handles patch version updates", () => {
      expect(hasUpdate("1.0.0", "1.0.1")).toBe(true);
      expect(hasUpdate("1.0.1", "1.0.2")).toBe(true);
      expect(hasUpdate("1.0.2", "1.0.1")).toBe(false);
    });

    test("handles minor version updates", () => {
      expect(hasUpdate("1.0.0", "1.1.0")).toBe(true);
      expect(hasUpdate("1.0.9", "1.1.0")).toBe(true);
    });

    test("handles major version updates", () => {
      expect(hasUpdate("1.9.9", "2.0.0")).toBe(true);
      expect(hasUpdate("2.0.0", "1.9.9")).toBe(false);
    });

    test("handles pre-release versions", () => {
      expect(hasUpdate("1.0.0-alpha", "1.0.0")).toBe(true);
      expect(hasUpdate("1.0.0-alpha", "1.0.0-beta")).toBe(true);
      expect(hasUpdate("1.0.0-rc.1", "1.0.0")).toBe(true);
    });

    test("throws on invalid version strings", () => {
      expect(() => hasUpdate("invalid", "1.0.0")).toThrow();
      expect(() => hasUpdate("1.0.0", "invalid")).toThrow();
      expect(() => hasUpdate("", "1.0.0")).toThrow();
      expect(() => hasUpdate("1.0.0", "")).toThrow();
      expect(() => hasUpdate("not_semver", "also_not")).toThrow();
    });
  });

  // ── getLatestRelease (free function) ───────────────────────────────────

  describe("getLatestRelease", () => {
    test("is a function", () => {
      expect(typeof getLatestRelease).toBe("function");
    });

    test("returns a promise", () => {
      const result = getLatestRelease("test", "nonexistent-repo-12345");
      expect(result).toBeInstanceOf(Promise);
      result.catch(() => {});
    });
  });

  // ── checkForUpdates (free function) ────────────────────────────────────

  describe("checkForUpdates", () => {
    test("is a function", () => {
      expect(typeof checkForUpdates).toBe("function");
    });

    test("returns a promise", () => {
      const result = checkForUpdates(
        "test",
        "nonexistent-repo-12345",
        "1.0.0",
      );
      expect(result).toBeInstanceOf(Promise);
      result.catch(() => {});
    });
  });
});
