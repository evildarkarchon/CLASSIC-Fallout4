import { afterEach, describe, expect, test } from "bun:test";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import { openUserSettings } from "../index.js";

const roots: string[] = [];
const fixtureRoot = join(
  import.meta.dir,
  "..",
  "..",
  "..",
  "tests",
  "fixtures",
  "user_settings_compatibility",
);

/** Creates an isolated CLASSIC root with optional byte-exact settings content. */
function makeRoot(
  settings?: string | Buffer,
  relativePath = "CLASSIC Settings.yaml",
): string {
  const root = mkdtempSync(join(tmpdir(), "classic-user-settings-node-"));
  roots.push(root);
  if (settings !== undefined) {
    const settingsPath = join(root, relativePath);
    mkdirSync(dirname(settingsPath), { recursive: true });
    writeFileSync(settingsPath, settings);
  }
  return root;
}

/** Reads one shared User Settings compatibility fixture as exact bytes. */
function fixture(name: string): Buffer {
  return readFileSync(join(fixtureRoot, name));
}

afterEach(() => {
  for (const root of roots.splice(0)) {
    rmSync(root, { recursive: true, force: true });
  }
});

describe("read-only User Settings", () => {
  test("user-settings-read-only-open", () => {
    const content = fixture("invalid_known_values.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");

    const snapshot = openUserSettings(root);

    expect(snapshot.updatePreferences.updateCheck).toBe(false);
    expect(snapshot.updatePreferences.origin).toBe("degradedFallback");
    expect(snapshot.sourceLocation).toBe("canonical");
    expect(snapshot.sourcePath).toBe(path);
    expect(snapshot.classification).toBe("current");
    expect(snapshot.schemaMajor).toBe(1);
    expect(snapshot.schemaMinor).toBe(0);
    expect(snapshot.commitEligibility).toBe("eligible");
    expect(snapshot.diagnostics.map((diagnostic) => diagnostic.code)).toEqual([
      "invalid_type_update_check",
    ]);
    expect(snapshot.diagnostics[0]?.message.length).toBeGreaterThan(0);
    expect(snapshot.revision.startsWith("sha256:")).toBe(true);
    expect(snapshot.originalContent?.equals(content)).toBe(true);
    expect(readFileSync(path).equals(content)).toBe(true);

    for (const [name, classification, updateCheck, origin, eligibility] of [
      ["canonical_current_nested.yaml", "current", true, "document", "eligible"],
      ["flat_classic_config.yaml", "legacyFlat", false, "document", "requiresMigration"],
      ["newer_major_schema.yaml", "futureMajor", false, "degradedFallback", "blockedUntrusted"],
      ["malformed.yaml", "malformed", false, "degradedFallback", "blockedUntrusted"],
    ] as const) {
      const caseSnapshot = openUserSettings(makeRoot(fixture(name)));
      expect(caseSnapshot.classification).toBe(classification);
      expect(caseSnapshot.updatePreferences.updateCheck).toBe(updateCheck);
      expect(caseSnapshot.updatePreferences.origin).toBe(origin);
      expect(caseSnapshot.commitEligibility).toBe(eligibility);
    }

    const legacyRoot = makeRoot(
      fixture("previous_location_nested.yaml"),
      join("CLASSIC Data", "CLASSIC Settings.yaml"),
    );
    const legacy = openUserSettings(legacyRoot);
    expect(legacy.sourceLocation).toBe("legacy");
    expect(legacy.commitEligibility).toBe("requiresMigration");

    const missing = openUserSettings(makeRoot());
    expect(missing.sourceLocation).toBe("missing");
    expect(missing.sourcePath).toBeUndefined();
    expect(missing.classification).toBe("missing");
    expect(missing.schemaMajor).toBeUndefined();
    expect(missing.schemaMinor).toBeUndefined();
    expect(missing.revision).toBe("missing");
    expect(missing.updatePreferences.updateCheck).toBe(true);
    expect(missing.updatePreferences.origin).toBe("default");
    expect(missing.originalContent).toBeUndefined();

    const invalidBytes = Buffer.from([0xff, 0xfe, 0xfd]);
    const invalidBytesSnapshot = openUserSettings(makeRoot(invalidBytes));
    expect(invalidBytesSnapshot.classification).toBe("malformed");
    expect(invalidBytesSnapshot.originalContent?.equals(invalidBytes)).toBe(true);
  });
});
