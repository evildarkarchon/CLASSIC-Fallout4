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

import { openUserSettings, previewUserSettingsUpdate } from "../index.js";

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
      "invalid_enum_game_version",
      "invalid_type_move_unsolved_logs",
      "invalid_path_unsolved_logs_destination",
      "invalid_path_custom_scan_input",
      "invalid_range_max_concurrent_scans",
      "invalid_value_formid_databases",
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

describe("Crash Log Scan User Settings", () => {
  test("user-settings-crash-log-scan-snapshot", () => {
    const canonicalContent = fixture("canonical_current_nested.yaml");
    const canonicalRoot = makeRoot(canonicalContent);
    const canonical = openUserSettings(canonicalRoot);

    expect(canonical.crashLogScanSettings).toEqual({
      fcxMode: false,
      fcxModeOrigin: "document",
      simplifyLogs: false,
      simplifyLogsOrigin: "document",
      showStatistics: false,
      showStatisticsOrigin: "document",
      formidValueLookup: false,
      formidValueLookupOrigin: "document",
      formidDatabases: {
        Fallout4: ["databases/Fallout4 FormIDs.db"],
      },
      formidDatabasesOrigin: "document",
      moveUnsolvedLogs: true,
      moveUnsolvedLogsOrigin: "document",
      unsolvedLogsDestinationOrigin: "document",
      customScanInputOrigin: "document",
      gameVersionSelection: "auto",
      gameVersionSelectionOrigin: "document",
      maxConcurrentScans: 0,
      maxConcurrentScansOrigin: "document",
    });
    expect(readFileSync(join(canonicalRoot, "CLASSIC Settings.yaml"))).toEqual(
      canonicalContent,
    );

    const aliasContent = fixture("alias_only.yaml");
    const aliasRoot = makeRoot(aliasContent);
    const alias = openUserSettings(aliasRoot);
    expect(alias.crashLogScanSettings.customScanInput).toBe(
      "E:/Alias Crash Logs",
    );
    expect(alias.crashLogScanSettings.customScanInputOrigin).toBe("document");
    expect(alias.crashLogScanSettings.moveUnsolvedLogs).toBe(true);
    expect(alias.crashLogScanSettings.moveUnsolvedLogsOrigin).toBe("default");
    expect(alias.diagnostics).toEqual([]);
    expect(readFileSync(join(aliasRoot, "CLASSIC Settings.yaml"))).toEqual(
      aliasContent,
    );

    const conflict = openUserSettings(
      makeRoot(fixture("canonical_alias_conflict.yaml")),
    );
    expect(conflict.crashLogScanSettings.customScanInput).toBe(
      "D:/Canonical Crash Logs",
    );
    expect(conflict.diagnostics.map((diagnostic) => diagnostic.code)).toEqual([
      "canonical_alias_conflict_mods_folder",
      "canonical_alias_conflict_custom_scan_folder",
    ]);

    const invalidContent = fixture("invalid_known_values.yaml");
    const invalidRoot = makeRoot(invalidContent);
    const invalid = openUserSettings(invalidRoot);
    expect(invalid.crashLogScanSettings.gameVersionSelection).toBe("auto");
    expect(invalid.crashLogScanSettings.gameVersionSelectionOrigin).toBe(
      "degradedFallback",
    );
    expect(invalid.crashLogScanSettings.moveUnsolvedLogs).toBe(false);
    expect(invalid.crashLogScanSettings.moveUnsolvedLogsOrigin).toBe(
      "degradedFallback",
    );
    expect(invalid.crashLogScanSettings.unsolvedLogsDestination).toBeUndefined();
    expect(invalid.crashLogScanSettings.unsolvedLogsDestinationOrigin).toBe(
      "degradedFallback",
    );
    expect(invalid.crashLogScanSettings.customScanInput).toBeUndefined();
    expect(invalid.crashLogScanSettings.customScanInputOrigin).toBe(
      "degradedFallback",
    );
    expect(invalid.crashLogScanSettings.formidDatabases).toEqual({});
    expect(invalid.crashLogScanSettings.formidDatabasesOrigin).toBe(
      "degradedFallback",
    );
    expect(invalid.crashLogScanSettings.maxConcurrentScans).toBe(0);
    expect(invalid.crashLogScanSettings.maxConcurrentScansOrigin).toBe(
      "degradedFallback",
    );
    expect(readFileSync(join(invalidRoot, "CLASSIC Settings.yaml"))).toEqual(
      invalidContent,
    );

    const unknownContent = fixture("unknown_entries.yaml");
    const unknownRoot = makeRoot(unknownContent);
    const unknown = openUserSettings(unknownRoot);
    expect(unknown.crashLogScanSettings.gameVersionSelection).toBe("auto");
    expect(readFileSync(join(unknownRoot, "CLASSIC Settings.yaml"))).toEqual(
      unknownContent,
    );
  });
});

describe("Game Setup User Settings", () => {
  test("user-settings-game-setup-snapshot", () => {
    const content = `schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4 VR
  Game Version: VR
  Game Folder Path: C:/Games/Fallout4VR
  Game EXE Path: C:/Games/Fallout4VR/Fallout4VR.exe
  Documents Folder Path: C:/Users/Player/Documents/My Games/Fallout4VR
  INI Folder Path: D:/Overrides/Fallout4VR
  MODS Folder Path: E:/Staging/Fallout4VR
  SCAN Custom Path: F:/Crash Logs
  Papyrus Log Path: C:/Users/Player/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log
`;
    const snapshot = openUserSettings(makeRoot(content));

    expect(snapshot.gameSetupSettings).toEqual({
      managedGame: "Fallout4VR",
      managedGameOrigin: "document",
      gameVersionSelection: "VR",
      gameVersionSelectionOrigin: "document",
      gameRoot: "C:/Games/Fallout4VR",
      gameRootOrigin: "document",
      gameExecutable: "C:/Games/Fallout4VR/Fallout4VR.exe",
      gameExecutableOrigin: "document",
      documentsRoot: "C:/Users/Player/Documents/My Games/Fallout4VR",
      documentsRootOrigin: "document",
      iniFolder: "D:/Overrides/Fallout4VR",
      iniFolderOrigin: "document",
      modsRoot: "E:/Staging/Fallout4VR",
      modsRootOrigin: "document",
      customScanInput: "F:/Crash Logs",
      customScanInputOrigin: "document",
      papyrusLog:
        "C:/Users/Player/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log",
      papyrusLogOrigin: "document",
    });
  });
});

describe("User Settings Update preview", () => {
  test("user-settings-update-preview", () => {
    const content = fixture("unknown_entries.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const revision = openUserSettings(root).revision;

    const accepted = previewUserSettingsUpdate(root, {
      updateCheck: false,
      unsolvedLogsDestination: null,
      customScanInput: null,
      maxConcurrentScans: 4,
    });

    expect(accepted).toEqual({
      accepted: true,
      baseRevision: revision,
      fields: [
        {
          fieldPath: "/CLASSIC_Settings/Update Check",
          value: false,
        },
        {
          fieldPath: "/CLASSIC_Settings/Unsolved Logs Destination",
          value: null,
        },
        {
          fieldPath: "/CLASSIC_Settings/SCAN Custom Path",
          value: null,
        },
        {
          fieldPath: "/CLASSIC_Settings/Max Concurrent Scans",
          value: 4,
        },
      ],
      diagnostics: [],
    });
    expect(readFileSync(path)).toEqual(content);

    const gameSetupAccepted = previewUserSettingsUpdate(root, {
      managedGame: "Starfield",
      gameRoot: "C:/Games/Starfield",
      gameExecutable: "C:/Games/Starfield/Starfield.exe",
      documentsRoot: "C:/Users/Player/Documents/My Games/Starfield",
      iniFolder: null,
      modsFolder: "D:/Mod Staging/Starfield",
      papyrusLogPath: null,
    });
    expect(gameSetupAccepted.fields).toEqual([
      {
        fieldPath: "/CLASSIC_Settings/Managed Game",
        value: "Starfield",
      },
      {
        fieldPath: "/CLASSIC_Settings/Game Folder Path",
        value: "C:/Games/Starfield",
      },
      {
        fieldPath: "/CLASSIC_Settings/Game EXE Path",
        value: "C:/Games/Starfield/Starfield.exe",
      },
      {
        fieldPath: "/CLASSIC_Settings/Documents Folder Path",
        value: "C:/Users/Player/Documents/My Games/Starfield",
      },
      {
        fieldPath: "/CLASSIC_Settings/INI Folder Path",
        value: null,
      },
      {
        fieldPath: "/CLASSIC_Settings/MODS Folder Path",
        value: "D:/Mod Staging/Starfield",
      },
      {
        fieldPath: "/CLASSIC_Settings/Papyrus Log Path",
        value: null,
      },
    ]);
    expect(gameSetupAccepted.diagnostics).toEqual([]);
    expect(readFileSync(path)).toEqual(content);

    const rejected = previewUserSettingsUpdate(root, {
      updateCheck: true,
      gameVersionSelection: "Future",
      maxConcurrentScans: -9,
    });

    expect(rejected.accepted).toBe(false);
    expect(rejected.baseRevision).toBeUndefined();
    expect(rejected.fields).toEqual([]);
    expect(rejected.diagnostics).toEqual([
      {
        fieldPath: "/CLASSIC_Settings/Game Version",
        code: "invalid_enum_game_version",
        message:
          "Game Version must be auto, Original, NextGen, AnniversaryEdition, or VR",
      },
      {
        fieldPath: "/CLASSIC_Settings/Max Concurrent Scans",
        code: "invalid_range_max_concurrent_scans",
        message: "Max Concurrent Scans must be between 0 and 32",
      },
    ]);
    expect(readFileSync(path)).toEqual(content);

    const wideNumberRejected = previewUserSettingsUpdate(root, {
      updateCheck: true,
      maxConcurrentScans: 2 ** 32,
    });
    expect(wideNumberRejected.accepted).toBe(false);
    expect(wideNumberRejected.fields).toEqual([]);
    expect(wideNumberRejected.diagnostics.map(({ code }) => code)).toEqual([
      "invalid_range_max_concurrent_scans",
    ]);
    expect(readFileSync(path)).toEqual(content);

    const conflictContent = fixture("canonical_alias_conflict.yaml");
    const conflictRoot = makeRoot(conflictContent);
    const aliasPreserving = previewUserSettingsUpdate(conflictRoot, {
      maxConcurrentScans: 4,
    });
    expect(aliasPreserving.fields).toEqual([
      {
        fieldPath: "/CLASSIC_Settings/Max Concurrent Scans",
        value: 4,
      },
    ]);
    expect(
      readFileSync(join(conflictRoot, "CLASSIC Settings.yaml")),
    ).toEqual(conflictContent);
  });
});
