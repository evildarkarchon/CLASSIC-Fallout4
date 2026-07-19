import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import {
  existsSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createHash } from "node:crypto";
import {
  // YamlData class
  YamlData,
  // Free functions
  createYamlDataFromContent,
  clearYamlCache,
  registryClear,
  getApplicationDir,
  setApplicationDir,
  getYamlSourcePath,
  getYamlSourceDisplayName,
  getYamlSourceDisplayNameWithGame,
  persistGameLocalPaths,
  JsGameId,
  JsInstalledYamlDataDiagnosticKind,
  JsInstalledYamlDataLoadStatus,
  JsInstalledYamlDataProvenance,
  JsInstalledYamlDataRole,
  JsLocalIgnoreResetPublicationStage,
  JsLocalIgnoreResetStatus,
  JsLocalIgnoreYamlDataState,
  inspectInstalledYamlData,
  loadExplicitYamlData,
  loadInstalledYamlData,
} from "../index.js";
import { getRuntimeCoverageEntries } from "./fixtures/runtime_coverage_registry";

const THIS_SUITE =
  "node-bindings/classic-node/__test__/config.spec.ts";

// ============================================================================
// Test Fixtures
// ============================================================================

const MAIN_YAML = `
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
catch_log_records:
  - "LAND"
  - "REFR"
  - "CELL"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
  autoscan_text_Skyrim: "Autoscan Skyrim"
`;

const GAME_YAML = `
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "4.0.0"
  CRASHGEN_LogName: "crash-og"
Game_Hints:
  - "Hint 1"
  - "Hint 2"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found!"
  Warn_Outdated: "Your version is outdated."
Crashlog_Plugins_Exclude:
  - "Unofficial*.esp"
Crashlog_Records_Exclude:
  - "RecordType1"
Crashlog_Error_Check:
  - id: error_pattern_1
    name: Error Pattern 1
    severity: 4
    main_error_contains_any:
      - "Error description 1"
  - id: error_pattern_2
    name: Error Pattern 2
    severity: 2
    main_error_contains_any:
      - "Error description 2"
Crashlog_Stack_Check:
  - id: stack_pattern_1
    name: Stack Pattern 1
    severity: 3
    main_error_required_any:
      - "Main error required"
    main_error_optional_any:
      - "Main error optional"
    stack_contains_any:
      - "Stack pattern 1"
      - "Stack pattern 2"
    exclude_if_stack_contains_any:
      - "Excluded pattern"
    stack_contains_at_least:
      - substring: "Repeated pattern"
        count: 2
Mods_CONF:
  - mod_a: modA
    mod_b: modB
    name_a: Mod A
    name_b: Mod B
    description: "Config for ModA"
    fix: "Remove one."
Mods_CORE:
  - detect: ModB
    name: Core Mod B
    description: "Core mod B"
Mods_FREQ:
  - id: freq-mod
    criteria:
      any:
        - FreqMod
    name: Frequent Mod
    description: "Frequently used mod"
Mods_SOLU:
  - id: solu-mod
    criteria:
      any:
        - SoluMod
    name: Solution Mod
    description: "Solution mod"
`;

const IGNORE_YAML = `
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
  - "IgnoreItem2"
CLASSIC_Ignore_Skyrim:
  - "SkyrimIgnore1"
`;

const GAME_YAML_MAIN_ROOT_ONLY = `
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
`;

const EXPLICIT_MAIN_YAML = [
  'schema_version: "2.0"',
  "CLASSIC_Info:",
  '  version: "9.1.0"',
  "CLASSIC_Interface:",
  '  autoscan_text_Fallout4: "explicit node"',
  "",
].join("\r\n");

const GENERATED_IGNORE_YAML =
  "CLASSIC_Ignore_Fallout4:\n  - SelectedNodeDefault.dll\n";

const INSTALLED_MAIN_WITH_DEFAULT_YAML = `schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  default_ignorefile: |
    CLASSIC_Ignore_Fallout4:
      - SelectedNodeDefault.dll
CLASSIC_Interface:
  autoscan_text_Fallout4: "installed node"
`;

const EXPLICIT_GAME_YAML = `schema_version: "1.0"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_FREQ: []
Mods_SOLU: []
`;

const EXPLICIT_EMPTY_IGNORE_YAML = "CLASSIC_Ignore_Fallout4: []\n";

const YAML_CACHE_ENV_NAMES = [
  "LOCALAPPDATA",
  "APPDATA",
  "XDG_CACHE_HOME",
  "HOME",
] as const;

/** Run one assertion against an isolated cross-platform YAML cache root. */
async function withIsolatedYamlCache<T>(
  cacheRoot: string,
  operation: () => Promise<T>,
): Promise<T> {
  const previous = new Map(
    YAML_CACHE_ENV_NAMES.map((name) => [name, process.env[name]]),
  );
  for (const name of YAML_CACHE_ENV_NAMES) {
    process.env[name] = cacheRoot;
  }
  try {
    return await operation();
  } finally {
    for (const [name, value] of previous) {
      if (value === undefined) {
        delete process.env[name];
      } else {
        process.env[name] = value;
      }
    }
  }
}

// ============================================================================
// YamlData: Construction
// ============================================================================

describe("YamlData construction", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("fromYamlContent creates a valid instance", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data).toBeDefined();
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("createYamlDataFromContent free function works", () => {
    const data = createYamlDataFromContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data).toBeDefined();
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("fromYamlContent throws on invalid YAML", () => {
    expect(() =>
      YamlData.fromYamlContent(
        "{ invalid: yaml: content: }}}",
        GAME_YAML,
        IGNORE_YAML,
        "Fallout4",
        "auto",
      ),
    ).toThrow(/Failed to parse main YAML:/);
  });

  test("fromYamlContent classifies parse failures as InvalidArg", () => {
    try {
      YamlData.fromYamlContent(
        "{ invalid: yaml: content: }}}",
        GAME_YAML,
        IGNORE_YAML,
        "Fallout4",
        "auto",
      );
      throw new Error("expected parse failure");
    } catch (err) {
      const error = err as Error & { code?: string };
      expect(error.code).toBe("InvalidArg");
      expect(error.message).toContain("Failed to parse main YAML:");
    }
  });

  test("fromYamlContent throws on empty document", () => {
    expect(() =>
      YamlData.fromYamlContent("", GAME_YAML, IGNORE_YAML, "Fallout4", "auto"),
    ).toThrow();
  });

  test("fromYamlContent keeps metadata non-empty when Game_Info only has Main_Root_Name", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML_MAIN_ROOT_ONLY,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );

    expect(data.crashgenName.length).toBeGreaterThan(0);
    expect(data.xseAcronym.length).toBeGreaterThan(0);
    expect(data.gameVersion.length).toBeGreaterThan(0);
  });
});

describe("explicit YAML Data loading", () => {
  test("loads arbitrary paths with typed VR role and exact byte identities", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-explicit-yaml-"));
    try {
      const mainPath = join(root, "chosen-main.fixture");
      const gamePath = join(root, "chosen-game.fixture");
      const ignorePath = join(root, "chosen-ignore.fixture");
      writeFileSync(mainPath, EXPLICIT_MAIN_YAML);
      writeFileSync(gamePath, EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, EXPLICIT_EMPTY_IGNORE_YAML);

      const snapshot = await loadExplicitYamlData(
        { mainPath, gamePath, ignorePath },
        JsGameId.Fallout4Vr,
        "VR",
      );

      expect(snapshot.game).toBe(JsGameId.Fallout4Vr);
      expect(snapshot.gameDataRole).toBe("Fallout4");
      expect(snapshot.yamlData.classicVersion).toBe("9.1.0");
      expect(snapshot.yamlData.ignoreList).toEqual([]);
      expect(snapshot.mainIdentity.byteLen).toBe(
        Buffer.byteLength(EXPLICIT_MAIN_YAML),
      );
      expect(snapshot.mainIdentity.sha256).toBe(
        createHash("sha256").update(EXPLICIT_MAIN_YAML).digest("hex"),
      );

      writeFileSync(mainPath, "replacement bytes");
      expect(snapshot.yamlData.classicVersion).toBe("9.1.0");
      expect(snapshot.mainIdentity.sha256).toBe(
        createHash("sha256").update(EXPLICIT_MAIN_YAML).digest("hex"),
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("returns stable typed unsupported-game and Local Ignore errors", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-explicit-yaml-errors-"));
    try {
      await expect(
        loadExplicitYamlData(
          {
            mainPath: join(root, "missing-main"),
            gamePath: join(root, "missing-game"),
            ignorePath: join(root, "missing-ignore"),
          },
          JsGameId.Skyrim,
          "AnniversaryEdition",
        ),
      ).rejects.toMatchObject({ code: "unsupported_game" });

      const mainPath = join(root, "chosen-main.fixture");
      const gamePath = join(root, "chosen-game.fixture");
      const ignorePath = join(root, "chosen-ignore.fixture");
      writeFileSync(mainPath, EXPLICIT_MAIN_YAML);
      writeFileSync(gamePath, EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, "CLASSIC_Ignore_Fallout4: not-a-sequence\n");

      await expect(
        loadExplicitYamlData(
          { mainPath, gamePath, ignorePath },
          JsGameId.Fallout4,
          "Original",
        ),
      ).rejects.toMatchObject({
        code: "invalid_role_data",
        yamlRole: "local_ignore",
        path: ignorePath,
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

describe("Installed YAML Data inspection", () => {
  test("projects independent selection, exact identities, and diagnostics", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const cacheDir = join(cacheRoot, "CLASSIC", "yaml-cache");
    const rejectedMain = 'schema_version: "2.0"\nunrelated: true\n';
    try {
      mkdirSync(bundledDir, { recursive: true });
      mkdirSync(cacheDir, { recursive: true });
      writeFileSync(join(bundledDir, "CLASSIC Main.yaml"), EXPLICIT_MAIN_YAML);
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);
      writeFileSync(join(cacheDir, "CLASSIC Main.yaml"), rejectedMain);
      writeFileSync(join(cacheDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);

      const inspection = await withIsolatedYamlCache(cacheRoot, () =>
        inspectInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4Vr,
        }),
      );

      expect(inspection.game).toBe(JsGameId.Fallout4Vr);
      expect(inspection.gameDataRole).toBe("Fallout4");
      expect(inspection.main).toMatchObject({
        role: JsInstalledYamlDataRole.Main,
        provenance: JsInstalledYamlDataProvenance.Bundled,
        schemaMajor: 2,
        schemaMinor: 0,
        byteLength: Buffer.byteLength(EXPLICIT_MAIN_YAML),
        sha256: createHash("sha256").update(EXPLICIT_MAIN_YAML).digest("hex"),
      });
      expect(inspection.gameFile).toMatchObject({
        role: JsInstalledYamlDataRole.Game,
        provenance: JsInstalledYamlDataProvenance.Updated,
        schemaMajor: 1,
        schemaMinor: 0,
        byteLength: Buffer.byteLength(EXPLICIT_GAME_YAML),
        sha256: createHash("sha256").update(EXPLICIT_GAME_YAML).digest("hex"),
      });
      expect(inspection.diagnostics).toHaveLength(1);
      expect(inspection.diagnostics[0]).toMatchObject({
        role: JsInstalledYamlDataRole.Main,
        candidate: JsInstalledYamlDataProvenance.Updated,
        kind: JsInstalledYamlDataDiagnosticKind.InvalidRoleData,
        path: join(cacheDir, "CLASSIC Main.yaml"),
      });
      expect(existsSync(join(installationRoot, "CLASSIC Ignore.yaml"))).toBe(false);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("rejects with stable typed unsupported-game and no-source metadata", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-errors-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    try {
      await expect(
        inspectInstalledYamlData({
          installationRoot,
          game: JsGameId.Skyrim,
        }),
      ).rejects.toMatchObject({ code: "unsupported_game" });

      const failure = withIsolatedYamlCache(cacheRoot, () =>
        inspectInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
        }),
      );
      await expect(failure).rejects.toMatchObject({
        code: "no_usable_source",
        yamlRole: "main",
        diagnostics: [
          {
            role: JsInstalledYamlDataRole.Main,
            candidate: JsInstalledYamlDataProvenance.Bundled,
            kind: JsInstalledYamlDataDiagnosticKind.Missing,
            path: join(
              installationRoot,
              "CLASSIC Data",
              "databases",
              "CLASSIC Main.yaml",
            ),
          },
        ],
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

describe("Installed YAML Data loading", () => {
  test("returns a typed Ready snapshot with exact identities and stable parsed data", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-load-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(join(bundledDir, "CLASSIC Main.yaml"), EXPLICIT_MAIN_YAML);
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, IGNORE_YAML);

      const outcome = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4Vr,
          selectedGameVersion: "VR",
        }),
      );

      expect(outcome.status).toBe(JsInstalledYamlDataLoadStatus.Ready);
      expect(outcome.recoveryPlan).toBeUndefined();
      expect(outcome.snapshot.game).toBe(JsGameId.Fallout4Vr);
      expect(outcome.snapshot.gameDataRole).toBe("Fallout4");
      expect(outcome.snapshot.localIgnoreState).toBe(
        JsLocalIgnoreYamlDataState.Existing,
      );
      expect(outcome.snapshot.yamlData.classicVersion).toBe("9.1.0");
      expect(outcome.snapshot.yamlData.ignoreList).toEqual([
        "IgnoreItem1",
        "IgnoreItem2",
      ]);
      expect(outcome.snapshot.main).toMatchObject({
        role: JsInstalledYamlDataRole.Main,
        provenance: JsInstalledYamlDataProvenance.Bundled,
        schemaMajor: 2,
        schemaMinor: 0,
        sha256: createHash("sha256").update(EXPLICIT_MAIN_YAML).digest("hex"),
      });
      expect(outcome.snapshot.gameFile).toMatchObject({
        role: JsInstalledYamlDataRole.Game,
        provenance: JsInstalledYamlDataProvenance.Bundled,
        schemaMajor: 1,
        schemaMinor: 0,
        sha256: createHash("sha256").update(EXPLICIT_GAME_YAML).digest("hex"),
      });
      expect(outcome.snapshot.localIgnoreIdentity).toEqual({
        sha256: createHash("sha256").update(IGNORE_YAML).digest("hex"),
        byteLen: Buffer.byteLength(IGNORE_YAML),
      });
      expect(outcome.snapshot.diagnostics).toEqual([]);

      writeFileSync(join(bundledDir, "CLASSIC Main.yaml"), "replacement bytes");
      writeFileSync(ignorePath, "replacement bytes");
      expect(outcome.snapshot.yamlData.classicVersion).toBe("9.1.0");
      expect(outcome.snapshot.yamlData.ignoreList).toEqual([
        "IgnoreItem1",
        "IgnoreItem2",
      ]);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("generates missing Local Ignore from selected Main defaults with structured metadata", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-generated-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(
        join(bundledDir, "CLASSIC Main.yaml"),
        INSTALLED_MAIN_WITH_DEFAULT_YAML,
      );
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);

      const outcome = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );

      expect(outcome.status).toBe(JsInstalledYamlDataLoadStatus.Ready);
      expect(outcome.snapshot.localIgnoreState).toBe(
        JsLocalIgnoreYamlDataState.Generated,
      );
      expect(outcome.snapshot.yamlData.ignoreList).toEqual([
        "SelectedNodeDefault.dll",
      ]);
      expect(readFileSync(ignorePath, "utf8")).toBe(GENERATED_IGNORE_YAML);
      expect(outcome.snapshot.localIgnoreIdentity).toEqual({
        sha256: createHash("sha256").update(GENERATED_IGNORE_YAML).digest("hex"),
        byteLen: Buffer.byteLength(GENERATED_IGNORE_YAML),
      });
      expect(outcome.snapshot.diagnostics).toEqual([
        expect.objectContaining({
          path: ignorePath,
          kind: JsInstalledYamlDataDiagnosticKind.LocalIgnoreGenerated,
        }),
      ]);
      const [generationDiagnostic] = outcome.snapshot.diagnostics;
      expect(generationDiagnostic?.role).toBeUndefined();
      expect(generationDiagnostic?.candidate).toBeUndefined();
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("rejects fatal selection failures with stable metadata", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-load-errors-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    try {
      await expect(
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Skyrim,
          selectedGameVersion: "AnniversaryEdition",
        }),
      ).rejects.toMatchObject({ code: "unsupported_game" });

      const missingSource = withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );
      await expect(missingSource).rejects.toMatchObject({
        code: "no_usable_source",
        yamlRole: "main",
        diagnostics: [
          {
            role: JsInstalledYamlDataRole.Main,
            candidate: JsInstalledYamlDataProvenance.Bundled,
            kind: JsInstalledYamlDataDiagnosticKind.Missing,
          },
        ],
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("proceeds without malformed Local Ignore content for one operation without changing installed bytes", async () => {
    const root = mkdtempSync(
      join(tmpdir(), "classic-node-installed-yaml-ignore-recovery-"),
    );
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const mainPath = join(bundledDir, "CLASSIC Main.yaml");
    const gamePath = join(bundledDir, "CLASSIC Fallout4.yaml");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    const malformedIgnore = Buffer.from("CLASSIC_Ignore_Fallout4: [unterminated\n");
    const request = {
      installationRoot,
      game: JsGameId.Fallout4,
      selectedGameVersion: "Original",
    };
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(mainPath, INSTALLED_MAIN_WITH_DEFAULT_YAML);
      writeFileSync(gamePath, EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, malformedIgnore);
      const installedBytes = new Map([
        [mainPath, readFileSync(mainPath)],
        [gamePath, readFileSync(gamePath)],
        [ignorePath, readFileSync(ignorePath)],
      ]);

      const outcome = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData(request),
      );

      expect(outcome.status).toBe(
        JsInstalledYamlDataLoadStatus.LocalIgnoreRecoveryRequired,
      );
      expect(outcome.snapshot).toBeUndefined();
      expect(outcome.recoveryPlan).toBeDefined();
      const recoveryPlan = outcome.recoveryPlan!;
      expect(recoveryPlan.game).toBe(JsGameId.Fallout4);
      expect(recoveryPlan.gameDataRole).toBe("Fallout4");
      expect(recoveryPlan.localIgnorePath).toBe(ignorePath);
      expect(recoveryPlan.selectedGameVersion).toBe("Original");
      expect(recoveryPlan.malformedLocalIgnoreIdentity).toEqual({
        sha256: createHash("sha256").update(malformedIgnore).digest("hex"),
        byteLen: malformedIgnore.byteLength,
      });
      expect(recoveryPlan.defaultLocalIgnoreIdentity).toEqual({
        sha256: createHash("sha256").update(GENERATED_IGNORE_YAML).digest("hex"),
        byteLen: Buffer.byteLength(GENERATED_IGNORE_YAML),
      });
      expect(recoveryPlan.diagnostics).toEqual([
        expect.objectContaining({
          path: ignorePath,
          kind: JsInstalledYamlDataDiagnosticKind.Parse,
        }),
      ]);
      const retainedMain = recoveryPlan.main;
      const retainedGame = recoveryPlan.gameFile;
      const malformedIdentity = recoveryPlan.malformedLocalIgnoreIdentity;

      const snapshot = recoveryPlan.proceedWithoutIgnore();
      expect(snapshot.localIgnoreState).toBe(
        JsLocalIgnoreYamlDataState.ProceedWithoutIgnore,
      );
      expect(snapshot.yamlData.ignoreList).toEqual([]);
      expect(snapshot.main).toEqual(retainedMain);
      expect(snapshot.gameFile).toEqual(retainedGame);
      expect(snapshot.localIgnoreIdentity).toEqual(malformedIdentity);
      for (const [path, bytes] of installedBytes) {
        expect(readFileSync(path)).toEqual(bytes);
      }

      let replayError: unknown;
      try {
        recoveryPlan.proceedWithoutIgnore();
      } catch (error) {
        replayError = error;
      }
      expect(replayError).toMatchObject({
        code: "local_ignore_recovery_plan_consumed",
      });

      const repeatedOutcome = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData(request),
      );
      expect(repeatedOutcome.status).toBe(
        JsInstalledYamlDataLoadStatus.LocalIgnoreRecoveryRequired,
      );
      expect(repeatedOutcome.snapshot).toBeUndefined();
      expect(repeatedOutcome.recoveryPlan).toBeDefined();
      for (const [path, bytes] of installedBytes) {
        expect(readFileSync(path)).toEqual(bytes);
      }
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("resets malformed Local Ignore from retained defaults with a verified byte-exact backup", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-ignore-reset-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    const malformedIgnore = Buffer.from(
      "CLASSIC_Ignore_Fallout4: [reset-this-byte-exactly\r\n",
    );
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(
        join(bundledDir, "CLASSIC Main.yaml"),
        INSTALLED_MAIN_WITH_DEFAULT_YAML,
      );
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, malformedIgnore);

      const loaded = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );
      const recoveryPlan = loaded.recoveryPlan!;
      const expectedMalformedIdentity = {
        sha256: createHash("sha256").update(malformedIgnore).digest("hex"),
        byteLen: malformedIgnore.byteLength,
      };
      const expectedReplacementIdentity = {
        sha256: createHash("sha256")
          .update(GENERATED_IGNORE_YAML)
          .digest("hex"),
        byteLen: Buffer.byteLength(GENERATED_IGNORE_YAML),
      };

      const outcome = await recoveryPlan.resetToDefault();

      expect(outcome.status).toBe(JsLocalIgnoreResetStatus.Reset);
      expect(outcome.conflict).toBeUndefined();
      expect(outcome.reset).toBeDefined();
      const reset = outcome.reset!;
      expect(reset.localIgnorePath).toBe(ignorePath);
      expect(reset.malformedLocalIgnoreIdentity).toEqual(
        expectedMalformedIdentity,
      );
      expect(reset.backupIdentity).toEqual(expectedMalformedIdentity);
      expect(reset.replacementIdentity).toEqual(expectedReplacementIdentity);
      expect(readFileSync(reset.backupPath)).toEqual(malformedIgnore);
      expect(readFileSync(ignorePath, "utf8")).toBe(GENERATED_IGNORE_YAML);
      expect(reset.snapshot.localIgnoreState).toBe(
        JsLocalIgnoreYamlDataState.ResetToDefault,
      );
      expect(reset.snapshot.localIgnoreIdentity).toEqual(
        expectedReplacementIdentity,
      );
      expect(reset.snapshot.yamlData.ignoreList).toEqual([
        "SelectedNodeDefault.dll",
      ]);
      expect(reset.diagnostics).toEqual(reset.snapshot.diagnostics);
      expect(reset.diagnostics).toContainEqual(
        expect.objectContaining({
          path: ignorePath,
          kind: JsInstalledYamlDataDiagnosticKind.LocalIgnoreReset,
        }),
      );

      let replayError: unknown;
      try {
        recoveryPlan.resetToDefault();
      } catch (error) {
        replayError = error;
      }
      expect(replayError).toMatchObject({
        code: "local_ignore_recovery_plan_consumed",
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("returns a typed reset conflict without overwriting newer Local Ignore bytes", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-reset-conflict-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    const malformedIgnore = Buffer.from("CLASSIC_Ignore_Fallout4: invalid\n");
    const newerIgnore = Buffer.from(IGNORE_YAML);
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(
        join(bundledDir, "CLASSIC Main.yaml"),
        INSTALLED_MAIN_WITH_DEFAULT_YAML,
      );
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, malformedIgnore);

      const loaded = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );
      const recoveryPlan = loaded.recoveryPlan!;
      writeFileSync(ignorePath, newerIgnore);

      const outcome = await recoveryPlan.resetToDefault();

      expect(outcome.status).toBe(JsLocalIgnoreResetStatus.Conflict);
      expect(outcome.reset).toBeUndefined();
      expect(outcome.conflict).toEqual({
        expectedIdentity: {
          sha256: createHash("sha256").update(malformedIgnore).digest("hex"),
          byteLen: malformedIgnore.byteLength,
        },
        actualIdentity: {
          sha256: createHash("sha256").update(newerIgnore).digest("hex"),
          byteLen: newerIgnore.byteLength,
        },
        backupPath: undefined,
      });
      expect(readFileSync(ignorePath)).toEqual(newerIgnore);
      expect(
        existsSync(join(installationRoot, "CLASSIC Backup", "YAML Data")),
      ).toBe(false);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("rejects reset failures with stable operation metadata", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-reset-error-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    const malformedIgnore = Buffer.from(
      "CLASSIC_Ignore_Fallout4: not-a-sequence\n",
    );
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(join(bundledDir, "CLASSIC Main.yaml"), EXPLICIT_MAIN_YAML);
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);
      writeFileSync(ignorePath, malformedIgnore);

      const loaded = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );

      await expect(loaded.recoveryPlan!.resetToDefault()).rejects.toMatchObject({
        code: "defaults_unavailable",
        yamlRole: "local_ignore",
        path: ignorePath,
        reason: expect.any(String),
      });
      expect(readFileSync(ignorePath)).toEqual(malformedIgnore);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("exports stable publication stages", () => {
    expect(JsLocalIgnoreResetPublicationStage.Create).toBe("Create");
    expect(JsLocalIgnoreResetPublicationStage.Write).toBe("Write");
    expect(JsLocalIgnoreResetPublicationStage.Flush).toBe("Flush");
    expect(JsLocalIgnoreResetPublicationStage.Sync).toBe("Sync");
    expect(JsLocalIgnoreResetPublicationStage.Publish).toBe("Publish");
  });

  test("keeps invalid selected Main defaults fatal only while Local Ignore is missing", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-installed-yaml-default-error-"));
    const cacheRoot = join(root, "platform-cache");
    const installationRoot = join(root, "installation");
    const bundledDir = join(installationRoot, "CLASSIC Data", "databases");
    const ignorePath = join(
      installationRoot,
      "CLASSIC Data",
      "CLASSIC Ignore.yaml",
    );
    try {
      mkdirSync(bundledDir, { recursive: true });
      writeFileSync(join(bundledDir, "CLASSIC Main.yaml"), EXPLICIT_MAIN_YAML);
      writeFileSync(join(bundledDir, "CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML);

      await expect(
        withIsolatedYamlCache(cacheRoot, () =>
          loadInstalledYamlData({
            installationRoot,
            game: JsGameId.Fallout4,
            selectedGameVersion: "Original",
          }),
        ),
      ).rejects.toMatchObject({
        code: "local_ignore_default_invalid",
        yamlRole: "local_ignore",
        path: ignorePath,
      });
      expect(existsSync(ignorePath)).toBe(false);

      const malformedIgnore = Buffer.from(
        "CLASSIC_Ignore_Fallout4: not-a-sequence\n",
      );
      writeFileSync(ignorePath, malformedIgnore);
      const mainPath = join(bundledDir, "CLASSIC Main.yaml");
      const gamePath = join(bundledDir, "CLASSIC Fallout4.yaml");
      const installedBytes = new Map([
        [mainPath, readFileSync(mainPath)],
        [gamePath, readFileSync(gamePath)],
        [ignorePath, readFileSync(ignorePath)],
      ]);

      const outcome = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );
      expect(outcome.status).toBe(
        JsInstalledYamlDataLoadStatus.LocalIgnoreRecoveryRequired,
      );
      expect(outcome.snapshot).toBeUndefined();
      expect(outcome.recoveryPlan).toBeDefined();
      const recoveryPlan = outcome.recoveryPlan!;
      expect(recoveryPlan.defaultLocalIgnoreIdentity).toBeNull();

      const snapshot = recoveryPlan.proceedWithoutIgnore();
      expect(snapshot.localIgnoreState).toBe(
        JsLocalIgnoreYamlDataState.ProceedWithoutIgnore,
      );
      expect(snapshot.yamlData.ignoreList).toEqual([]);
      for (const [path, bytes] of installedBytes) {
        expect(readFileSync(path)).toEqual(bytes);
      }

      const repeatedOutcome = await withIsolatedYamlCache(cacheRoot, () =>
        loadInstalledYamlData({
          installationRoot,
          game: JsGameId.Fallout4,
          selectedGameVersion: "Original",
        }),
      );
      expect(repeatedOutcome.status).toBe(
        JsInstalledYamlDataLoadStatus.LocalIgnoreRecoveryRequired,
      );
      expect(repeatedOutcome.recoveryPlan?.defaultLocalIgnoreIdentity).toBeNull();
      for (const [path, bytes] of installedBytes) {
        expect(readFileSync(path)).toEqual(bytes);
      }
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

describe("runtime coverage metadata", () => {
  test("tracks Installed YAML Data, application directory, and Game Local adapters", () => {
    const bindingIdentifiers = new Set(
      getRuntimeCoverageEntries(THIS_SUITE).flatMap(
        (entry) => entry.bindingIdentifiers ?? [],
      ),
    );

    expect(bindingIdentifiers.has("getApplicationDir")).toBe(true);
    expect(bindingIdentifiers.has("setApplicationDir")).toBe(true);
    expect(bindingIdentifiers.has("persistGameLocalPaths")).toBe(true);
    expect(bindingIdentifiers.has("LocalIgnoreRecoveryPlan")).toBe(true);
    expect(bindingIdentifiers.has("JsLocalIgnoreResetOutcome")).toBe(true);
    expect(
      bindingIdentifiers.has("JsLocalIgnoreResetPublicationStage"),
    ).toBe(true);
    expect(bindingIdentifiers.has("JsLocalIgnoreResetStatus")).toBe(true);
    expect(bindingIdentifiers.has("loadInstalledYamlData")).toBe(true);
  });
});

describe("application directory overrides", () => {
  beforeEach(() => {
    registryClear();
  });

  afterEach(() => {
    registryClear();
  });

  test("setApplicationDir and getApplicationDir round-trip", () => {
    expect(getApplicationDir()).toBeNull();

    const appDir = mkdtempSync(join(tmpdir(), "classic-node-appdir-"));
    setApplicationDir(appDir);

    expect(getApplicationDir()).toBe(appDir);
  });
});

// ============================================================================
// YamlData: Main YAML Properties
// ============================================================================

describe("YamlData main YAML properties", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("classicVersion returns correct version", () => {
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("classicVersionDate returns correct date", () => {
    expect(data.classicVersionDate).toBe("2024-01-15");
  });

  test("classicRecordsList returns correct records", () => {
    expect(data.classicRecordsList).toEqual(["LAND", "REFR", "CELL"]);
  });

  test("autoscanText returns game-specific text", () => {
    expect(data.autoscanText).toBe("Autoscan Fallout 4");
  });

  test("classicGameHints returns correct hints", () => {
    expect(data.classicGameHints).toEqual(["Hint 1", "Hint 2"]);
  });
});

// ============================================================================
// YamlData: Game YAML Properties
// ============================================================================

describe("YamlData game properties", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("xseAcronym returns correct value", () => {
    expect(data.xseAcronym).toBe("F4SE");
  });

  test("gameVersion returns correct version", () => {
    expect(data.gameVersion).toBe("1.10.163");
  });

  test("crashgenLatestOg returns correct version", () => {
    expect(data.crashgenLatestOg).toBe("4.0.0");
  });

  test("does not expose deprecated VR and split-version YAML fields", () => {
    expect((data as unknown as Record<string, unknown>).gameVersionNew).toBeUndefined();
    expect((data as unknown as Record<string, unknown>).gameVersionVr).toBeUndefined();
    expect((data as unknown as Record<string, unknown>).crashgenLatestVr).toBeUndefined();
  });

  test("warnNoplugins returns correct warning", () => {
    expect(data.warnNoplugins).toBe("No plugins found!");
  });

  test("warnOutdated returns correct warning", () => {
    expect(data.warnOutdated).toBe("Your version is outdated.");
  });
});

// ============================================================================
// YamlData: Ignore Lists
// ============================================================================

describe("YamlData ignore lists", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("ignoreList returns Fallout4-specific entries", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.ignoreList).toEqual(["IgnoreItem1", "IgnoreItem2"]);
  });

  test("ignoreList returns Skyrim-specific entries", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Skyrim",
      "auto",
    );
    expect(data.ignoreList).toEqual(["SkyrimIgnore1"]);
  });

  test("gameIgnorePlugins returns correct list", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.gameIgnorePlugins).toEqual(["Unofficial*.esp"]);
  });

  test("gameIgnoreRecords returns correct list", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.gameIgnoreRecords).toEqual(["RecordType1"]);
  });
});

// ============================================================================
// YamlData: Suspect Patterns
// ============================================================================

describe("YamlData suspect patterns", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("suspectErrorRules returns structured rules", () => {
    const rules = data.suspectErrorRules;
    expect(rules).toHaveLength(2);
    expect(rules[0]).toMatchObject({
      id: "error_pattern_1",
      name: "Error Pattern 1",
      severity: 4,
      mainErrorContainsAny: ["Error description 1"],
    });
  });

  test("suspectStackRules returns structured rules", () => {
    const rules = data.suspectStackRules;
    expect(rules).toHaveLength(1);
    expect(rules[0]).toMatchObject({
      id: "stack_pattern_1",
      name: "Stack Pattern 1",
      severity: 3,
      mainErrorRequiredAny: ["Main error required"],
      mainErrorOptionalAny: ["Main error optional"],
      stackContainsAny: ["Stack pattern 1", "Stack pattern 2"],
      excludeIfStackContainsAny: ["Excluded pattern"],
    });
    expect(rules[0].stackContainsAtLeast).toEqual([
      { substring: "Repeated pattern", count: 2 },
    ]);
  });
});

// ============================================================================
// YamlData: Mod Databases
// ============================================================================

describe("YamlData mod databases", () => {
  let data: InstanceType<typeof YamlData>;

  beforeEach(() => {
    clearYamlCache();
    data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
  });

  test("gameModsConf returns structured entries", () => {
    expect(data.gameModsConf).toHaveLength(1);
    expect(data.gameModsConf[0].modA).toBe("modA");
    expect(data.gameModsConf[0].description).toBe("Config for ModA");
  });

  test("gameModsCoreCount returns correct count", () => {
    expect(data.gameModsCoreCount).toBe(1);
  });

  test("gameModsCoreDetects returns detect ids", () => {
    expect(data.gameModsCoreDetects).toEqual(["ModB"]);
  });

  test("gameModsCoreNames returns display names", () => {
    expect(data.gameModsCoreNames).toEqual(["Core Mod B"]);
  });

  test("gameModsCoreDescriptions returns descriptions", () => {
    expect(data.gameModsCoreDescriptions).toEqual(["Core mod B"]);
  });

  test("gameModsFreq returns structured entries", () => {
    expect(data.gameModsFreq).toHaveLength(1);
    expect(data.gameModsFreq[0].id).toBe("freq-mod");
    expect(data.gameModsFreq[0].criteria.any).toEqual(["FreqMod"]);
    expect(data.gameModsFreq[0].name).toBe("Frequent Mod");
    expect(data.gameModsFreq[0].description).toBe("Frequently used mod");
  });

  test("legacy OPC2 YAML is not exposed through YamlData", () => {
    expect("gameModsOpc2" in data).toBe(false);
  });

  test("gameModsSolu returns structured entries", () => {
    expect(data.gameModsSolu).toHaveLength(1);
    expect(data.gameModsSolu[0].id).toBe("solu-mod");
    expect(data.gameModsSolu[0].criteria.any).toEqual(["SoluMod"]);
    expect(data.gameModsSolu[0].criteria.all).toBeUndefined();
    expect(data.gameModsSolu[0].exceptions).toEqual([]);
    expect(data.gameModsSolu[0].name).toBe("Solution Mod");
    expect(data.gameModsSolu[0].description).toBe("Solution mod");
  });
});

// ============================================================================
// YamlData: VR Mode
// ============================================================================

describe("YamlData VR mode", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("VR mode keeps shared YAML metadata and defers VR version metadata", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "VR",
    );
    // VR-specific static metadata is no longer sourced from YAML.
    // YamlData exposes shared config, while version-specific metadata now
    // comes from the version-registry APIs.
    expect(data.getCrashgenName()).toBe("crash-og");
    expect(data.getCrashgenIgnore()).toEqual([]);
    expect(data.crashgenName).toBe("crash-og");
  });

  test("non-VR mode reads from Game_Info section via accessor", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    expect(data.getCrashgenName()).toBe("crash-og");
    expect(data.crashgenName).toBe("crash-og");
  });
});

// ============================================================================
// YamlData: toString
// ============================================================================

describe("YamlData toString", () => {
  test("toString returns a human-readable string", () => {
    const data = YamlData.fromYamlContent(
      MAIN_YAML,
      GAME_YAML,
      IGNORE_YAML,
      "Fallout4",
      "auto",
    );
    const str = data.toString();
    expect(typeof str).toBe("string");
    expect(str).toContain("YamlData(");
    expect(str).toContain("7.31.0");
  });
});

// ============================================================================
// YamlData: Missing Keys Default Gracefully
// ============================================================================

describe("YamlData missing keys", () => {
  test("missing YAML keys return empty defaults", () => {
    const sparseMain = "other_key: value\n";
    const sparseGame = "unrelated: data\n";
    const sparseIgnore = "different_game: []\n";

    const data = YamlData.fromYamlContent(
      sparseMain,
      sparseGame,
      sparseIgnore,
      "Fallout4",
      "auto",
    );

    expect(data.classicVersion).toBe("");
    expect(data.classicRecordsList).toEqual([]);
    expect(data.ignoreList).toEqual([]);
    expect(data.xseAcronym).toBe("");
    expect(data.suspectErrorRules).toEqual([]);
    expect(data.gameModsCoreCount).toBe(0);
  });
});

// ============================================================================
// Game Local Path Persistence
// ============================================================================

describe("Game Local path persistence", () => {
  test("updates supplied paths without touching User Settings", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-game-local-"));

    try {
      const localYamlPath = join(
        root,
        "CLASSIC Data",
        "CLASSIC Fallout4 Local.yaml",
      );
      const userSettingsPath = join(root, "CLASSIC Settings.yaml");
      const userSettingsSentinel =
        "{ malformed user settings that must stay untouched";

      mkdirSync(dirname(localYamlPath), { recursive: true });
      writeFileSync(
        localYamlPath,
        [
          "Game_Info:",
          "  Root_Folder_Game: C:/Games/Old",
          "  Root_Folder_Docs: C:/Users/Test/Documents/Existing",
          "  Docs_Folder_XSE: C:/Users/Test/Documents/Existing/F4SE",
          "",
        ].join("\n"),
        "utf8",
      );
      writeFileSync(userSettingsPath, userSettingsSentinel, "utf8");

      await persistGameLocalPaths(
        localYamlPath,
        "D:/Games/Fallout4",
        undefined,
      );

      const localYaml = readFileSync(localYamlPath, "utf8");
      expect(localYaml).toContain('Root_Folder_Game: "D:/Games/Fallout4"');
      expect(localYaml).toContain(
        'Root_Folder_Docs: "C:/Users/Test/Documents/Existing"',
      );
      expect(localYaml).toContain(
        'Docs_Folder_XSE: "C:/Users/Test/Documents/Existing/F4SE"',
      );
      expect(readFileSync(userSettingsPath, "utf8")).toBe(
        userSettingsSentinel,
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});

// ============================================================================
// YamlSource Free Functions
// ============================================================================

describe("YamlSource free functions", () => {
  test("getYamlSourcePath returns correct path for Main", () => {
    const path = getYamlSourcePath("Main", "");
    expect(path).toContain("CLASSIC Main.yaml");
  });

  test("getYamlSourcePath returns correct path for Game with game name", () => {
    const path = getYamlSourcePath("Game", "Fallout4");
    expect(path).toContain("CLASSIC Fallout4.yaml");
  });

  test("getYamlSourcePath shares the Fallout4 database with Fallout4VR", () => {
    const path = getYamlSourcePath("Game", "Fallout4VR");
    expect(path).toContain("CLASSIC Fallout4.yaml");
    expect(path).not.toContain("CLASSIC Fallout4VR.yaml");
  });


  test("getYamlSourcePath returns correct path for Ignore", () => {
    const path = getYamlSourcePath("Ignore", "");
    expect(path).toContain("CLASSIC Ignore.yaml");
  });

  test("getYamlSourcePath returns correct path for GameLocal", () => {
    const path = getYamlSourcePath("GameLocal", "Skyrim");
    expect(path).toContain("CLASSIC Skyrim Local.yaml");
  });

  test("getYamlSourcePath returns CLASSIC cache path", () => {
    const path = getYamlSourcePath("Cache", "");
    expect(path).toContain("CLASSIC");
    expect(path).toContain("cache.yaml");
    expect(path).not.toContain("CLASSIC-Fallout4");
  });

  test("getYamlSourceDisplayName returns correct name for Main", () => {
    const name = getYamlSourceDisplayName("Main");
    expect(name).toBe("Main Database");
  });


  test("getYamlSourceDisplayNameWithGame returns game-specific name", () => {
    const name = getYamlSourceDisplayNameWithGame("Game", "Fallout4");
    expect(name).toBe("Fallout4 Database");
  });

  test("getYamlSourceDisplayNameWithGame for GameLocal", () => {
    const name = getYamlSourceDisplayNameWithGame("GameLocal", "Skyrim");
    expect(name).toBe("Skyrim Local Config");
  });
});

// ============================================================================
// clearYamlCache
// ============================================================================

describe("clearYamlCache", () => {
  test("clearYamlCache does not throw", () => {
    expect(() => clearYamlCache()).not.toThrow();
  });

  test("clearYamlCache can be called multiple times", () => {
    clearYamlCache();
    clearYamlCache();
    clearYamlCache();
    // No error means success
  });
});

// ============================================================================
// Phase 4 Plan 3: Promoted config cache constants (real-shape assertions)
// ============================================================================

import {
  DEFAULT_CACHE_CLEANUP_INTERVAL,
  DEFAULT_CACHE_CLEANUP_THRESHOLD,
  DEFAULT_QUERY_CACHE_CAPACITY,
  getDefaultCacheCleanupInterval,
  getDefaultCacheCleanupThreshold,
  getDefaultQueryCacheCapacity,
  getHashCacheStats,
  resetHashCacheStats,
  clearHashCache,
  detectConfigDuplicates,
  gameSetupNeedsPathDetection,
  JsConfigDuplicateDetector,
} from "../index.js";

describe("config: cache constants (Plan 3 promotion)", () => {
  test("DEFAULT_CACHE_CLEANUP_INTERVAL is a positive number", () => {
    expect(typeof DEFAULT_CACHE_CLEANUP_INTERVAL).toBe("number");
    expect(DEFAULT_CACHE_CLEANUP_INTERVAL).toBeGreaterThan(0);
  });

  test("getDefaultCacheCleanupInterval returns the const value", () => {
    expect(getDefaultCacheCleanupInterval()).toBe(
      DEFAULT_CACHE_CLEANUP_INTERVAL,
    );
  });

  test("DEFAULT_CACHE_CLEANUP_THRESHOLD is a positive number", () => {
    expect(typeof DEFAULT_CACHE_CLEANUP_THRESHOLD).toBe("number");
    expect(DEFAULT_CACHE_CLEANUP_THRESHOLD).toBeGreaterThan(0);
  });

  test("getDefaultCacheCleanupThreshold returns the const value", () => {
    expect(getDefaultCacheCleanupThreshold()).toBe(
      DEFAULT_CACHE_CLEANUP_THRESHOLD,
    );
  });

  test("DEFAULT_QUERY_CACHE_CAPACITY is a positive integer", () => {
    expect(typeof DEFAULT_QUERY_CACHE_CAPACITY).toBe("number");
    expect(Number.isInteger(DEFAULT_QUERY_CACHE_CAPACITY)).toBe(true);
    expect(DEFAULT_QUERY_CACHE_CAPACITY).toBeGreaterThan(0);
  });

  test("getDefaultQueryCacheCapacity returns the const value", () => {
    expect(getDefaultQueryCacheCapacity()).toBe(DEFAULT_QUERY_CACHE_CAPACITY);
  });
});

describe("config: hash cache stats (Plan 3 promotion)", () => {
  test("getHashCacheStats returns a stats shape with numeric fields", () => {
    const stats = getHashCacheStats();
    expect(stats).toBeDefined();
    expect(typeof stats.hits).toBe("number");
    expect(typeof stats.misses).toBe("number");
    expect(typeof stats.hit_rate).toBe("number");
    expect(typeof stats.size).toBe("number");
    expect(typeof stats.capacity).toBe("number");
  });

  test("resetHashCacheStats clears counters", () => {
    resetHashCacheStats();
    const stats = getHashCacheStats();
    expect(stats.hits).toBe(0);
    expect(stats.misses).toBe(0);
  });

  test("clearHashCache is callable without throwing", () => {
    expect(() => clearHashCache()).not.toThrow();
  });
});

describe("config: duplicate detector class (Plan 3 promotion)", () => {
  test("JsConfigDuplicateDetector can be constructed", () => {
    const det = new JsConfigDuplicateDetector();
    expect(det).toBeDefined();
    expect(typeof det).toBe("object");
  });

  test("JsConfigDuplicateDetector.withWhitelist creates instance", () => {
    const det = JsConfigDuplicateDetector.withWhitelist(["test.dll"]);
    expect(det).toBeDefined();
    expect(typeof det).toBe("object");
  });

  test("detectConfigDuplicates returns an array for a temp dir", () => {
    const dir = mkdtempSync(join(tmpdir(), "classic-node-dup-"));
    try {
      const result = detectConfigDuplicates(dir);
      expect(Array.isArray(result)).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("config: game setup path detection helpers (Plan 3 promotion)", () => {
  test("gameSetupNeedsPathDetection returns object with boolean fields", () => {
    const result = gameSetupNeedsPathDetection();
    expect(typeof result.needsGamePath).toBe("boolean");
    expect(typeof result.needsDocsPath).toBe("boolean");
  });
});
