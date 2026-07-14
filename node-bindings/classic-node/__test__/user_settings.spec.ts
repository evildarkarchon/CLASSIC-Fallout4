import { afterEach, describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import {
  applyUserSettingsMigration,
  commitUserSettingsBootstrap,
  commitUserSettingsUpdate,
  openUserSettings,
  planUserSettingsMigration,
  publishedUserSettingsDefaults,
  previewUserSettingsBootstrap,
  previewUserSettingsUpdate,
  reverseUserSettingsMigrationPlan,
} from "../index.js";

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
  test("user-settings-published-defaults", () => {
    const snapshot = publishedUserSettingsDefaults();

    expect(snapshot.sourceLocation).toBe("missing");
    expect(snapshot.sourcePath).toBeUndefined();
    expect(snapshot.classification).toBe("missing");
    expect(snapshot.revision).toBe("missing");
    expect(snapshot.commitEligibility).toBe("eligible");
    expect(snapshot.diagnostics).toEqual([]);
    expect(snapshot.originalContent).toBeUndefined();
    expect(snapshot.updatePreferences).toEqual({
      updateCheck: true,
      origin: "default",
      updateSource: "GitHub",
      updateSourceOrigin: "default",
    });
    expect(snapshot.crashLogScanSettings.moveUnsolvedLogs).toBe(true);
    expect(snapshot.crashLogScanSettings.moveUnsolvedLogsOrigin).toBe(
      "default",
    );
    expect(snapshot.gameSetupSettings.managedGame).toBe("Fallout4");
    expect(snapshot.gameSetupSettings.managedGameOrigin).toBe("default");
    expect(snapshot.frontendState.preferences.autoSwitchAfterScan).toBe(true);
    expect(
      snapshot.frontendState.preferences.autoSwitchAfterScanOrigin,
    ).toBe("default");
  });

  test("user-settings-update-source-snapshot", () => {
    const snapshot = openUserSettings(
      makeRoot(fixture("canonical_current_nested.yaml")),
    );

    expect(snapshot.updatePreferences.updateSource).toBe("GitHub");
    expect(snapshot.updatePreferences.updateSourceOrigin).toBe("document");

    const missing = openUserSettings(makeRoot());
    expect(missing.updatePreferences.updateSource).toBe("GitHub");
    expect(missing.updatePreferences.updateSourceOrigin).toBe("default");

    const invalid = openUserSettings(
      makeRoot(`schema_version: "1.0"
CLASSIC_Settings:
  Update Source: Nexus
`),
    );
    expect(invalid.updatePreferences.updateSource).toBe("GitHub");
    expect(invalid.updatePreferences.updateSourceOrigin).toBe(
      "degradedFallback",
    );
    expect(invalid.diagnostics.map(({ code }) => code)).toContain(
      "invalid_value_update_source",
    );
  });

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
      "invalid_type_gui_geometry_width",
      "invalid_type_gui_geometry_maximized",
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

describe("User Settings migration planning", () => {
  test("user-settings-migration-planning-current-document", () => {
    const content = fixture("canonical_current_nested.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");

    const result = planUserSettingsMigration(root);

    expect(result).toEqual({
      status: "notRequired",
      diagnostics: [],
    });
    expect(readFileSync(path)).toEqual(content);
  });

  test("user-settings-migration-planning-flat-document", () => {
    const content = fixture("flat_classic_config.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const revision = openUserSettings(root).revision;

    const result = planUserSettingsMigration(root);

    expect(result.status).toBe("planned");
    expect(result.diagnostics).toEqual([]);
    expect(result.plan?.required).toBe(true);
    expect(result.plan?.baseRevision).toBe(revision);
    expect(result.plan?.source).toEqual({
      location: "canonical",
    });
    expect(result.plan?.target).toEqual({
      location: "canonical",
      schemaVersion: { major: 1, minor: 0 },
    });
    expect(result.plan?.changes[0]).toEqual({
      kind: "schemaVersionTransition",
      targetPath: "/schema_version",
      after: "1.0",
    });
    expect(result.plan?.changes).toContainEqual({
      kind: "fieldTransition",
      sourcePath: "/fcx_mode",
      targetPath: "/CLASSIC_Settings/FCX Mode",
      before: "---\ntrue",
      after: "---\ntrue",
    });
    expect(result.plan?.originalContent).toEqual(content);
    expect(result.plan?.proposedContent.toString("utf8")).toContain(
      'schema_version: "1.0"',
    );
    expect(result.plan?.proposedContent.toString("utf8")).toContain(
      "CLASSIC_Settings:",
    );
    expect(readFileSync(path)).toEqual(content);
  });

  test("user-settings-migration-planning-unsupported-document", () => {
    const content = fixture("newer_major_schema.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");

    const result = planUserSettingsMigration(root);

    expect(result.status).toBe("unsupported");
    expect(result.plan).toBeUndefined();
    expect(result.diagnostics.map(({ code }) => code)).toEqual([
      "future_major_schema_read_only",
    ]);
    expect(readFileSync(path)).toEqual(content);
  });

  test("user-settings-migration-plan-reversal-is-pure-and-involutive", () => {
    const content = fixture("flat_classic_config.yaml");
    const root = makeRoot(content);
    const outcome = planUserSettingsMigration(root);
    expect(outcome.status).toBe("planned");
    expect(outcome.plan).toBeDefined();
    const plan = outcome.plan!;
    const expectedReverseRevision = `sha256:${createHash("sha256")
      .update(plan.proposedContent)
      .digest("hex")}`;

    rmSync(root, { recursive: true, force: true });
    const reversed = reverseUserSettingsMigrationPlan(plan);

    expect(reversed.required).toBe(plan.required);
    expect(reversed.baseRevision).toBe(expectedReverseRevision);
    expect(reversed.source).toEqual(plan.target);
    expect(reversed.target).toEqual(plan.source);
    expect(reversed.originalContent).toEqual(plan.proposedContent);
    expect(reversed.proposedContent).toEqual(plan.originalContent);
    expect(reversed.changes[0]).toEqual({
      kind: "fieldTransition",
      sourcePath: "/UI/preferences/auto_refresh_interval_ms",
      targetPath: "/auto_refresh_interval_ms",
      before: "---\n2500",
      after: "---\n2500",
    });
    expect(reverseUserSettingsMigrationPlan(reversed)).toEqual(plan);
  });

  test("user-settings-migration-plan-reversal-rejects-invalid-review-tokens", () => {
    const root = makeRoot(fixture("flat_classic_config.yaml"));
    const plan = planUserSettingsMigration(root).plan!;
    plan.source.location = "callerMutation";
    let caught: unknown;

    try {
      reverseUserSettingsMigrationPlan(plan);
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(Error);
    expect((caught as Error & { code?: string }).code).toBe(
      "migration_plan_review_invalid",
    );
  });
});

describe("User Settings migration persistence", () => {
  test("user-settings-migration-apply-and-explicit-restore", () => {
    const content = fixture("flat_classic_config.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const outcome = planUserSettingsMigration(root);
    expect(outcome.status).toBe("planned");
    const plan = outcome.plan!;

    const applied = applyUserSettingsMigration(
      root,
      plan.baseRevision,
      plan.proposedContent,
    );

    expect(applied.status).toBe("applied");
    expect(applied.expectedRevision).toBe(plan.baseRevision);
    expect(applied.actualRevision).toBeUndefined();
    expect(applied.receipt).toBeDefined();
    const receipt = applied.receipt!;
    expect(receipt.sourcePath).toBe(path);
    expect(receipt.destinationPath).toBe(path);
    expect(receipt.source).toEqual(plan.source);
    expect(receipt.target).toEqual(plan.target);
    expect(receipt.backupRevision).toBe(plan.baseRevision);
    expect(receipt.publishedRevision.startsWith("sha256:")).toBe(true);
    expect(readFileSync(receipt.backupPath)).toEqual(content);
    expect(readFileSync(path)).toEqual(plan.proposedContent);

    const restored = receipt.restore(root);

    expect(restored).toEqual({
      status: "restored",
      revision: plan.baseRevision,
      expectedRevision: receipt.publishedRevision,
    });
    expect(readFileSync(path)).toEqual(content);
  });

  test("user-settings-migration-apply-refuses-stale-and-mutated-approvals", () => {
    const content = fixture("flat_classic_config.yaml");
    const staleRoot = makeRoot(content);
    const stalePath = join(staleRoot, "CLASSIC Settings.yaml");
    const stalePlan = planUserSettingsMigration(staleRoot).plan!;
    const externallyEdited = Buffer.from(
      content.toString("utf8").replace("fcx_mode: true", "fcx_mode: false"),
    );
    writeFileSync(stalePath, externallyEdited);
    const actualRevision = openUserSettings(staleRoot).revision;

    expect(
      applyUserSettingsMigration(
        staleRoot,
        stalePlan.baseRevision,
        stalePlan.proposedContent,
      ),
    ).toEqual({
      status: "conflict",
      expectedRevision: stalePlan.baseRevision,
      actualRevision,
    });
    expect(readFileSync(stalePath)).toEqual(externallyEdited);

    const mutatedRoot = makeRoot(content);
    const mutatedPath = join(mutatedRoot, "CLASSIC Settings.yaml");
    const mutatedPlan = planUserSettingsMigration(mutatedRoot).plan!;
    const unapproved = Buffer.concat([
      mutatedPlan.proposedContent,
      Buffer.from("# caller mutation\n"),
    ]);
    let caught: unknown;

    try {
      applyUserSettingsMigration(
        mutatedRoot,
        mutatedPlan.baseRevision,
        unapproved,
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(Error);
    expect((caught as Error & { code?: string }).code).toBe(
      "migration_plan_approval_mismatch",
    );
    expect(readFileSync(mutatedPath)).toEqual(content);
  });

  test("user-settings-migration-restore-refuses-a-newer-document", () => {
    const content = fixture("flat_classic_config.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const plan = planUserSettingsMigration(root).plan!;
    const receipt = applyUserSettingsMigration(
      root,
      plan.baseRevision,
      plan.proposedContent,
    ).receipt!;
    const externallyEdited = Buffer.concat([
      readFileSync(path),
      Buffer.from("# external edit\n"),
    ]);
    writeFileSync(path, externallyEdited);
    const actualRevision = openUserSettings(root).revision;

    expect(receipt.restore(root)).toEqual({
      status: "conflict",
      expectedRevision: receipt.publishedRevision,
      actualRevision,
    });
    expect(readFileSync(path)).toEqual(externallyEdited);
  });
});

describe("Frontend State User Settings", () => {
  test("user-settings-frontend-state-snapshot", () => {
    const content = fixture("gui_geometry.yaml");
    const root = makeRoot(content);

    const snapshot = openUserSettings(root);

    expect(snapshot.frontendState).toEqual({
      preferences: {
        autoSwitchAfterScan: true,
        autoSwitchAfterScanOrigin: "document",
        autoRefreshIntervalMs: 5000,
        autoRefreshIntervalMsOrigin: "document",
      },
      windowGeometry: {
        mainTab: {
          maximized: false,
          maximizedOrigin: "document",
          width: 705,
          widthOrigin: "document",
          height: 641,
          heightOrigin: "document",
        },
        backupsTab: {
          maximized: false,
          maximizedOrigin: "document",
          width: 750,
          widthOrigin: "document",
          height: 580,
          heightOrigin: "document",
        },
        articlesTab: {
          maximized: false,
          maximizedOrigin: "document",
          width: 550,
          widthOrigin: "document",
          height: 350,
          heightOrigin: "document",
        },
        resultsTab: {
          maximized: true,
          maximizedOrigin: "document",
          width: 750,
          widthOrigin: "document",
          height: 450,
          heightOrigin: "document",
        },
      },
      tui: {
        activeTab: 0,
        activeTabOrigin: "default",
        resultsPanelWidth: 30,
        resultsPanelWidthOrigin: "default",
        sortAscending: false,
        sortAscendingOrigin: "default",
      },
    });
    expect(snapshot.diagnostics).toEqual([]);
    expect(snapshot.originalContent?.equals(content)).toBe(true);
    expect(readFileSync(join(root, "CLASSIC Settings.yaml"))).toEqual(content);
  });

  test("user-settings-frontend-state-invalid-fallbacks", () => {
    const content = fixture("invalid_known_values.yaml");
    const root = makeRoot(content);

    const snapshot = openUserSettings(root);
    const main = snapshot.frontendState.windowGeometry.mainTab;

    expect(main).toEqual({
      maximized: false,
      maximizedOrigin: "degradedFallback",
      width: 640,
      widthOrigin: "degradedFallback",
      height: 500,
      heightOrigin: "document",
    });
    expect(snapshot.frontendState.preferences).toEqual({
      autoSwitchAfterScan: true,
      autoSwitchAfterScanOrigin: "default",
      autoRefreshIntervalMs: 5000,
      autoRefreshIntervalMsOrigin: "default",
    });
    expect(snapshot.diagnostics.map((diagnostic) => diagnostic.code).slice(-2)).toEqual([
      "invalid_type_gui_geometry_width",
      "invalid_type_gui_geometry_maximized",
    ]);
    expect(snapshot.originalContent?.equals(content)).toBe(true);
    expect(readFileSync(join(root, "CLASSIC Settings.yaml"))).toEqual(content);
  });

  test("user-settings-frontend-state-tui-namespace", () => {
    const content = `schema_version: "1.0"
UI:
  tui:
    active_tab: 2
    results_panel_width: 42
    sort_ascending: true
`;

    const snapshot = openUserSettings(makeRoot(content));

    expect(snapshot.frontendState.tui).toEqual({
      activeTab: 2,
      activeTabOrigin: "document",
      resultsPanelWidth: 42,
      resultsPanelWidthOrigin: "document",
      sortAscending: true,
      sortAscendingOrigin: "document",
    });
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
      updateSource: "Both",
      autoSwitchAfterScan: true,
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
          fieldPath: "/CLASSIC_Settings/Update Source",
          value: "Both",
        },
        {
          fieldPath: "/UI/preferences/auto_switch_after_scan",
          value: true,
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
      updateSource: "Nexus",
      gameVersionSelection: "Future",
      maxConcurrentScans: -9,
    });

    expect(rejected.accepted).toBe(false);
    expect(rejected.baseRevision).toBeUndefined();
    expect(rejected.fields).toEqual([]);
    expect(rejected.diagnostics).toEqual([
      {
        fieldPath: "/CLASSIC_Settings/Update Source",
        code: "invalid_enum_update_source",
        message: "Update Source must be GitHub or Both",
      },
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

describe("User Settings Update commit", () => {
  test("user-settings-update-commit-publishes-accepted-fields", () => {
    const content = fixture("unknown_entries.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const update = {
      updateCheck: false,
      updateSource: "Both",
      autoSwitchAfterScan: true,
      unsolvedLogsDestination: "D:/CLASSIC/Unsolved",
    };
    const preview = previewUserSettingsUpdate(root, update);

    expect(preview.accepted).toBe(true);
    const result = commitUserSettingsUpdate(
      root,
      preview.baseRevision!,
      update,
    );

    expect(result.status).toBe("committed");
    expect(result.expectedRevision).toBe(preview.baseRevision);
    expect(result.revision?.startsWith("sha256:")).toBe(true);
    expect(result.actualRevision).toBeUndefined();
    expect(result.diagnostics).toEqual([]);

    const committed = openUserSettings(root);
    expect(committed.updatePreferences.updateCheck).toBe(false);
    expect(committed.updatePreferences.updateSource).toBe("Both");
    expect(committed.frontendState.preferences.autoSwitchAfterScan).toBe(true);
    expect(committed.crashLogScanSettings.unsolvedLogsDestination).toBe(
      "D:/CLASSIC/Unsolved",
    );
    expect(committed.revision).toBe(result.revision);

    // Unknown nodes are not projected by the DTO, so verify their semantic payload survived.
    const published = readFileSync(path, "utf8");
    expect(published).toContain("Future Scan Knob");
    expect(published).toContain("community_frontend");
    expect(published).toContain("ThirdPartyPlugin");
    expect(published).toContain("threshold: 1.25");
  });

  test("user-settings-update-commit-refuses-a-stale-preview", () => {
    const content = fixture("unknown_entries.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const update = { updateCheck: false };
    const preview = previewUserSettingsUpdate(root, update);
    expect(preview.accepted).toBe(true);

    const externallyEdited = content
      .toString("utf8")
      .replace("retry_count: 3", "retry_count: 4");
    writeFileSync(path, externallyEdited);
    const externalRevision = openUserSettings(root).revision;

    const result = commitUserSettingsUpdate(
      root,
      preview.baseRevision!,
      update,
    );

    expect(result).toEqual({
      status: "conflict",
      expectedRevision: preview.baseRevision,
      actualRevision: externalRevision,
      diagnostics: [],
    });
    expect(readFileSync(path, "utf8")).toBe(externallyEdited);
    expect(openUserSettings(root).updatePreferences.updateCheck).toBe(true);
  });

  test("user-settings-update-commit-returns-validation-rejection", () => {
    const content = fixture("unknown_entries.yaml");
    const root = makeRoot(content);
    const path = join(root, "CLASSIC Settings.yaml");
    const revision = openUserSettings(root).revision;

    const result = commitUserSettingsUpdate(root, revision, {
      maxConcurrentScans: -1,
    });

    expect(result.status).toBe("rejected");
    expect(result.revision).toBeUndefined();
    expect(result.expectedRevision).toBe(revision);
    expect(result.actualRevision).toBeUndefined();
    expect(result.diagnostics.map(({ code }) => code)).toEqual([
      "invalid_range_max_concurrent_scans",
    ]);
    expect(readFileSync(path)).toEqual(content);
  });

  test("user-settings-update-commit-throws-stable-operational-error", () => {
    const root = makeRoot();
    mkdirSync(join(root, "CLASSIC Settings.yaml"));
    let caught: unknown;

    try {
      commitUserSettingsUpdate(root, "missing", { updateCheck: false });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(Error);
    const commitError = caught as Error & { code?: string };
    expect(commitError.code).toBe("commit_source_unavailable");
    expect(commitError.message).toContain("could not be reopened");
  });
});

describe("User Settings bootstrap", () => {
  test("user-settings-bootstrap-requires-explicit-preview-and-commit", () => {
    const root = makeRoot();
    const path = join(root, "CLASSIC Settings.yaml");
    const update = {
      managedGame: "Fallout4",
      gameRoot: "C:/Games/Fallout 4",
    };

    const ordinaryPreview = previewUserSettingsUpdate(root, update);
    expect(ordinaryPreview.accepted).toBe(false);
    expect(ordinaryPreview.diagnostics.map(({ code }) => code)).toEqual([
      "update_base_requires_bootstrap",
    ]);
    expect(() => readFileSync(path)).toThrow();

    const ordinaryCommit = commitUserSettingsUpdate(root, "missing", update);
    expect(ordinaryCommit.status).toBe("rejected");
    expect(ordinaryCommit.diagnostics.map(({ code }) => code)).toEqual([
      "update_base_requires_bootstrap",
    ]);
    expect(() => readFileSync(path)).toThrow();

    const bootstrapPreview = previewUserSettingsBootstrap(root, update);
    expect(bootstrapPreview.accepted).toBe(true);
    expect(bootstrapPreview.baseRevision).toBe("missing");
    expect(() => readFileSync(path)).toThrow();

    const result = commitUserSettingsBootstrap(
      root,
      bootstrapPreview.baseRevision!,
      update,
    );
    expect(result.status).toBe("committed");
    expect(result.expectedRevision).toBe("missing");
    expect(result.revision?.startsWith("sha256:")).toBe(true);
    expect(result.diagnostics).toEqual([]);

    const published = readFileSync(path, "utf8");
    expect(published).toContain("CLASSIC_Settings:");
    expect(published).toContain("Update Check:");
    expect(published).toContain("Max Concurrent Scans:");
    expect(openUserSettings(root).gameSetupSettings.gameRoot).toBe(
      "C:/Games/Fallout 4",
    );
  });
});
