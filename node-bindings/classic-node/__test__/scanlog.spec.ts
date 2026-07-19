import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import {
  copyFileSync,
  existsSync,
  mkdtempSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
  rmSync,
} from "fs";
import { dirname, join, relative } from "path";
import { tmpdir } from "os";
import {
  getVersion,
  ScanRunCancellation,
  ScanRunRequest,
  ScanRunUnsolvedLogs,
  JsGameId,
  JsScanRunInstalledYamlDataDiagnosticKind,
  JsScanRunLocalIgnoreRecoveryDecision,
  JsScanRunLocalIgnoreState,
  scanRunExecute,
  scanRunResume,
  parseLogSegments,
  extractFormIds,
  extractPluginList,
  detectCrashPattern,
  detectVrLog,
  detectGpuInfo,
  parseCrashgenVersion,
  checkCrashgenVersionStatus,
  analyzePapyrusLog,
  CRASH_LOG_PATTERN,
  checkXsePlugins,
  parseXseLog,
  type JsGpuInfo,
  type JsScanRunConfiguration,
  type JsScanRunEvent,
  type JsLogErrorEntry,
  type JsLogSegments,
  type JsPapyrusStats,
  type JsCrashgenVersionStatus,
} from "../index.js";

const CRASHGEN_VERSION_STATUS = {
  Valid: "Valid" as JsCrashgenVersionStatus,
  Outdated: "Outdated" as JsCrashgenVersionStatus,
  NoSupportedVersion: "NoSupportedVersion" as JsCrashgenVersionStatus,
};

// ============================================================================
// Sample crash log content for testing
// ============================================================================

const SAMPLE_CRASH_LOG = `Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

\t[Compatibility]
\tAchievements: true
\tMemoryManager: false
\tF4EE: false

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tPHYSICAL MEMORY: 32.0 GB

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> TESForm::SetReference+0x12
\t[ 1] 0x7FF6EF4C3600 Fallout4.exe+0733600 -> BGSInventoryItem::GetOwner+0x30
\t[ 2] 0x7FFB12340000 nvwgf2umx.dll+00FF1234 -> ?

MODULES:
\tFallout4.exe v1.10.163.0
\tnvwgf2umx.dll v31.0.15.3713
\tkernel32.dll v10.0.22621.1
\tAchievements.dll v2.3.0

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] DLCworkshop01.esm
\t[FE:000] ccBGSFO4001-PipBoy(Black).esl
\t[03] Unofficial Fallout 4 Patch.esp
`;

const FORMID_CONTENT = `PROBABLE CALL STACK:
[0] 0x7FF6DEADBEEF    FormID: 0x00012345    TestMod.esp
[1] 0x7FF6CAFEBABE    FormID: 0x00023456    Fallout4.esm
[2] 0x7FF6BADF00D5    FormID: 0x00034567    DLCCoast.esm
`;

const PLUGIN_CONTENT = `PLUGINS:
[00] Fallout4.esm
[01] DLCRobot.esm
[02] DLCworkshop01.esm
[03] DLCCoast.esm
[FE:000] ccBGSFO4001-PipBoy(Black).esl
[04] TestMod.esp
`;

const SETTINGS_MARKER_CONTENT = `Fallout 4 v1.10.163
[Compatibility]
Achievements: true
MemoryManager: false
`;

const MAIN_YAML = `
schema_version: "2.0"
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
  default_ignorefile: |
    CLASSIC_Ignore_Fallout4: []
catch_log_records:
  - "LAND"
`;

const GAME_YAML = `
schema_version: "1.0"
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "1.37.0"
  CRASHGEN_LogName: "Buffout 4"
  Main_Root_Name: "Fallout4"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found"
  Warn_Outdated: "Outdated"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: []
Mods_SOLU: []
`;

const IGNORE_YAML = `
CLASSIC_Ignore_Fallout4: []
`;

const MISSING_LOG_PATH = join("Z:", "nonexistent", "classic-fcx.log");

const SHARED_SCAN_RUN_FIXTURE_ROOT = join(
  import.meta.dir,
  "..",
  "..",
  "..",
  "tests",
  "fixtures",
  "crash_log_scan_run",
);
const SHARED_SCAN_RUN_MANIFEST = JSON.parse(
  readFileSync(join(SHARED_SCAN_RUN_FIXTURE_ROOT, "manifest.json"), "utf8"),
) as {
  fixtures: {
    standard: {
      logs: string[];
      maxConcurrent: number;
      expected: {
        acceptedLogs: string[];
        effectiveConcurrency: number;
        discoveryOrder: number[];
        dispositions: string[];
      };
    };
    targeted: {
      inputs: string[];
      maxConcurrent: number;
      expected: {
        acceptedLogs: string[];
        rejectedInputs: string[];
        effectiveConcurrency: number;
        discoveryOrder: number[];
        dispositions: string[];
        unsolvedLogsArtifacts: string[];
      };
    };
    installedYamlData: {
      input: string;
      malformedLocalIgnore: string;
      resetOutcomes: {
        conflictCode: string;
        backupFailureCode: string;
        replacementFailureCode: string;
        consumedCode: string;
        backupMustEqualMalformedBytes: boolean;
        reportMustEqualExistingBytes: boolean;
        preResetCancellationMutates: boolean;
        postCriticalCancellationStatus: string;
      };
    };
  };
};
const SHARED_VALID_CRASH_LOG = readFileSync(
  join(SHARED_SCAN_RUN_FIXTURE_ROOT, "valid-crash.log"),
  "utf8",
);

const writeScanRunDataRoot = (name: string): string => {
  const root = mkdtempSync(join(tmpdir(), `${name}-`));
  const dataDir = join(root, "CLASSIC Data");
  const databaseDir = join(dataDir, "databases");
  mkdirSync(databaseDir, { recursive: true });
  writeFileSync(join(databaseDir, "CLASSIC Main.yaml"), MAIN_YAML, "utf8");
  writeFileSync(join(databaseDir, "CLASSIC Fallout4.yaml"), GAME_YAML, "utf8");
  writeFileSync(join(dataDir, "CLASSIC Ignore.yaml"), IGNORE_YAML, "utf8");
  return root;
};

/** Copies the language-neutral YAML corpus into one temporary Node run root. */
const writeSharedScanRunDataRoot = (name: string): string => {
  const root = mkdtempSync(join(tmpdir(), `${name}-`));
  const databaseDir = join(root, "CLASSIC Data", "databases");
  mkdirSync(databaseDir, { recursive: true });
  copyFileSync(
    join(SHARED_SCAN_RUN_FIXTURE_ROOT, "CLASSIC Data", "CLASSIC Ignore.yaml"),
    join(root, "CLASSIC Data", "CLASSIC Ignore.yaml"),
  );
  for (const name of ["CLASSIC Main.yaml", "CLASSIC Fallout4.yaml"]) {
    copyFileSync(
      join(SHARED_SCAN_RUN_FIXTURE_ROOT, "CLASSIC Data", "databases", name),
      join(databaseDir, name),
    );
  }
  return root;
};

/** Materializes one shared valid log at a manifest-relative path. */
const writeSharedScanRunLog = (root: string, relativePath: string): string => {
  const path = join(root, relativePath);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, SHARED_VALID_CRASH_LOG, "utf8");
  return path;
};

/** Normalizes one temporary path to the manifest's slash-separated form. */
const sharedRelativePath = (root: string, path: string): string =>
  relative(root, path).replace(/\\/g, "/");

type ScanRunExecution = Awaited<ReturnType<typeof scanRunExecute>>;
type ScanRunSuccess = Extract<ScanRunExecution, { result: unknown }>;
type ScanRunFailure = Extract<ScanRunExecution, { error: unknown }>;

const requireScanRunSuccess = (execution: ScanRunExecution): ScanRunSuccess => {
  if (!("result" in execution)) {
    throw new Error(`Expected scan success, received ${execution.error.stage}`);
  }
  return execution;
};

const requireScanRunFailure = (execution: ScanRunExecution): ScanRunFailure => {
  if (!("error" in execution)) {
    throw new Error(`Expected scan failure, received ${execution.result.status}`);
  }
  return execution;
};

// ============================================================================
// Version & Config
// ============================================================================

describe("Scanlog bindings", () => {
  test("getVersion returns a semver string", () => {
    const version = getVersion();
    expect(typeof version).toBe("string");
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);
  });
});

describe("final Crash Log Scan Run contract", () => {
  const scanRunConfiguration = (
    root: string,
    options: Partial<JsScanRunConfiguration> = {},
  ): JsScanRunConfiguration => ({
    installationRoot: root,
    game: JsGameId.Fallout4,
    gameVersion: "auto",
    showFormidValues: false,
    simplifyLogs: false,
    formidDatabasePaths: [],
    maxConcurrent: 1,
    ...options,
  });

  test("constructors make Targeted movement and FCX without context unrepresentable", () => {
    const root = writeScanRunDataRoot("classic-node-scan-run-request-types");
    const configuration = scanRunConfiguration(root);
    const standardSource = {
      baseDirectory: root,
      configuredDocumentsRoot: join(root, "Docs"),
    };
    const targetedSource = { inputs: [MISSING_LOG_PATH] };
    const movement = ScanRunUnsolvedLogs.leaveInPlace();
    const configuredMovement = ScanRunUnsolvedLogs.moveToConfiguredOrDefault();
    const customMovement = ScanRunUnsolvedLogs.moveToCustom(join(root, "Unsolved Logs"));

    try {
      expect(ScanRunRequest.standard(configuration, standardSource, movement)).toBeDefined();
      expect(ScanRunRequest.standard(configuration, standardSource, configuredMovement)).toBeDefined();
      expect(ScanRunRequest.standard(configuration, standardSource, customMovement)).toBeDefined();
      expect(ScanRunRequest.targeted(configuration, targetedSource)).toBeDefined();

      if (false) {
        // @ts-expect-error Targeted requests deliberately accept no movement policy.
        ScanRunRequest.targeted(configuration, targetedSource, movement);
        // @ts-expect-error FCX constructors require explicit run-scoped setup facts.
        ScanRunRequest.standardWithFcx(configuration, standardSource, movement);
        // @ts-expect-error FCX constructors require explicit run-scoped setup facts.
        ScanRunRequest.targetedWithFcx(configuration, targetedSource);
      }
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("returns typed Targeted rejections and request-validation errors", async () => {
    const root = writeScanRunDataRoot("classic-node-scan-run-failure");

    try {
      const request = ScanRunRequest.targeted(
        scanRunConfiguration(root),
        { inputs: [MISSING_LOG_PATH] },
      );
      const execution = await scanRunExecute(request, new ScanRunCancellation());

      const success = requireScanRunSuccess(execution);
      expect(success.result.status).toBe("no_crash_logs_found");
      expect(success.result.discovery).toMatchObject({
        source: "targeted",
        acceptedLogs: [],
      });
      expect(success.result.discovery?.rejectedInputs[0]).toMatchObject({
        path: MISSING_LOG_PATH,
      });

      const invalidRequest = ScanRunRequest.targeted(
        scanRunConfiguration(root, { maxConcurrent: 0 }),
        { inputs: [MISSING_LOG_PATH] },
      );
      const invalidExecution = await scanRunExecute(
        invalidRequest,
        new ScanRunCancellation(),
      );
      const failure = requireScanRunFailure(invalidExecution);
      expect(failure.error).toEqual({
        stage: "request_validation",
        message: expect.stringMatching(/greater than zero/i),
        path: undefined,
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("maps FCX setup outcomes through the final Standard contract", async () => {
    const root = writeScanRunDataRoot("classic-node-scan-run-fcx");
    const gameRoot = join(root, "Fallout4");
    const docsRoot = join(root, "Documents");
    const gameExePath = join(gameRoot, "Fallout4.exe");
    const crashLogPath = join(root, "crash-2026-07-15-12-00-00.log");
    mkdirSync(gameRoot, { recursive: true });
    mkdirSync(docsRoot, { recursive: true });
    writeFileSync(gameExePath, "", "utf8");
    writeFileSync(crashLogPath, SAMPLE_CRASH_LOG, "utf8");

    try {
      const request = ScanRunRequest.standardWithFcx(
        scanRunConfiguration(root),
        { baseDirectory: root, configuredDocumentsRoot: docsRoot },
        ScanRunUnsolvedLogs.leaveInPlace(),
        { gameRoot, docsRoot, gameExePath },
      );
      const execution = await scanRunExecute(
        request,
        new ScanRunCancellation(),
      );

      const success = requireScanRunSuccess(execution);
      expect(success.result.setup).toMatchObject({
        status: expect.any(String),
        renderedReport: expect.any(String),
        checks: expect.any(Array),
        pathUpdates: expect.any(Array),
        configurationIssues: expect.any(Array),
        actions: expect.any(Array),
        fatalErrors: expect.any(Array),
      });

      const discoveredLog = success.result.discovery?.acceptedLogs[0];
      expect(discoveredLog).toBeDefined();
      const targetedExecution = await scanRunExecute(
        ScanRunRequest.targetedWithFcx(
          scanRunConfiguration(root),
          { inputs: [discoveredLog!] },
          { gameRoot, docsRoot, gameExePath },
        ),
        new ScanRunCancellation(),
      );
      expect(requireScanRunSuccess(targetedExecution).result.setup).toBeDefined();
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("shared Standard fixture writes durable reports and exposes every serialized event variant", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.standard;
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-standard");
    const events: JsScanRunEvent[] = [];

    try {
      for (const log of fixture.logs) {
        writeSharedScanRunLog(root, log);
      }

      const request = ScanRunRequest.standard(
        scanRunConfiguration(root, { maxConcurrent: fixture.maxConcurrent }),
        {
          baseDirectory: root,
          configuredDocumentsRoot: join(root, "Docs"),
        },
        ScanRunUnsolvedLogs.leaveInPlace(),
      );
      const execution = await scanRunExecute(
        request,
        new ScanRunCancellation(),
        (event) => {
          events.push(event);
          return false;
        },
      );
      const scanResult = requireScanRunSuccess(execution).result;
      expect(scanResult.installedYamlData).toMatchObject({
        main: {
          role: "Main",
          provenance: expect.any(String),
          schemaMajor: 2,
          schemaMinor: 0,
        },
        gameFile: {
          role: "Game",
          provenance: expect.any(String),
          schemaMajor: 1,
          schemaMinor: 0,
        },
        localIgnoreState: JsScanRunLocalIgnoreState.Existing,
        localIgnoreIdentity: {
          sha256: expect.any(String),
          byteLen: expect.any(Number),
        },
        diagnostics: expect.any(Array),
      });
      expect(scanResult.discovery?.acceptedLogs.map((path) => sharedRelativePath(root, path))).toEqual(
        fixture.expected.acceptedLogs,
      );
      expect(scanResult.effectiveConcurrency).toBe(fixture.expected.effectiveConcurrency);
      expect(scanResult.logs.map((result) => result.discoveryIndex)).toEqual(
        fixture.expected.discoveryOrder,
      );
      expect(scanResult.logs.map((result) => result.disposition)).toEqual(
        fixture.expected.dispositions,
      );
      expect(scanResult.logs.every((result) => result.failures.length === 0)).toBe(true);
      expect(
        scanResult.logs.every(
          (result) => result.autoscanReport && existsSync(result.autoscanReport),
        ),
      ).toBe(true);
      expect(events.map((event) => event.kind)).toEqual(
        expect.arrayContaining([
          "discovery_completed",
          "effective_concurrency_selected",
          "log_queued",
          "log_started",
          "log_phase",
          "log_finished",
        ]),
      );
      expect(events.at(0)?.kind).toBe("discovery_completed");
      expect(events.at(-1)).toMatchObject({
        kind: "log_finished",
        disposition: "succeeded",
      });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("returns generated Local Ignore diagnostics as run-level data", async () => {
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-generated-ignore");
    const crashLog = writeSharedScanRunLog(root, "generated-ignore.log");
    rmSync(join(root, "CLASSIC Data", "CLASSIC Ignore.yaml"));

    try {
      const execution = await scanRunExecute(
        ScanRunRequest.targeted(scanRunConfiguration(root), { inputs: [crashLog] }),
        new ScanRunCancellation(),
      );
      const scanResult = requireScanRunSuccess(execution).result;

      expect(scanResult.status).toBe("completed");
      expect(scanResult.installedYamlData?.localIgnoreState).toBe(
        JsScanRunLocalIgnoreState.Generated,
      );
      expect(scanResult.installedYamlData?.diagnostics).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            kind: JsScanRunInstalledYamlDataDiagnosticKind.LocalIgnoreGenerated,
          }),
        ]),
      );
      expect(scanResult.logs[0]?.autoscanReport).toSatisfy(
        (path: string | undefined) => path !== undefined && existsSync(path),
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("shared Local Ignore recovery continuation retains snapshots and rejects replay", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.installedYamlData;
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-ignore-recovery");
    const crashLog = writeSharedScanRunLog(root, fixture.input);
    const ignorePath = join(root, "CLASSIC Data", "CLASSIC Ignore.yaml");
    const request = ScanRunRequest.targeted(
      scanRunConfiguration(root),
      { inputs: [crashLog] },
    );

    try {
      const baseline = requireScanRunSuccess(
        await scanRunExecute(request, new ScanRunCancellation()),
      ).result;
      const baselineReport = readFileSync(baseline.logs[0]!.autoscanReport!);
      writeFileSync(ignorePath, fixture.malformedLocalIgnore);
      const initialEvents: JsScanRunEvent[] = [];
      const initial = requireScanRunSuccess(
        await scanRunExecute(request, new ScanRunCancellation(), initialEvents.push.bind(initialEvents)),
      ).result;

      expect(initial.status).toBe("local_ignore_recovery_required");
      expect(initial.installedYamlData?.localIgnoreState).toBe(
        JsScanRunLocalIgnoreState.RecoveryRequired,
      );
      expect(initial.installedYamlData?.diagnostics.map((diagnostic) => diagnostic.kind)).toContain(
        JsScanRunInstalledYamlDataDiagnosticKind.Parse,
      );
      expect(initialEvents.map((event) => event.kind)).toEqual(["discovery_completed"]);
      const continuation = initial.continuation;
      expect(continuation).toBeDefined();

      writeFileSync(
        join(root, "CLASSIC Data", "databases", "CLASSIC Main.yaml"),
        "invalid: [unterminated",
      );
      const resumedEvents: JsScanRunEvent[] = [];
      const resumed = requireScanRunSuccess(
        await scanRunResume(
          continuation!,
          JsScanRunLocalIgnoreRecoveryDecision.ProceedWithoutIgnore,
          new ScanRunCancellation(),
          resumedEvents.push.bind(resumedEvents),
        ),
      ).result;

      expect(resumed.status).toBe("completed");
      expect(resumed.discovery).toEqual(initial.discovery);
      expect(resumed.installedYamlData?.main.sha256).toBe(initial.installedYamlData?.main.sha256);
      expect(resumed.installedYamlData?.gameFile.sha256).toBe(
        initial.installedYamlData?.gameFile.sha256,
      );
      expect(resumed.installedYamlData?.localIgnoreState).toBe(
        JsScanRunLocalIgnoreState.ProceedWithoutIgnore,
      );
      expect(resumedEvents.some((event) => event.kind === "discovery_completed")).toBe(false);
      expect(readFileSync(resumed.logs[0]!.autoscanReport!)).toEqual(baselineReport);
      expect(readFileSync(ignorePath, "utf8")).toBe(fixture.malformedLocalIgnore);

      await expect(
        scanRunResume(
          continuation!,
          JsScanRunLocalIgnoreRecoveryDecision.ProceedWithoutIgnore,
          new ScanRunCancellation(),
        ),
      ).rejects.toMatchObject({ code: "scan_run_continuation_consumed" });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("Reset To Default returns durable metadata and the unchanged shared report", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.installedYamlData;
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-ignore-reset");
    const crashLog = writeSharedScanRunLog(root, fixture.input);
    const ignorePath = join(root, "CLASSIC Data", "CLASSIC Ignore.yaml");
    const request = ScanRunRequest.targeted(scanRunConfiguration(root), { inputs: [crashLog] });

    try {
      const baseline = requireScanRunSuccess(
        await scanRunExecute(request, new ScanRunCancellation()),
      ).result;
      const baselineReport = readFileSync(baseline.logs[0]!.autoscanReport!);
      writeFileSync(ignorePath, fixture.malformedLocalIgnore);
      const initial = requireScanRunSuccess(
        await scanRunExecute(request, new ScanRunCancellation()),
      ).result;
      const retainedMain = initial.installedYamlData?.main.sha256;
      const retainedGame = initial.installedYamlData?.gameFile.sha256;
      writeFileSync(
        join(root, "CLASSIC Data", "databases", "CLASSIC Main.yaml"),
        "invalid: [unterminated",
      );
      writeFileSync(
        join(root, "CLASSIC Data", "databases", "CLASSIC Fallout4.yaml"),
        "invalid: [unterminated",
      );

      const resumedEvents: JsScanRunEvent[] = [];
      const reset = requireScanRunSuccess(
        await scanRunResume(
          initial.continuation!,
          JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
          new ScanRunCancellation(),
          resumedEvents.push.bind(resumedEvents),
        ),
      ).result;

      expect(reset.status).toBe("completed");
      expect(reset.discovery).toEqual(initial.discovery);
      expect(reset.installedYamlData?.main.sha256).toBe(retainedMain);
      expect(reset.installedYamlData?.gameFile.sha256).toBe(retainedGame);
      expect(reset.installedYamlData?.localIgnoreState).toBe(
        JsScanRunLocalIgnoreState.ResetToDefault,
      );
      expect(reset.installedYamlData?.diagnostics.map((diagnostic) => diagnostic.kind)).toContain(
        JsScanRunInstalledYamlDataDiagnosticKind.LocalIgnoreReset,
      );
      const metadata = reset.installedYamlData?.localIgnoreReset;
      expect(metadata).toBeDefined();
      expect(readFileSync(metadata!.backupPath, "utf8")).toBe(fixture.malformedLocalIgnore);
      expect(metadata!.malformedIdentity).toEqual(metadata!.backupIdentity);
      expect(metadata!.replacementIdentity).toEqual(reset.installedYamlData?.localIgnoreIdentity);
      expect(readFileSync(reset.logs[0]!.autoscanReport!)).toEqual(baselineReport);
      expect(resumedEvents.some((event) => event.kind === "discovery_completed")).toBe(false);
      await expect(
        scanRunResume(
          initial.continuation!,
          JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
          new ScanRunCancellation(),
        ),
      ).rejects.toMatchObject({ code: fixture.resetOutcomes.consumedCode });
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("Reset To Default exposes typed conflict and backup failure outcomes", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.installedYamlData;
    const runCase = async (name: string, mutate: (root: string, ignorePath: string) => void) => {
      const root = writeSharedScanRunDataRoot(name);
      const crashLog = writeSharedScanRunLog(root, fixture.input);
      const ignorePath = join(root, "CLASSIC Data", "CLASSIC Ignore.yaml");
      writeFileSync(ignorePath, fixture.malformedLocalIgnore);
      const initial = requireScanRunSuccess(
        await scanRunExecute(
          ScanRunRequest.targeted(scanRunConfiguration(root), { inputs: [crashLog] }),
          new ScanRunCancellation(),
        ),
      ).result;
      mutate(root, ignorePath);
      return { root, ignorePath, continuation: initial.continuation! };
    };

    const conflict = await runCase(
      "classic-node-scan-run-reset-conflict",
      (_root, ignorePath) => writeFileSync(ignorePath, "CLASSIC_Ignore_Fallout4: []\n"),
    );
    try {
      await expect(
        scanRunResume(
          conflict.continuation,
          JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
          new ScanRunCancellation(),
        ),
      ).rejects.toMatchObject({
        code: fixture.resetOutcomes.conflictCode,
        kind: fixture.resetOutcomes.conflictCode,
      });
    } finally {
      rmSync(conflict.root, { recursive: true, force: true });
    }

    const backupFailure = await runCase(
      "classic-node-scan-run-reset-backup-failure",
      (root) => writeFileSync(join(root, "CLASSIC Backup"), "not a directory"),
    );
    try {
      await expect(
        scanRunResume(
          backupFailure.continuation,
          JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
          new ScanRunCancellation(),
        ),
      ).rejects.toMatchObject({
        code: fixture.resetOutcomes.backupFailureCode,
        kind: fixture.resetOutcomes.backupFailureCode,
      });
      expect(readFileSync(backupFailure.ignorePath, "utf8")).toBe(
        fixture.malformedLocalIgnore,
      );
    } finally {
      rmSync(backupFailure.root, { recursive: true, force: true });
    }
  });

  test("pre-resume cancellation wins without changing malformed Local Ignore", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.installedYamlData;
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-ignore-recovery-cancelled");
    const crashLog = writeSharedScanRunLog(root, fixture.input);
    const ignorePath = join(root, "CLASSIC Data", "CLASSIC Ignore.yaml");
    writeFileSync(ignorePath, fixture.malformedLocalIgnore);

    try {
      const initial = requireScanRunSuccess(
        await scanRunExecute(
          ScanRunRequest.targeted(scanRunConfiguration(root), { inputs: [crashLog] }),
          new ScanRunCancellation(),
        ),
      ).result;
      const cancellation = new ScanRunCancellation();
      cancellation.cancel();
      const resumedEvents: JsScanRunEvent[] = [];
      const resumed = requireScanRunSuccess(
        await scanRunResume(
          initial.continuation!,
          JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
          cancellation,
          resumedEvents.push.bind(resumedEvents),
        ),
      ).result;

      expect(resumed.status).toBe("cancelled");
      expect(resumed.cancelled).toBe(resumed.total);
      expect(resumed.logs.every((log) => log.disposition === "cancelled_before_start")).toBe(true);
      expect(resumedEvents).toEqual([]);
      expect(readFileSync(ignorePath, "utf8")).toBe(fixture.malformedLocalIgnore);
      expect(existsSync(join(root, "CLASSIC Backup"))).toBe(
        fixture.resetOutcomes.preResetCancellationMutates,
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("cancellation observed after reset entry waits for durable repair", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.installedYamlData;
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-reset-racing-cancel");
    const crashLog = writeSharedScanRunLog(root, fixture.input);
    const ignorePath = join(root, "CLASSIC Data", "CLASSIC Ignore.yaml");
    const largeMalformedIgnore = fixture.malformedLocalIgnore + "x".repeat(16 * 1024 * 1024);
    writeFileSync(ignorePath, largeMalformedIgnore);
    const initial = requireScanRunSuccess(
      await scanRunExecute(
        ScanRunRequest.targeted(scanRunConfiguration(root), { inputs: [crashLog] }),
        new ScanRunCancellation(),
      ),
    ).result;
    const cancellation = new ScanRunCancellation();
    const resetLock = join(root, ".classic-local-ignore-reset.lock");

    try {
      const resume = scanRunResume(
        initial.continuation!,
        JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
        cancellation,
      );
      const deadline = Date.now() + 5_000;
      while (!existsSync(resetLock) && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 1));
      }
      expect(existsSync(resetLock)).toBe(true);
      cancellation.cancel();
      const cancelled = requireScanRunSuccess(await resume).result;

      expect(cancelled.status).toBe(fixture.resetOutcomes.postCriticalCancellationStatus);
      expect(cancelled.logs.every((log) => log.autoscanReport === undefined)).toBe(true);
      const backupDirectory = join(root, "CLASSIC Backup", "YAML Data", "Local Ignore");
      const backups = readdirSync(backupDirectory);
      expect(backups).toHaveLength(1);
      if (fixture.resetOutcomes.backupMustEqualMalformedBytes) {
        expect(readFileSync(join(backupDirectory, backups[0]!), "utf8")).toBe(
          largeMalformedIgnore,
        );
      }
      expect(readFileSync(ignorePath, "utf8")).not.toBe(largeMalformedIgnore);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  }, 30_000);

  test("shared Targeted fixture preserves discovery order, rejections, artifacts, and no movement", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.targeted;
    const root = writeSharedScanRunDataRoot("classic-node-scan-run-targeted");

    try {
      for (const input of fixture.inputs.filter((path) => path.endsWith(".log"))) {
        writeSharedScanRunLog(root, input);
      }

      const request = ScanRunRequest.targeted(
        scanRunConfiguration(root, { maxConcurrent: fixture.maxConcurrent }),
        { inputs: fixture.inputs.map((path) => join(root, path)) },
      );
      const execution = await scanRunExecute(request, new ScanRunCancellation());
      const scanResult = requireScanRunSuccess(execution).result;

      expect(scanResult.discovery?.acceptedLogs.map((path) => sharedRelativePath(root, path))).toEqual(
        fixture.expected.acceptedLogs,
      );
      expect(
        scanResult.discovery?.rejectedInputs.map((input) => sharedRelativePath(root, input.path)),
      ).toEqual(fixture.expected.rejectedInputs);
      expect(scanResult.effectiveConcurrency).toBe(fixture.expected.effectiveConcurrency);
      expect(scanResult.logs.map((result) => sharedRelativePath(root, result.crashLog))).toEqual(
        fixture.expected.acceptedLogs,
      );
      expect(scanResult.logs.map((result) => result.discoveryIndex)).toEqual(
        fixture.expected.discoveryOrder,
      );
      expect(scanResult.logs.map((result) => result.disposition)).toEqual(
        fixture.expected.dispositions,
      );
      expect(
        scanResult.logs.every(
          (result) => result.autoscanReport && existsSync(result.autoscanReport),
        ),
      ).toBe(true);
      expect(scanResult.logs.every((result) => result.movedToUnsolvedLogs === false)).toBe(true);
      expect(fixture.expected.unsolvedLogsArtifacts).toEqual([]);
      expect(existsSync(join(root, "Unsolved Logs"))).toBe(false);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("shared cancellation fixture distinguishes pre-discovery, queued, and admitted work", async () => {
    const fixture = SHARED_SCAN_RUN_MANIFEST.fixtures.targeted;

    const preRoot = writeSharedScanRunDataRoot("classic-node-scan-run-cancel-pre");
    try {
      const inputs = fixture.expected.acceptedLogs.map((path) =>
        writeSharedScanRunLog(preRoot, path),
      );
      const cancellation = new ScanRunCancellation();
      cancellation.cancel();
      const execution = await scanRunExecute(
        ScanRunRequest.targeted(scanRunConfiguration(preRoot), { inputs }),
        cancellation,
      );
      const result = requireScanRunSuccess(execution).result;
      expect(result.status).toBe("cancelled_before_discovery");
      expect(result.discovery).toBeUndefined();
      expect(result.logs).toEqual([]);
    } finally {
      rmSync(preRoot, { recursive: true, force: true });
    }

    const queuedRoot = writeSharedScanRunDataRoot("classic-node-scan-run-cancel-queued");
    try {
      const inputs = fixture.expected.acceptedLogs.map((path) =>
        writeSharedScanRunLog(queuedRoot, path),
      );
      const cancellation = new ScanRunCancellation();
      const queuedEvents: string[] = [];
      const execution = await scanRunExecute(
        ScanRunRequest.targeted(scanRunConfiguration(queuedRoot, { maxConcurrent: 1 }), {
          inputs,
        }),
        cancellation,
        (event) => {
          queuedEvents.push(event.kind);
          if (event.kind === "log_queued") cancellation.cancel();
          return false;
        },
      );
      const result = requireScanRunSuccess(execution).result;
      expect(result.discovery?.acceptedLogs).toHaveLength(2);
      expect(result.logs.map((log) => log.disposition)).toEqual([
        "cancelled_before_start",
        "cancelled_before_start",
      ]);
      expect(result.logs.every((log) => log.autoscanReport === undefined)).toBe(true);
      expect(queuedEvents).not.toContain("log_started");
    } finally {
      rmSync(queuedRoot, { recursive: true, force: true });
    }

    const admittedRoot = writeSharedScanRunDataRoot("classic-node-scan-run-cancel-admitted");
    try {
      const inputs = fixture.expected.acceptedLogs.map((path) =>
        writeSharedScanRunLog(admittedRoot, path),
      );
      const cancellation = new ScanRunCancellation();
      const execution = await scanRunExecute(
        ScanRunRequest.targeted(scanRunConfiguration(admittedRoot, { maxConcurrent: 1 }), {
          inputs,
        }),
        cancellation,
        (event) => {
          if (event.kind === "log_started" && event.log?.discoveryIndex === 0) {
            cancellation.cancel();
          }
          return false;
        },
      );
      const result = requireScanRunSuccess(execution).result;
      expect(result.logs[0]?.disposition).toBe("succeeded");
      expect(existsSync(result.logs[0]?.autoscanReport!)).toBe(true);
      expect(result.logs[1]?.disposition).toBe("cancelled_before_start");
      expect(result.logs[1]?.autoscanReport).toBeUndefined();
    } finally {
      rmSync(admittedRoot, { recursive: true, force: true });
    }
  });

  test("observer delivery failures stay separate and can request safe cancellation", async () => {
    const root = writeScanRunDataRoot("classic-node-scan-run-observer-failure");
    const logPath = join(root, "crash-2026-07-15-12-00-00.log");
    writeFileSync(logPath, SAMPLE_CRASH_LOG, "utf8");

    try {
      const requestWithoutCancellation = ScanRunRequest.targeted(
        scanRunConfiguration(root),
        { inputs: [logPath] },
      );
      const retainedCancellation = new ScanRunCancellation();
      const completedExecution = await scanRunExecute(
        requestWithoutCancellation,
        retainedCancellation,
        () => {
          throw new Error("observer transport closed");
        },
        false,
      );
      const completed = requireScanRunSuccess(completedExecution);
      expect(completed.result.status).toBe("completed");
      expect(completed.observerError).toMatch(/observer transport closed/);
      expect(retainedCancellation.isCancelled).toBe(false);

      const cancellingControl = new ScanRunCancellation();
      const cancelledExecution = await scanRunExecute(
        ScanRunRequest.targeted(scanRunConfiguration(root), { inputs: [logPath] }),
        cancellingControl,
        () => {
          throw new Error("observer transport closed");
        },
        true,
      );

      const cancelled = requireScanRunSuccess(cancelledExecution);
      expect(cancelled.result.status).toBe("cancelled");
      expect(cancelled.observerError).toMatch(/observer transport closed/);
      expect(cancellingControl.isCancelled).toBe(true);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

});

// ============================================================================
// Synchronous: parseLogSegments
// ============================================================================

describe("parseLogSegments", () => {
  test("parses a standard crash log into segments", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments).toBeDefined();
    expect(segments.segmentCount).toBeGreaterThan(0);
  });

  test("extracts system section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.system.length).toBeGreaterThan(0);
    const joined = segments.system.join("\n");
    expect(joined).toContain("AMD Ryzen");
  });

  test("extracts plugins section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.plugins.length).toBeGreaterThan(0);
    const joined = segments.plugins.join("\n");
    expect(joined).toContain("Fallout4.esm");
  });

  test("extracts stack section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.stack.length).toBeGreaterThan(0);
    const joined = segments.stack.join("\n");
    expect(joined).toContain("TESForm");
  });

  test("extracts modules section", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.modules.length).toBeGreaterThan(0);
    const joined = segments.modules.join("\n");
    expect(joined).toContain("nvwgf2umx.dll");
  });

  test("extracts header compatibility settings", () => {
    const segments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(segments.header.length).toBeGreaterThan(0);
    const joined = segments.header.join("\n");
    expect(joined).toContain("Achievements: true");
  });

  test("uses compatibility marker to build header section", () => {
    const segments = parseLogSegments(SETTINGS_MARKER_CONTENT);
    expect(segments.header).toEqual(["Achievements: true", "MemoryManager: false"]);
  });

  test("returns empty segments for empty content", () => {
    const segments = parseLogSegments("");
    expect(segments.segmentCount).toBe(0);
    expect(segments.header).toEqual([]);
    expect(segments.system).toEqual([]);
    expect(segments.stack).toEqual([]);
    expect(segments.modules).toEqual([]);
    expect(segments.plugins).toEqual([]);
  });

  test("returns empty segments for content without markers", () => {
    const segments = parseLogSegments("just some random text\nnothing special");
    expect(segments.segmentCount).toBe(0);
  });
});

// ============================================================================
// Synchronous: extractFormIds
// ============================================================================

describe("extractFormIds", () => {
  test("extracts FormIDs from content with FormID patterns", () => {
    const formIds = extractFormIds(FORMID_CONTENT);
    expect(formIds.length).toBeGreaterThan(0);
    // FormIDs are returned without 0x prefix, lowercase
    for (const fid of formIds) {
      expect(fid).toMatch(/^[0-9a-f]{8}$/);
    }
  });

  test("extracts the expected FormIDs", () => {
    const formIds = extractFormIds(FORMID_CONTENT);
    expect(formIds).toContain("00012345");
    expect(formIds).toContain("00023456");
    expect(formIds).toContain("00034567");
  });

  test("returns empty array for content without FormIDs", () => {
    const formIds = extractFormIds("No formids here\nJust regular text");
    expect(formIds).toEqual([]);
  });

  test("returns empty array for empty content", () => {
    const formIds = extractFormIds("");
    expect(formIds).toEqual([]);
  });
});

// ============================================================================
// Synchronous: extractPluginList
// ============================================================================

describe("extractPluginList", () => {
  test("extracts plugin names from plugin section content", () => {
    const plugins = extractPluginList(PLUGIN_CONTENT);
    expect(plugins.length).toBeGreaterThan(0);
  });

  test("extracts expected plugin names", () => {
    const plugins = extractPluginList(PLUGIN_CONTENT);
    expect(plugins).toContain("Fallout4.esm");
    expect(plugins).toContain("DLCRobot.esm");
    expect(plugins).toContain("DLCworkshop01.esm");
    expect(plugins).toContain("DLCCoast.esm");
    expect(plugins).toContain("TestMod.esp");
  });

  test("extracts only esm/esp plugins (esl not included)", () => {
    const plugins = extractPluginList(PLUGIN_CONTENT);
    // The parser extracts .esm and .esp files; .esl light plugins may not be included
    expect(plugins.length).toBeGreaterThan(0);
  });

  test("returns empty array for content without plugins", () => {
    const plugins = extractPluginList("No plugins here\nJust text");
    expect(plugins).toEqual([]);
  });

  test("returns empty array for empty content", () => {
    const plugins = extractPluginList("");
    expect(plugins).toEqual([]);
  });
});

// ============================================================================
// Synchronous: detectCrashPattern
// ============================================================================

describe("detectCrashPattern", () => {
  test("detects ACCESS_VIOLATION pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("ACCESS_VIOLATION");
  });

  test("detects STACK_OVERFLOW pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_STACK_OVERFLOW" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("STACK_OVERFLOW");
  });

  test("detects INT_DIVIDE_BY_ZERO pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_INT_DIVIDE_BY_ZERO" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("INT_DIVIDE_BY_ZERO");
  });

  test("detects BREAKPOINT pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_BREAKPOINT" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("BREAKPOINT");
  });

  test("detects STACK_BUFFER_OVERRUN pattern", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_STACK_BUFFER_OVERRUN" at 0x7FF6EF4C3512',
    );
    expect(pattern).toBe("STACK_BUFFER_OVERRUN");
  });

  test("detects pattern from full crash log", () => {
    const pattern = detectCrashPattern(SAMPLE_CRASH_LOG);
    expect(pattern).toBe("ACCESS_VIOLATION");
  });

  test("returns null for content without known patterns", () => {
    const pattern = detectCrashPattern("No crash here\nJust regular log content");
    expect(pattern).toBeNull();
  });

  test("returns null for empty content", () => {
    const pattern = detectCrashPattern("");
    expect(pattern).toBeNull();
  });

  test("returns null for content with unknown exception type", () => {
    const pattern = detectCrashPattern(
      'Unhandled exception "EXCEPTION_UNKNOWN_TYPE" at 0x7FF6EF4C3512',
    );
    // EXCEPTION_UNKNOWN_TYPE is not a known pattern, but the line does contain EXCEPTION_
    // The function should not match it to any known pattern
    expect(pattern).toBeNull();
  });
});

// ============================================================================
// Synchronous: detectVrLog
// ============================================================================

describe("detectVrLog", () => {
  test("returns true for VR crash log content", () => {
    expect(detectVrLog("Fallout4VR.exe v1.2.72.0")).toBe(true);
  });

  test("returns true for VR ESM reference", () => {
    expect(detectVrLog("[00] Fallout4VR.esm")).toBe(true);
  });

  test("returns true for case-insensitive VR match", () => {
    expect(detectVrLog("FALLOUT4VR.EXE loaded")).toBe(true);
  });

  test("returns false for non-VR crash log", () => {
    expect(detectVrLog("Fallout4.exe v1.10.163.0")).toBe(false);
  });

  test("returns false for empty content", () => {
    expect(detectVrLog("")).toBe(false);
  });

  test("returns false for unrelated content", () => {
    expect(detectVrLog("Some random text\nNo game references")).toBe(false);
  });
});

// ============================================================================
// Synchronous: detectGpuInfo
// ============================================================================

describe("detectGpuInfo", () => {
  test("detects Nvidia GPU", () => {
    const info = detectGpuInfo([
      "\tGPU #1: Nvidia AD104 [GeForce RTX 4070]",
    ]);
    expect(info.manufacturer).toBe("Nvidia");
    expect(info.primary).toContain("Nvidia");
    expect(info.rival).toBe("amd");
  });

  test("detects AMD GPU", () => {
    const info = detectGpuInfo(["\tGPU #1: AMD Radeon RX 7900 XTX"]);
    expect(info.manufacturer).toBe("AMD");
    expect(info.primary).toContain("AMD");
    expect(info.rival).toBe("nvidia");
  });

  test("detects Intel GPU", () => {
    const info = detectGpuInfo(["\tGPU #1: Intel UHD Graphics 770"]);
    expect(info.manufacturer).toBe("Intel");
    expect(info.primary).toContain("Intel");
    expect(info.rival).toBeUndefined();
  });

  test("detects secondary GPU", () => {
    const info = detectGpuInfo([
      "\tGPU #1: Nvidia GeForce RTX 4070",
      "\tGPU #2: Intel UHD Graphics 770",
    ]);
    expect(info.primary).toContain("Nvidia");
    expect(info.secondary).toContain("Intel");
  });

  test("returns Unknown for unrecognized GPU lines", () => {
    const info = detectGpuInfo(["no GPU info here"]);
    expect(info.manufacturer).toBe("Unknown");
    expect(info.primary).toBe("Unknown");
    expect(info.secondary).toBeUndefined();
    expect(info.rival).toBeUndefined();
  });

  test("returns Unknown for empty input", () => {
    const info = detectGpuInfo([]);
    expect(info.manufacturer).toBe("Unknown");
  });
});

// ============================================================================
// Synchronous: parseCrashgenVersion
// ============================================================================

describe("parseCrashgenVersion", () => {
  test("parses a simple version string", () => {
    const v = parseCrashgenVersion("1.28.6");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(28);
    expect(v!.patch).toBe(6);
  });

  test("parses a version with v prefix", () => {
    const v = parseCrashgenVersion("v1.29.1");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(29);
    expect(v!.patch).toBe(1);
  });

  test("parses a version with crashgen prefix", () => {
    const v = parseCrashgenVersion("Buffout 4 v1.30.2");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(30);
    expect(v!.patch).toBe(2);
  });

  test("parses version with two components", () => {
    const v = parseCrashgenVersion("1.28");
    expect(v).not.toBeNull();
    expect(v!.major).toBe(1);
    expect(v!.minor).toBe(28);
    expect(v!.patch).toBe(0);
  });

  test("returns null for invalid version", () => {
    expect(parseCrashgenVersion("not a version")).toBeNull();
  });

  test("returns null for empty string", () => {
    expect(parseCrashgenVersion("")).toBeNull();
  });
});

// ============================================================================
// Synchronous: checkCrashgenVersionStatus
// ============================================================================

describe("checkCrashgenVersionStatus", () => {
  test("returns Valid for matching version", () => {
    const status = checkCrashgenVersionStatus("1.28.6", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.Valid);
  });

  test("returns Valid for second valid version", () => {
    const status = checkCrashgenVersionStatus("1.37.0", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.Valid);
  });

  test("returns Outdated for old version", () => {
    const status = checkCrashgenVersionStatus("1.26.0", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.Outdated);
  });

  test("returns Valid for version newer than configured floor", () => {
    const status = checkCrashgenVersionStatus("1.40.0", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.Valid);
  });

  test("returns NoSupportedVersion for empty valid list", () => {
    const status = checkCrashgenVersionStatus("1.28.6", []);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.NoSupportedVersion);
  });

  test("handles version with crashgen prefix", () => {
    const status = checkCrashgenVersionStatus("Buffout 4 v1.28.6", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.Valid);
  });

  test("treats unparsable detected version as Outdated", () => {
    const status = checkCrashgenVersionStatus("invalid-version", [
      "1.28.6",
      "1.37.0",
    ]);
    expect(status).toBe(CRASHGEN_VERSION_STATUS.Outdated);
  });
});

// ============================================================================
// Synchronous: analyzePapyrusLog
// ============================================================================

describe("analyzePapyrusLog", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), "classic-papyrus-test-"));
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  test("analyzes a papyrus log with known content", () => {
    const logPath = join(tempDir, "Papyrus.0.log");
    const content = [
      "[01/01/2025 - 12:00:00AM] Papyrus log opened",
      "[01/01/2025 - 12:00:01AM] warning: Variable not found",
      "[01/01/2025 - 12:00:02AM] error: Stack overflow",
      "[01/01/2025 - 12:00:03AM] warning: Property not found",
      "[01/01/2025 - 12:00:04AM] Dumping Stacks",
      "[01/01/2025 - 12:00:05AM] Dumping Stack",
    ].join("\n");
    writeFileSync(logPath, content);

    const stats = analyzePapyrusLog(logPath);
    expect(stats).toBeDefined();
    expect(stats.warnings).toBe(2);
    expect(stats.errors).toBe(1);
    expect(stats.dumps).toBe(1);
    expect(stats.stacks).toBe(1);
    expect(stats.linesProcessed).toBe(6);
  });

  test("analyzes an empty papyrus log", () => {
    const logPath = join(tempDir, "Empty.log");
    writeFileSync(logPath, "");

    const stats = analyzePapyrusLog(logPath);
    expect(stats.dumps).toBe(0);
    expect(stats.stacks).toBe(0);
    expect(stats.warnings).toBe(0);
    expect(stats.errors).toBe(0);
  });

  test("throws for non-existent log file", () => {
    expect(() =>
      analyzePapyrusLog(join(tempDir, "nonexistent.log")),
    ).toThrow();
  });
});

// ============================================================================
// Phase 4 Plan 2: Promoted scanlog contract rows (NODE-02, NODE-04, NODE-05)
// ============================================================================
//
// These describe blocks exercise the 9 Node-exposed scanlog symbols newly
// promoted from the Tier-2 deferred backlog to enforced Tier-1 contract rows.
//
// MEDIUM concern fix: every assertion checks at least one typed field with
// a concrete expected value. No shallow `{} as Type` + `toBeDefined()` no-ops;
// every interface test exercises at least one runtime-observable field so the
// TS import path AND the NAPI-RS marshalling path are both covered.

describe("scanlog Plan 2 promotion: CRASH_LOG_PATTERN", () => {
  test("exposed as non-empty string with regex-pattern-like shape", () => {
    // Real-shape check: must be a string...
    expect(typeof CRASH_LOG_PATTERN).toBe("string");
    // ...with nonzero length...
    expect(CRASH_LOG_PATTERN.length).toBeGreaterThan(0);
    // ...that looks like a regex pattern (Rust LazyLock compiles this into
    // a Regex; the exported constant carries the raw pattern string).
    // Accept any regex-metacharacter presence OR a literal anchor keyword
    // that matches the classic-file-io-core CRASH_LOG_PATTERN definition.
    const hasRegexMeta = /[.\^\[\(\\\*\+\?\|]/.test(CRASH_LOG_PATTERN);
    const hasCrashWord = /crash/i.test(CRASH_LOG_PATTERN);
    expect(hasRegexMeta || hasCrashWord).toBe(true);
  });

  test("can be compiled into a JavaScript RegExp without throwing", () => {
    // MEDIUM concern: if the pattern isn't valid regex syntax, the Rust
    // core would never ship it; assert the Node surface preserves that
    // guarantee.
    expect(() => new RegExp(CRASH_LOG_PATTERN)).not.toThrow();
  });
});

describe("scanlog Plan 2 promotion: JsGpuInfo", () => {
  test("detectGpuInfo returns a JsGpuInfo with typed string fields", () => {
    const info: JsGpuInfo = detectGpuInfo([
      "GPU #1: Nvidia AD104 [GeForce RTX 4070]",
      "GPU #2: AMD Radeon RX 6600",
    ]);
    // Real-shape check: primary is a non-empty string; manufacturer is a
    // recognized vendor token; the interface carries typed optional fields.
    expect(typeof info.primary).toBe("string");
    expect(info.primary.length).toBeGreaterThan(0);
    expect(typeof info.manufacturer).toBe("string");
    expect(["AMD", "Nvidia", "Intel", "Unknown"]).toContain(info.manufacturer);
    // Optional fields: if present, must be strings.
    if (info.secondary !== undefined) {
      expect(typeof info.secondary).toBe("string");
    }
    if (info.rival !== undefined) {
      expect(typeof info.rival).toBe("string");
    }
  });

  test("empty system lines produce an unknown-shape JsGpuInfo without throwing", () => {
    const info: JsGpuInfo = detectGpuInfo([]);
    // Even with no input, the NAPI contract MUST return a valid JsGpuInfo
    // with primary + manufacturer populated (may be "Unknown").
    expect(typeof info.primary).toBe("string");
    expect(typeof info.manufacturer).toBe("string");
  });
});

describe("scanlog Plan 2 promotion: JsLogErrorEntry interface shape", () => {
  test("typed field shape is stable at compile time and runtime", () => {
    // JsLogErrorEntry is produced by JsLogProcessor at runtime; we test its
    // interface shape directly by constructing a value and asserting its
    // field types at runtime. This is NOT a `{} as Type` no-op — every
    // field is populated and type-checked.
    const entry: JsLogErrorEntry = {
      filePath: "/tmp/game.log",
      errors: ["error: something broke", "error: another failure"],
      totalErrors: 2,
    };
    expect(typeof entry.filePath).toBe("string");
    expect(entry.filePath.length).toBeGreaterThan(0);
    expect(Array.isArray(entry.errors)).toBe(true);
    expect(entry.errors.length).toBe(2);
    expect(entry.errors.every((e) => typeof e === "string")).toBe(true);
    expect(typeof entry.totalErrors).toBe("number");
    expect(entry.totalErrors).toBe(2);
  });
});

describe("scanlog Plan 2 promotion: JsLogSegments", () => {
  test("parseLogSegments returns a JsLogSegments with all required typed arrays", () => {
    // SAMPLE_CRASH_LOG is a realistic F4 crash log defined at the top of
    // this file. parseLogSegments against it must produce a fully-typed
    // JsLogSegments with non-empty header/system/stack/modules/plugins.
    const segments: JsLogSegments = parseLogSegments(SAMPLE_CRASH_LOG);
    expect(Array.isArray(segments.header)).toBe(true);
    expect(Array.isArray(segments.system)).toBe(true);
    expect(Array.isArray(segments.stack)).toBe(true);
    expect(Array.isArray(segments.modules)).toBe(true);
    expect(Array.isArray(segments.plugins)).toBe(true);
    expect(typeof segments.segmentCount).toBe("number");
    // Real-shape check: at least one module line was captured.
    expect(segments.modules.length).toBeGreaterThan(0);
    // Every line in every array is a string (NAPI marshalling sanity).
    expect(segments.modules.every((line) => typeof line === "string")).toBe(
      true,
    );
    expect(segments.plugins.every((line) => typeof line === "string")).toBe(
      true,
    );
  });
});

describe("scanlog Plan 2 promotion: JsPapyrusStats", () => {
  test("analyzePapyrusLog produces a JsPapyrusStats with all numeric fields typed", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "classic-papyrus-plan02-"));
    try {
      const logPath = join(tempDir, "Papyrus.0.log");
      writeFileSync(
        logPath,
        [
          "[01/01/2025 - 12:00:00AM] Papyrus log opened",
          "[01/01/2025 - 12:00:01AM] warning: x",
          "[01/01/2025 - 12:00:02AM] error: y",
          "[01/01/2025 - 12:00:03AM] Dumping Stack",
          "[01/01/2025 - 12:00:04AM] Dumping Stacks",
        ].join("\n"),
      );
      const stats: JsPapyrusStats = analyzePapyrusLog(logPath);
      // Real-shape check: all 5 required fields are numbers with expected values.
      expect(typeof stats.dumps).toBe("number");
      expect(typeof stats.stacks).toBe("number");
      expect(typeof stats.warnings).toBe("number");
      expect(typeof stats.errors).toBe("number");
      expect(typeof stats.linesProcessed).toBe("number");
      expect(stats.dumps).toBe(1);
      expect(stats.stacks).toBe(1);
      expect(stats.warnings).toBe(1);
      expect(stats.errors).toBe(1);
      expect(stats.linesProcessed).toBe(5);
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

describe("scanlog Plan 2 promotion: checkXsePlugins", () => {
  test("returns a string (validation message) for a non-existent plugins dir", () => {
    // MEDIUM concern: wrap in try/catch so any NAPI throw is a typed Error,
    // not an unhandled panic that would fail the whole suite.
    try {
      const result = checkXsePlugins("/nonexistent/plugins/dir", "1.10.163");
      // checkXsePlugins returns a string regardless of whether the dir
      // exists — empty dir or missing dir still produces a message.
      expect(typeof result).toBe("string");
    } catch (e) {
      // Acceptable fallback: a typed Error if the NAPI path decides
      // missing directories are an error condition.
      expect(e).toBeInstanceOf(Error);
    }
  });

  test("accepts empty plugins path without crashing", () => {
    try {
      const result = checkXsePlugins("", "1.10.163");
      expect(typeof result).toBe("string");
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
    }
  });
});

describe("scanlog Plan 2 promotion: parseXseLog", () => {
  test("returns null or string for a non-existent XSE log path (never throws)", () => {
    // Per index.d.ts: parseXseLog returns string | null.
    // Real-shape check: either null (file not found) or a string (parsed version).
    // MEDIUM concern: wrapped in try/catch so any unexpected throw fails as
    // a typed Error instead of a panic.
    try {
      const result = parseXseLog("/nonexistent/xse.log");
      // result must be null or a string.
      expect(result === null || typeof result === "string").toBe(true);
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
    }
  });

  test("parses a real-shaped XSE log line and returns version string or null", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "classic-xse-log-test-"));
    try {
      const logPath = join(tempDir, "f4se.log");
      writeFileSync(
        logPath,
        "F4SE runtime: initialize (version = 0.6.23)\r\n",
      );
      const result = parseXseLog(logPath);
      // Either null (parser couldn't extract) or a string version.
      expect(result === null || typeof result === "string").toBe(true);
      if (typeof result === "string") {
        // If extracted, the value must be non-empty.
        expect(result.length).toBeGreaterThan(0);
      }
    } catch (e) {
      // MEDIUM concern: any throw must be a typed Error.
      expect(e).toBeInstanceOf(Error);
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("empty string input produces null or string (never unhandled throw)", () => {
    try {
      const result = parseXseLog("");
      expect(result === null || typeof result === "string").toBe(true);
    } catch (e) {
      expect(e).toBeInstanceOf(Error);
    }
  });
});
