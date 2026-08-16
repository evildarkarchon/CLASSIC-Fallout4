import { createHash, randomUUID } from "node:crypto";
import type { Dirent } from "node:fs";
import {
  access,
  appendFile,
  copyFile,
  mkdir,
  mkdtemp,
  open,
  readdir,
  readFile,
  rename,
  rm,
  stat,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import type {
  JsInstalledYamlDataRunData,
  JsScanRunConfiguration,
  JsScanRunDisplayLine,
  JsScanRunEvent,
  JsScanRunFailure,
  JsScanRunLogResult,
  JsScanRunRecoveryPrompt,
  JsScanRunResult,
  JsScanRunSuccess,
  ScanRunCancellation,
  ScanRunContinuation,
} from "../index.js";

const RUN_PLAN_ENV = "CLASSIC_CONFORMANCE_RUN_PLAN" as const;
const OUTPUT_ENV = "CLASSIC_CONFORMANCE_OUTPUT" as const;

type InvocationEnvironmentName = typeof RUN_PLAN_ENV | typeof OUTPUT_ENV;
type JsonObject = Record<string, unknown>;

/** Exact byte identity used by durable Local Ignore conformance observations. */
interface FileIdentity extends JsonObject {
  sha256: string;
  byteLength: number;
}

/** One canonical plan-relative path. */
interface PathInput {
  path: string;
}

/** One fixture-backed or intentionally absent runtime input. */
interface FixturePathInput extends PathInput {
  fixtureRef?: string;
}

/** The frozen Standard discovery source. */
interface StandardSourceInput {
  baseDirectory: PathInput;
  configuredDocumentsRoot: PathInput;
}

/** Inputs shared by both frozen Crash Log Scan Run scenarios. */
interface CommonScenarioInput {
  observationProfile?: "failure" | "local-ignore" | "lifecycle";
  installationData: FixturePathInput[];
  directoryInputs?: PathInput[];
  observedPaths?: PathInput[];
  localIgnorePaddingBytes?: number;
  game: string;
  gameVersion: string;
  showFormidValues: boolean;
  simplifyLogs: boolean;
  formidDatabasePaths: Array<string | PathInput>;
  maxConcurrent: number;
  forbiddenEffectPaths?: string[];
  executionFlow?: ExecutionFlowInput;
  continuationFlow?: ContinuationFlowInput;
}

/** Input-only controls for one initial scan execution boundary. */
interface ExecutionFlowInput {
  cancellation:
    | "before-discovery"
    | "on-first-log-queued"
    | "on-first-log-started"
    | "on-observer-failure";
  observerFailure?: ObserverFailureInput | null;
}

/** One deterministic downstream delivery failure requested by the plan. */
interface ObserverFailureInput {
  eventKind: "discovery_completed";
  message: string;
}

/** Input-only instructions for one terminal continuation claim and its replays. */
interface ContinuationFlowInput {
  action: ContinuationActionInput;
  cancellation?: "before-resume" | "after-reset-critical-section";
  postPauseData: FixturePathInput[];
  replays: ContinuationActionInput[];
}

/** One public continuation operation and its decision when resuming. */
type ContinuationActionInput =
  | {
      operation: "resume";
      decision: "proceed-without-ignore" | "reset-to-default";
    }
  | { operation: "abandon"; decision?: never };

/** The frozen Standard scenario input. */
interface StandardScenarioInput extends CommonScenarioInput {
  intent: "standard";
  logInputs: FixturePathInput[];
  standardSource: StandardSourceInput;
  unsolvedLogs: "leave-in-place" | "move-to-custom";
  unsolvedLogsPath?: PathInput;
}

/** The frozen Targeted scenario input. */
interface TargetedScenarioInput extends CommonScenarioInput {
  intent: "targeted";
  targetedInputs: FixturePathInput[];
}

type ScenarioInput = StandardScenarioInput | TargetedScenarioInput;

/** One scenario from the centrally authenticated input-only plan. */
interface RunPlanScenario {
  id: string;
  action: string;
  capabilityIds: string[];
  fixtureRefs: string[];
  input: ScenarioInput;
  normalization: JsonObject;
}

/** Centrally owned participant identity copied into the receipt. */
interface ParticipantIdentity {
  id: string;
  role: string;
  executionInstanceId: string;
}

/** Centrally owned invocation identity copied into the receipt. */
interface InvocationIdentity {
  id: string;
  sourceIdentity: string;
  runPlanDigest: string;
}

/** The private runner's input-only invocation document. */
interface RunPlan {
  schemaVersion: number;
  familyId: string;
  familyVersion: number;
  expectationDigest: string;
  fixtureRoot: string;
  fixtures: Record<string, string>;
  participant: ParticipantIdentity;
  invocation: InvocationIdentity;
  scenarios: RunPlanScenario[];
}

/** A completed or failed scenario receipt. */
interface ScenarioReceipt {
  id: string;
  executionStatus: "completed" | "failed";
  capabilityIds: string[];
  observation: JsonObject;
  failure: { kind: string; message: string } | null;
}

/** Report an invalid private runner invocation or input-only plan. */
class RunnerContractError extends Error {
  /** Create one stable runner-contract failure. */
  constructor(message: string) {
    super(message);
    this.name = "RunnerContractError";
  }
}

/** Return whether an unknown JSON value is a non-array object. */
function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Return one required non-empty string with a path-attributed error. */
function requireString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new RunnerContractError(`${label} must be a non-empty string`);
  }
  return value;
}

/** Return one required Boolean without coercing malformed plan data. */
function requireBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") {
    throw new RunnerContractError(`${label} must be a Boolean`);
  }
  return value;
}

/** Return one required integer without admitting floating-point receipt data. */
function requireInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value)) {
    throw new RunnerContractError(`${label} must be a safe integer`);
  }
  return value;
}

/** Return one required array with a path-attributed error. */
function requireArray(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new RunnerContractError(`${label} must be an array`);
  }
  return value;
}

/** Return one required object with a path-attributed error. */
function requireObject(value: unknown, label: string): JsonObject {
  if (!isObject(value)) {
    throw new RunnerContractError(`${label} must be an object`);
  }
  return value;
}

/** Read one of the two environment-only invocation paths. */
function requireInvocationEnvironment(name: InvocationEnvironmentName): string {
  return requireString(process.env[name], name);
}

/** Load and minimally authenticate one input-only Crash Log Scan Run plan. */
async function loadRunPlan(path: string): Promise<RunPlan> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(await readFile(path, "utf8"));
  } catch (error) {
    throw new RunnerContractError(
      `cannot read conformance run plan: ${errorMessage(error)}`,
    );
  }

  const plan = requireObject(parsed, "run plan");
  if (plan.schemaVersion !== 1 || plan.familyId !== "crash-log-scan-run") {
    throw new RunnerContractError(
      "run plan must be Crash Log Scan Run schema version 1",
    );
  }
  const participant = requireObject(plan.participant, "run plan participant");
  if (
    participant.id !== "node" ||
    participant.role !== "semantic-adapter" ||
    participant.executionInstanceId !== "node"
  ) {
    throw new RunnerContractError(
      "run plan is not the Node semantic-adapter invocation",
    );
  }
  const scenarios = requireArray(plan.scenarios, "run plan scenarios");
  if (scenarios.length === 0) {
    throw new RunnerContractError("run plan must contain scenarios");
  }
  for (const [index, value] of scenarios.entries()) {
    const scenario = requireObject(value, `run plan scenarios[${index}]`);
    if ("expected" in scenario) {
      throw new RunnerContractError(
        "input-only run plan must not contain expectations",
      );
    }
  }
  requireObject(plan.fixtures, "run plan fixtures");
  requireObject(plan.invocation, "run plan invocation");

  return plan as unknown as RunPlan;
}

/** Resolve one canonical plan-relative path beneath a fresh runtime root. */
function runtimePath(root: string, value: unknown, label: string): string {
  const text = requireString(value, label);
  const components = text.split("/");
  if (
    isAbsolute(text) ||
    text.includes("\\") ||
    components.some(
      (component) =>
        component === "" || component === "." || component === "..",
    )
  ) {
    throw new RunnerContractError(
      `${label} must stay beneath the runtime root`,
    );
  }
  const candidate = resolve(root, ...components);
  const projected = relative(root, candidate);
  if (
    projected === "" ||
    projected === ".." ||
    projected.startsWith(`..${sep}`)
  ) {
    throw new RunnerContractError(`${label} escapes the runtime root`);
  }
  return candidate;
}

/** Project one public path result to a canonical runtime-root-relative string. */
function relativePath(root: string, value: unknown, label: string): string {
  const text = requireString(value, label);
  const candidate = resolve(isAbsolute(text) ? text : join(root, text));
  const projected = relative(root, candidate);
  if (
    projected === "" ||
    projected === ".." ||
    projected.startsWith(`..${sep}`)
  ) {
    throw new RunnerContractError(`${label} is outside the fresh runtime root`);
  }
  return projected.split(sep).join("/");
}

/** Create one normalized path carrier used by the common observation contract. */
function pathCarrier(
  root: string,
  value: unknown,
  label: string,
): { path: string } {
  return { path: relativePath(root, value, label) };
}

/** Copy one scenario-declared fixture to its writable runtime destination. */
async function copyDeclaredFixture(
  plan: RunPlan,
  scenario: RunPlanScenario,
  item: FixturePathInput,
  root: string,
  label: string,
): Promise<void> {
  if (item.fixtureRef === undefined) {
    return;
  }
  const reference = requireString(item.fixtureRef, `${label}.fixtureRef`);
  if (!scenario.fixtureRefs.includes(reference)) {
    throw new RunnerContractError(
      `${label}.fixtureRef is not declared by the scenario`,
    );
  }
  const source = requireString(
    plan.fixtures[reference],
    `fixture ${reference}`,
  );
  const destination = runtimePath(root, item.path, `${label}.path`);
  await mkdir(dirname(destination), { recursive: true });
  try {
    await copyFile(source, destination);
  } catch (error) {
    throw new RunnerContractError(
      `cannot copy fixture ${reference}: ${errorMessage(error)}`,
    );
  }
}

/** Materialize every plan-declared file, directory, and Standard discovery root. */
async function materializeScenarioInputs(
  plan: RunPlan,
  scenario: RunPlanScenario,
  root: string,
): Promise<ScenarioInput> {
  const input = scenario.input;
  for (const [index, item] of input.installationData.entries()) {
    await copyDeclaredFixture(
      plan,
      scenario,
      item,
      root,
      `installationData[${index}]`,
    );
  }

  const logInputs =
    input.intent === "standard" ? input.logInputs : input.targetedInputs;
  for (const [index, item] of logInputs.entries()) {
    await copyDeclaredFixture(
      plan,
      scenario,
      item,
      root,
      `${input.intent === "standard" ? "logInputs" : "targetedInputs"}[${index}]`,
    );
  }

  for (const [index, item] of (input.directoryInputs ?? []).entries()) {
    await mkdir(
      runtimePath(root, item.path, `directoryInputs[${index}].path`),
      { recursive: true },
    );
  }

  if (input.intent === "standard") {
    const baseDirectory = runtimePath(
      root,
      input.standardSource.baseDirectory.path,
      "standard baseDirectory.path",
    );
    // A failure scenario can deliberately materialize a regular file here so the
    // public discovery seam, rather than runner setup, owns the resulting error.
    if (!(await pathExists(baseDirectory))) {
      await mkdir(baseDirectory, { recursive: true });
    }
    await mkdir(
      runtimePath(
        root,
        input.standardSource.configuredDocumentsRoot.path,
        "standard configuredDocumentsRoot.path",
      ),
      { recursive: true },
    );
  }
  return input;
}

/** Materialize mutations that the plan deliberately withholds until after the run pauses. */
async function materializePostPauseData(
  plan: RunPlan,
  scenario: RunPlanScenario,
  items: FixturePathInput[],
  root: string,
): Promise<void> {
  for (const [index, item] of items.entries()) {
    await copyDeclaredFixture(
      plan,
      scenario,
      item,
      root,
      `continuationFlow.postPauseData[${index}]`,
    );
  }
}

/** Append scenario-owned bytes that make the reset critical section observable. */
async function appendLocalIgnorePadding(
  input: ScenarioInput,
  root: string,
): Promise<void> {
  if (input.localIgnorePaddingBytes === undefined) {
    return;
  }
  const byteLength = requireInteger(
    input.localIgnorePaddingBytes,
    "localIgnorePaddingBytes",
  );
  if (byteLength < 0) {
    throw new RunnerContractError(
      "localIgnorePaddingBytes must be non-negative",
    );
  }
  await appendFile(
    join(root, "CLASSIC Data", "CLASSIC Ignore.yaml"),
    Buffer.alloc(byteLength, "x", "ascii"),
  );
}

/** Convert PascalCase binding enums to their frozen lowercase token spelling. */
function normalizedToken(value: unknown): string {
  return String(value)
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1_$2")
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/-/g, "_")
    .toLowerCase();
}

/** Convert plan path values into absolute binding configuration paths. */
function configuredPaths(
  root: string,
  values: Array<string | PathInput>,
): string[] {
  return values.map((value, index) =>
    runtimePath(
      root,
      typeof value === "string" ? value : value.path,
      `formidDatabasePaths[${index}]`,
    ),
  );
}

/** Construct the frozen Standard or Targeted request through public factories. */
async function buildRequest(input: ScenarioInput, root: string) {
  const classic = await import("../index.js");
  if (input.game !== "fallout4") {
    throw new RunnerContractError("base scenario game must be fallout4");
  }
  const configuration: JsScanRunConfiguration = {
    installationRoot: root,
    game: classic.JsGameId.Fallout4,
    gameVersion: requireString(input.gameVersion, "gameVersion"),
    showFormidValues: requireBoolean(
      input.showFormidValues,
      "showFormidValues",
    ),
    simplifyLogs: requireBoolean(input.simplifyLogs, "simplifyLogs"),
    formidDatabasePaths: configuredPaths(root, input.formidDatabasePaths),
    maxConcurrent: requireInteger(input.maxConcurrent, "maxConcurrent"),
  };

  if (input.intent === "standard") {
    let unsolvedLogs;
    if (input.unsolvedLogs === "leave-in-place") {
      unsolvedLogs = classic.ScanRunUnsolvedLogs.leaveInPlace();
    } else if (input.unsolvedLogs === "move-to-custom") {
      unsolvedLogs = classic.ScanRunUnsolvedLogs.moveToCustom(
        runtimePath(
          root,
          input.unsolvedLogsPath?.path,
          "unsolvedLogsPath.path",
        ),
      );
    } else {
      throw new RunnerContractError(
        "Standard scenario unsolvedLogs must be leave-in-place or move-to-custom",
      );
    }
    return classic.ScanRunRequest.standard(
      configuration,
      {
        baseDirectory: runtimePath(
          root,
          input.standardSource.baseDirectory.path,
          "baseDirectory.path",
        ),
        configuredDocumentsRoot: runtimePath(
          root,
          input.standardSource.configuredDocumentsRoot.path,
          "configuredDocumentsRoot.path",
        ),
      },
      unsolvedLogs,
    );
  }

  return classic.ScanRunRequest.targeted(configuration, {
    inputs: input.targetedInputs.map((item, index) =>
      runtimePath(root, item.path, `targetedInputs[${index}].path`),
    ),
  });
}

/** Serialize frozen Display Content while preserving every ordered carrier field. */
function displayContent(
  lines: JsScanRunDisplayLine[],
  root: string,
): JsonObject[] {
  return lines.map((line) => ({
    severity: normalizedToken(line.severity),
    segments: line.segments.map((segment) => ({
      kind: normalizedToken(segment.kind),
      text: segment.text,
      path:
        segment.path === ""
          ? ""
          : relativePath(root, segment.path, "display segment path"),
      count: requireInteger(segment.count, "display segment count"),
    })),
  }));
}

/** Serialize unexpected FCX setup data so a non-null regression stays visible. */
function serializeSetup(
  setup: JsScanRunResult["setup"],
  root: string,
): JsonObject | null {
  if (setup === undefined) {
    return null;
  }
  return {
    status: normalizedToken(setup.status),
    message: setup.message ?? null,
    renderedReport: setup.renderedReport,
    checks: setup.checks.map((check) => ({
      kind: normalizedToken(check.kind),
      state: normalizedToken(check.state),
      message: check.message,
      details: [...check.details],
    })),
    pathUpdates: setup.pathUpdates.map((update) => ({
      kind: normalizedToken(update.kind),
      path: pathCarrier(root, update.path, "setup path update"),
    })),
    actions: [...setup.actions],
    fatalErrors: [...setup.fatalErrors],
  };
}

/** Serialize the immutable Installed YAML Data snapshot used by the run. */
function installedYamlData(
  installed: JsInstalledYamlDataRunData | undefined,
  root: string,
): JsonObject | null {
  if (installed === undefined) {
    return null;
  }
  return {
    main: {
      role: normalizedToken(installed.main.role),
      provenance: normalizedToken(installed.main.provenance),
      schemaMajor: requireInteger(
        installed.main.schemaMajor,
        "Main schema major",
      ),
      schemaMinor: requireInteger(
        installed.main.schemaMinor,
        "Main schema minor",
      ),
      identity: {
        sha256: installed.main.sha256,
        byteLength: requireInteger(
          installed.main.byteLength,
          "Main byte length",
        ),
      },
    },
    gameFile: {
      role: normalizedToken(installed.gameFile.role),
      provenance: normalizedToken(installed.gameFile.provenance),
      schemaMajor: requireInteger(
        installed.gameFile.schemaMajor,
        "game schema major",
      ),
      schemaMinor: requireInteger(
        installed.gameFile.schemaMinor,
        "game schema minor",
      ),
      identity: {
        sha256: installed.gameFile.sha256,
        byteLength: requireInteger(
          installed.gameFile.byteLength,
          "game byte length",
        ),
      },
    },
    localIgnoreState: normalizedToken(installed.localIgnoreState),
    localIgnoreIdentity: {
      sha256: installed.localIgnoreIdentity.sha256,
      byteLength: requireInteger(
        installed.localIgnoreIdentity.byteLen,
        "Local Ignore byte length",
      ),
    },
    diagnostics: installed.diagnostics.map((diagnostic) => ({
      role:
        diagnostic.role === undefined ? null : normalizedToken(diagnostic.role),
      candidate:
        diagnostic.candidate === undefined
          ? null
          : normalizedToken(diagnostic.candidate),
      path:
        diagnostic.path === undefined
          ? null
          : pathCarrier(
              root,
              diagnostic.path,
              "Installed YAML Data diagnostic path",
            ),
      kind: normalizedToken(diagnostic.kind),
      message: diagnostic.message,
    })),
    localIgnoreResetAvailable: installed.localIgnoreResetAvailable,
  };
}

/** Project one retained byte identity to the canonical cross-adapter carrier. */
function contentIdentity(identity: {
  sha256: string;
  byteLen: number;
}): FileIdentity {
  return {
    sha256: identity.sha256,
    byteLength: requireInteger(
      identity.byteLen,
      "content identity byte length",
    ),
  };
}

/** Serialize stable Local Ignore snapshot and reset facts while omitting path-bearing prose. */
async function localIgnoreInstalledYamlData(
  installed: JsInstalledYamlDataRunData | undefined,
  root: string,
): Promise<JsonObject | null> {
  if (installed === undefined) {
    return null;
  }
  const reset = installed.localIgnoreReset;
  let projectedReset: JsonObject | null = null;
  if (reset !== undefined) {
    const backupBytes = await readOptionalFile(reset.backupPath);
    projectedReset = {
      localIgnorePath: pathCarrier(
        root,
        reset.localIgnorePath,
        "Local Ignore reset path",
      ),
      backup: {
        parentPath: relativePath(
          root,
          dirname(reset.backupPath),
          "Local Ignore reset backup parent",
        ),
        exists: backupBytes !== null,
        identityMatchesReceipt:
          backupBytes !== null &&
          sameIdentity(
            fileIdentity(backupBytes),
            contentIdentity(reset.backupIdentity),
          ),
      },
      malformedIdentity: contentIdentity(reset.malformedIdentity),
      backupIdentity: contentIdentity(reset.backupIdentity),
      replacementIdentity: contentIdentity(reset.replacementIdentity),
    };
  }

  return {
    mainIdentity: {
      sha256: installed.main.sha256,
      byteLength: requireInteger(installed.main.byteLength, "Main byte length"),
    },
    gameIdentity: {
      sha256: installed.gameFile.sha256,
      byteLength: requireInteger(
        installed.gameFile.byteLength,
        "game byte length",
      ),
    },
    localIgnoreState: normalizedToken(installed.localIgnoreState),
    localIgnoreIdentity: contentIdentity(installed.localIgnoreIdentity),
    diagnostics: installed.diagnostics.map((diagnostic) => ({
      role:
        diagnostic.role === undefined ? null : normalizedToken(diagnostic.role),
      candidate:
        diagnostic.candidate === undefined
          ? null
          : normalizedToken(diagnostic.candidate),
      path:
        diagnostic.path === undefined
          ? null
          : pathCarrier(
              root,
              diagnostic.path,
              "Installed YAML Data diagnostic path",
            ),
      kind: normalizedToken(diagnostic.kind),
    })),
    localIgnoreResetAvailable: installed.localIgnoreResetAvailable,
    localIgnoreReset: projectedReset,
  };
}

/** Serialize ordered discovery paths and Targeted rejection reasons. */
function discovery(
  value: JsScanRunResult["discovery"],
  root: string,
): JsonObject | null {
  if (value === undefined) {
    return null;
  }
  return {
    source: value.source,
    acceptedLogs: value.acceptedLogs.map((path) =>
      pathCarrier(root, path, "accepted Crash Log"),
    ),
    rejectedInputs: value.rejectedInputs.map((rejected) => ({
      path: relativePath(root, rejected.path, "rejected input"),
      reason: rejected.reason,
    })),
    searchedLocations: value.searchedLocations.map((path) =>
      pathCarrier(root, path, "searched location"),
    ),
  };
}

/** Serialize discovery-ordered terminal log outcomes without timing fields. */
function logResults(logs: JsScanRunLogResult[], root: string): JsonObject[] {
  return logs.map((log) => ({
    discoveryIndex: requireInteger(log.discoveryIndex, "log discovery index"),
    crashLog: pathCarrier(root, log.crashLog, "result Crash Log"),
    autoscanReport:
      log.autoscanReport === undefined
        ? null
        : pathCarrier(root, log.autoscanReport, "Autoscan Report"),
    disposition: log.disposition,
    failures: log.failures.map((failure) => ({
      stage: failure.stage,
      message: failure.message,
    })),
    message: log.message ?? null,
    movedToUnsolvedLogs: log.movedToUnsolvedLogs,
  }));
}

/** Partition callbacks into deterministic run-wide and per-log ordered traces. */
function events(callbacks: JsScanRunEvent[], root: string): JsonObject {
  const runEvents: JsonObject[] = [];
  const logStreams = new Map<number, JsonObject & { trace: JsonObject[] }>();
  for (const event of callbacks) {
    const projected: JsonObject = {
      kind: event.kind,
      displayContent: displayContent(event.displayLines, root),
    };
    if (event.log === undefined) {
      if (event.effectiveConcurrency !== undefined) {
        projected.effectiveConcurrency = requireInteger(
          event.effectiveConcurrency,
          "event effective concurrency",
        );
      }
      runEvents.push(projected);
      continue;
    }

    const discoveryIndex = requireInteger(
      event.log.discoveryIndex,
      "event discovery index",
    );
    let stream = logStreams.get(discoveryIndex);
    if (stream === undefined) {
      stream = {
        discoveryIndex,
        crashLog: pathCarrier(root, event.log.crashLog, "event Crash Log"),
        trace: [],
      };
      logStreams.set(discoveryIndex, stream);
    }
    if (event.phase !== undefined) {
      projected.phase = event.phase;
    }
    if (event.disposition !== undefined) {
      projected.disposition = event.disposition;
    }
    stream.trace.push(projected);
  }
  return {
    run: runEvents,
    logs: [...logStreams.entries()]
      .sort(([left], [right]) => left - right)
      .map(([, stream]) => stream),
  };
}

/** Project only stable event tokens while retaining per-log observer ordering. */
function compactEvents(
  result: JsScanRunResult,
  callbacks: JsScanRunEvent[],
): JsonObject {
  const run: string[] = [];
  const traces = new Map<number, string[]>();
  for (const log of result.logs) {
    traces.set(log.discoveryIndex, []);
  }

  for (const event of callbacks) {
    if (event.kind === "discovery_completed") {
      run.push("discovery_completed");
      continue;
    }
    if (event.kind === "effective_concurrency_selected") {
      run.push("effective_concurrency_selected");
      continue;
    }
    if (event.log === undefined) {
      throw new RunnerContractError(
        `compact event ${event.kind} has no Crash Log identity`,
      );
    }
    const trace = traces.get(event.log.discoveryIndex);
    const resultLog = result.logs.find(
      (log) => log.discoveryIndex === event.log?.discoveryIndex,
    );
    if (trace === undefined || resultLog === undefined) {
      throw new RunnerContractError(
        "compact event references an unknown discovery index",
      );
    }
    if (resolve(resultLog.crashLog) !== resolve(event.log.crashLog)) {
      throw new RunnerContractError(
        "compact event references a different Crash Log",
      );
    }
    if (event.kind === "log_phase") {
      trace.push(`log_phase:${event.phase}`);
    } else if (event.kind === "log_finished") {
      trace.push(`log_finished:${event.disposition}`);
    } else {
      trace.push(event.kind);
    }
  }

  return {
    run,
    logs: result.logs.map((log) => ({
      discoveryIndex: log.discoveryIndex,
      trace: traces.get(log.discoveryIndex) ?? [],
    })),
  };
}

/** Return a report's observed file state without converting I/O failures to absence. */
async function reportState(
  path: string,
): Promise<{ exists: boolean; nonEmpty: boolean }> {
  try {
    const metadata = await stat(path);
    return {
      exists: metadata.isFile(),
      nonEmpty: metadata.isFile() && metadata.size > 0,
    };
  } catch (error) {
    if (isMissingPathError(error)) {
      return { exists: false, nonEmpty: false };
    }
    throw error;
  }
}

/** Return whether one path exists while preserving non-absence I/O errors. */
async function pathExists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch (error) {
    if (isMissingPathError(error)) {
      return false;
    }
    throw error;
  }
}

/** Classify one declared durable path without collapsing a directory into file existence. */
async function observedPathKind(path: string): Promise<string> {
  try {
    const metadata = await stat(path);
    if (metadata.isFile()) {
      return "file";
    }
    if (metadata.isDirectory()) {
      return "directory";
    }
    return "other";
  } catch (error) {
    if (isMissingPathError(error)) {
      return "missing";
    }
    throw error;
  }
}

/** Observe the exact ordered path/type inventory declared by a failure scenario. */
async function observedDurableEffects(
  input: ScenarioInput,
  root: string,
): Promise<JsonObject[]> {
  const effects: JsonObject[] = [];
  for (const [index, item] of (input.observedPaths ?? []).entries()) {
    const path = runtimePath(root, item.path, `observedPaths[${index}].path`);
    effects.push({
      path: relativePath(root, path, "observed failure effect"),
      kind: await observedPathKind(path),
    });
  }
  return effects;
}

/** Observe report persistence and the forbidden Unsolved Logs destination. */
async function durableEffects(
  logs: JsScanRunLogResult[],
  root: string,
): Promise<JsonObject> {
  const reports: JsonObject[] = [];
  for (const log of logs) {
    if (log.autoscanReport === undefined) {
      continue;
    }
    const path = resolve(
      isAbsolute(log.autoscanReport)
        ? log.autoscanReport
        : join(root, log.autoscanReport),
    );
    reports.push({
      path: relativePath(root, path, "durable Autoscan Report"),
      ...(await reportState(path)),
    });
  }
  const unsolved = join(root, "Unsolved Logs");
  return {
    reports,
    unsolvedLogs: {
      path: "Unsolved Logs",
      exists: await pathExists(unsolved),
    },
  };
}

/** Observe only lifecycle-relevant durable reports and declared forbidden paths. */
async function lifecycleDurableEffects(
  logs: JsScanRunLogResult[],
  input: ScenarioInput,
  root: string,
): Promise<JsonObject> {
  const base = await durableEffects(logs, root);
  const forbidden: JsonObject[] = [];
  for (const [index, path] of (input.forbiddenEffectPaths ?? []).entries()) {
    const absolute = runtimePath(root, path, `forbiddenEffectPaths[${index}]`);
    forbidden.push({
      path: relativePath(root, absolute, "forbidden lifecycle effect"),
      exists: await pathExists(absolute),
    });
  }
  return {
    reports: base.reports,
    forbidden,
  };
}

/** Hash one durable file's exact bytes using the canonical SHA-256 identity shape. */
function fileIdentity(bytes: Uint8Array): FileIdentity {
  return {
    sha256: createHash("sha256").update(bytes).digest("hex"),
    byteLength: bytes.byteLength,
  };
}

/** Compare two byte identities without relying on JSON key ordering. */
function sameIdentity(left: FileIdentity, right: FileIdentity): boolean {
  return left.sha256 === right.sha256 && left.byteLength === right.byteLength;
}

/** Read an optional file while converting only a genuine NotFound result to absence. */
async function readOptionalFile(path: string): Promise<Buffer | null> {
  try {
    return await readFile(path);
  } catch (error) {
    if (isMissingPathError(error)) {
      return null;
    }
    throw error;
  }
}

/** Project one file's existence and exact identity beneath the isolated root. */
async function exactFileEffect(
  root: string,
  path: string,
): Promise<JsonObject> {
  let metadata;
  try {
    metadata = await stat(path);
  } catch (error) {
    if (isMissingPathError(error)) {
      return {
        path: relativePath(root, path, "durable file effect"),
        exists: false,
        identity: null,
      };
    }
    throw error;
  }
  const bytes = metadata.isFile() ? await readFile(path) : null;
  return {
    path: relativePath(root, path, "durable file effect"),
    exists: true,
    identity: bytes === null ? null : fileIdentity(bytes),
  };
}

/** Enumerate backups, including the intentional regular-file backup blocker as none. */
async function localIgnoreBackupEffects(root: string): Promise<JsonObject[]> {
  const backupRoot = join(root, "CLASSIC Backup");
  try {
    const rootMetadata = await stat(backupRoot);
    if (rootMetadata.isFile()) {
      // A scenario can deliberately block backup creation with a regular file.
      return [];
    }
    if (!rootMetadata.isDirectory()) {
      throw new RunnerContractError(
        "Local Ignore backup root is neither a file nor a directory",
      );
    }
  } catch (error) {
    if (isMissingPathError(error)) {
      return [];
    }
    throw error;
  }

  const directory = join(root, "CLASSIC Backup", "YAML Data", "Local Ignore");
  const entries = await readOptionalDirectory(directory);
  if (entries === null) {
    return [];
  }

  const paths = entries
    .filter((entry) => entry.isFile())
    .map((entry) => join(directory, entry.name))
    .sort();
  const effects: JsonObject[] = [];
  for (const path of paths) {
    const bytes = await readOptionalFile(path);
    if (bytes === null) {
      throw new RunnerContractError(
        "enumerated Local Ignore backup disappeared before observation",
      );
    }
    effects.push({
      parentPath: relativePath(
        root,
        dirname(path),
        "Local Ignore backup parent",
      ),
      identity: fileIdentity(bytes),
    });
  }
  return effects;
}

/** Read one optional directory while preserving every failure other than NotFound. */
async function readOptionalDirectory(
  directory: string,
): Promise<Dirent<string>[] | null> {
  try {
    return await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (isMissingPathError(error)) {
      return null;
    }
    throw error;
  }
}

/** Observe exact Local Ignore, backup, report, and forbidden filesystem effects. */
async function localIgnoreDurableEffects(
  result: JsScanRunResult | null,
  input: ScenarioInput,
  root: string,
): Promise<JsonObject> {
  const reports: JsonObject[] = [];
  for (const log of result?.logs ?? []) {
    if (log.autoscanReport === undefined) {
      continue;
    }
    const path = resolve(
      isAbsolute(log.autoscanReport)
        ? log.autoscanReport
        : join(root, log.autoscanReport),
    );
    const bytes = await readOptionalFile(path);
    reports.push({
      path: relativePath(root, path, "durable Autoscan Report"),
      exists: bytes !== null,
      nonEmpty: bytes !== null && bytes.byteLength > 0,
      identity: bytes === null ? null : fileIdentity(bytes),
    });
  }

  const forbidden: JsonObject[] = [];
  for (const [index, relative] of (
    input.forbiddenEffectPaths ?? []
  ).entries()) {
    forbidden.push(
      await exactFileEffect(
        root,
        runtimePath(root, relative, `forbiddenEffectPaths[${index}]`),
      ),
    );
  }

  return {
    localIgnore: await exactFileEffect(
      root,
      join(root, "CLASSIC Data", "CLASSIC Ignore.yaml"),
    ),
    backups: await localIgnoreBackupEffects(root),
    reports,
    forbidden,
  };
}

/** Reject adapter infrastructure or observer failures and return the public success envelope. */
function requireSuccessfulExecution(
  execution: JsScanRunSuccess | JsScanRunFailure,
  label: string,
): JsScanRunSuccess {
  if (execution.observerError !== undefined) {
    throw new RunnerContractError(
      `${label} observer delivery failed: ${execution.observerError}`,
    );
  }
  if ("error" in execution) {
    const errorPath =
      execution.error.path === undefined ? "" : ` (${execution.error.path})`;
    throw new RunnerContractError(
      `${label} failed during ${execution.error.stage}: ${execution.error.message}${errorPath}`,
    );
  }
  return execution;
}

/** Preserve ordered Display Content severities while omitting separately tested prose. */
function displaySeverities(lines: JsScanRunDisplayLine[]): string[] {
  return lines.map((line) => normalizedToken(line.severity));
}

/** Project the stable decision labels and availability from a public recovery prompt. */
function compactRecoveryPrompt(prompt: JsScanRunRecoveryPrompt): JsonObject {
  return {
    displaySeverities: displaySeverities(prompt.lines),
    decisions: prompt.decisions.map((decision) => ({
      decision: normalizedToken(decision.decision),
      label: decision.label,
      available: decision.available,
    })),
  };
}

/** Project one initial or terminal Local Ignore phase without reading durable effects. */
async function localIgnorePhase(
  execution: JsScanRunSuccess | JsScanRunFailure,
  callbacks: JsScanRunEvent[],
  root: string,
  continuationAvailable: boolean,
  recoveryPrompt: JsScanRunRecoveryPrompt | undefined,
): Promise<JsonObject> {
  const success = requireSuccessfulExecution(execution, "scan-run phase");
  const result = success.result;
  if (result.setup !== undefined) {
    throw new RunnerContractError(
      "Local Ignore scenario unexpectedly returned setup data",
    );
  }
  return {
    run: {
      status: result.status,
      message: result.message ?? null,
      total: requireInteger(result.total, "run total"),
      succeeded: requireInteger(result.succeeded, "run succeeded"),
      failed: requireInteger(result.failed, "run failed"),
      cancelled: requireInteger(result.cancelled, "run cancelled"),
      effectiveConcurrency:
        result.effectiveConcurrency === undefined
          ? null
          : requireInteger(
              result.effectiveConcurrency,
              "effective concurrency",
            ),
    },
    discovery: discovery(result.discovery, root),
    installedYamlData: await localIgnoreInstalledYamlData(
      result.installedYamlData,
      root,
    ),
    logs: logResults(result.logs, root),
    events: compactEvents(result, callbacks),
    continuationAvailable,
    recoveryPrompt:
      recoveryPrompt === undefined
        ? null
        : compactRecoveryPrompt(recoveryPrompt),
  };
}

/** Invoke exactly one public continuation operation without deriving it from scenario names. */
async function runContinuationAction(
  classic: typeof import("../index.js"),
  continuation: ScanRunContinuation,
  action: ContinuationActionInput,
  cancellation: ScanRunCancellation,
  callbacks?: JsScanRunEvent[],
): Promise<JsScanRunSuccess | JsScanRunFailure> {
  const observer =
    callbacks === undefined
      ? undefined
      : (event: JsScanRunEvent) => {
          callbacks.push(event);
        };
  if (action.operation === "abandon") {
    return await classic.scanRunAbandon(continuation, cancellation, observer);
  }
  const decision =
    action.decision === "proceed-without-ignore"
      ? classic.JsScanRunLocalIgnoreRecoveryDecision.ProceedWithoutIgnore
      : classic.JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault;
  return await classic.scanRunResume(
    continuation,
    decision,
    cancellation,
    observer,
  );
}

/** Project one optional reset identity from a rejected public continuation. */
function resumeErrorIdentity(
  value: unknown,
  label: string,
): FileIdentity | null {
  if (value === undefined) {
    return null;
  }
  const identity = requireObject(value, label);
  return {
    sha256: requireString(identity.sha256, `${label}.sha256`),
    byteLength: requireInteger(identity.byteLen, `${label}.byteLen`),
  };
}

/** Normalize one typed reset rejection without retaining OS-dependent prose. */
function terminalResumeError(
  error: unknown,
  callbacks: JsScanRunEvent[],
  root: string,
): JsonObject {
  const value = requireObject(error, "terminal continuation error");
  const kind = requireString(
    value.kind ?? value.code,
    "terminal continuation error kind",
  );
  const code = requireString(
    value.code ?? value.kind,
    "terminal continuation error code",
  );
  if (code !== kind) {
    throw new RunnerContractError(
      "terminal continuation error kind and code must agree",
    );
  }
  const message = requireString(
    value.message,
    "terminal continuation error message",
  );
  const lines = requireArray(
    value.displayLines,
    "terminal continuation error displayLines",
  );
  return {
    kind,
    code,
    messageNonEmpty: message.length > 0,
    path:
      value.path === undefined
        ? null
        : pathCarrier(root, value.path, "terminal continuation error path"),
    stage:
      value.stage === undefined
        ? null
        : normalizedToken(
            requireString(value.stage, "terminal continuation error stage"),
          ),
    expectedIdentity: resumeErrorIdentity(
      value.expectedIdentity,
      "terminal continuation error expectedIdentity",
    ),
    actualIdentity: resumeErrorIdentity(
      value.actualIdentity,
      "terminal continuation error actualIdentity",
    ),
    backupPath:
      value.backupPath === undefined
        ? null
        : pathCarrier(
            root,
            value.backupPath,
            "terminal continuation error backupPath",
          ),
    malformedIdentity: resumeErrorIdentity(
      value.malformedIdentity,
      "terminal continuation error malformedIdentity",
    ),
    backupIdentity: resumeErrorIdentity(
      value.backupIdentity,
      "terminal continuation error backupIdentity",
    ),
    replacementIdentity: resumeErrorIdentity(
      value.replacementIdentity,
      "terminal continuation error replacementIdentity",
    ),
    displaySeverities: lines.map((line, index) =>
      normalizedToken(
        requireObject(
          line,
          `terminal continuation error displayLines[${index}]`,
        ).severity,
      ),
    ),
    events: callbacks.map((event) => normalizedToken(event.kind)),
  };
}

/** Yield briefly while polling the public reset lock used as the critical-section seam. */
async function waitForResetCriticalSection(root: string): Promise<boolean> {
  const lockPath = join(root, ".classic-local-ignore-reset.lock");
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    if (await pathExists(lockPath)) {
      return true;
    }
    await new Promise<void>((resolveDelay) => setTimeout(resolveDelay, 1));
  }
  return await pathExists(lockPath);
}

/** Project a rejected one-shot replay through its stable typed error and severity contract. */
function replayError(
  action: ContinuationActionInput,
  error: unknown,
): JsonObject {
  const value = requireObject(error, "continuation replay error");
  const kind = requireString(
    value.kind ?? value.code,
    "continuation replay error kind",
  );
  const lines = requireArray(
    value.displayLines,
    "continuation replay error displayLines",
  );
  const severities = lines.map((line, index) =>
    normalizedToken(
      requireObject(line, `continuation replay displayLines[${index}]`)
        .severity,
    ),
  );
  return {
    operation: action.operation,
    decision:
      action.operation === "resume" ? normalizedToken(action.decision) : null,
    error: {
      kind,
      message:
        error instanceof Error
          ? error.message
          : requireString(value.message, "continuation replay error message"),
      displaySeverities: severities,
    },
  };
}

/** Claim one paused continuation, apply post-pause mutations, and prove replay is one-shot. */
async function continuationObservation(
  plan: RunPlan,
  scenario: RunPlanScenario,
  input: ScenarioInput,
  root: string,
  classic: typeof import("../index.js"),
  cancellation: ScanRunCancellation,
  initialExecution: JsScanRunSuccess | JsScanRunFailure,
  initialCallbacks: JsScanRunEvent[],
  flow: ContinuationFlowInput,
): Promise<JsonObject> {
  const initialSuccess = requireSuccessfulExecution(
    initialExecution,
    "initial scan run",
  );
  const continuation = initialSuccess.result.continuation;
  if (continuation === undefined) {
    throw new RunnerContractError(
      "continuationFlow initial result has no continuation",
    );
  }
  if (initialSuccess.recoveryPrompt === undefined) {
    throw new RunnerContractError(
      "continuationFlow initial result has no recovery prompt",
    );
  }
  const initial = await localIgnorePhase(
    initialSuccess,
    initialCallbacks,
    root,
    true,
    initialSuccess.recoveryPrompt,
  );
  await materializePostPauseData(plan, scenario, flow.postPauseData, root);

  if (
    flow.cancellation !== undefined &&
    flow.cancellation !== "before-resume" &&
    flow.cancellation !== "after-reset-critical-section"
  ) {
    throw new RunnerContractError(
      "continuationFlow.cancellation is not a supported cancellation seam",
    );
  }
  if (flow.cancellation === "before-resume") {
    cancellation.cancel();
  }
  const cancelledBeforeTerminal = cancellation.isCancelled;
  const terminalCallbacks: JsScanRunEvent[] = [];
  let terminalExecution: JsScanRunSuccess | JsScanRunFailure | null = null;
  let terminalError: JsonObject | null = null;
  if (flow.cancellation === "after-reset-critical-section") {
    if (
      flow.action.operation !== "resume" ||
      flow.action.decision !== "reset-to-default"
    ) {
      throw new RunnerContractError(
        "after-reset-critical-section cancellation requires Reset To Default",
      );
    }
    const pending = runContinuationAction(
      classic,
      continuation,
      flow.action,
      cancellation,
      terminalCallbacks,
    ).then(
      (execution) => ({ ok: true as const, execution }),
      (error: unknown) => ({ ok: false as const, error }),
    );
    if (!(await waitForResetCriticalSection(root))) {
      cancellation.cancel();
      await pending;
      throw new RunnerContractError(
        "reset critical section was not observed before the five-second deadline",
      );
    }
    cancellation.cancel();
    const outcome = await pending;
    if (outcome.ok) {
      terminalExecution = outcome.execution;
    } else {
      terminalError = terminalResumeError(
        outcome.error,
        terminalCallbacks,
        root,
      );
    }
  } else {
    try {
      terminalExecution = await runContinuationAction(
        classic,
        continuation,
        flow.action,
        cancellation,
        terminalCallbacks,
      );
    } catch (error) {
      terminalError = terminalResumeError(error, terminalCallbacks, root);
    }
  }

  let terminalSuccess: JsScanRunSuccess | null = null;
  let terminal: JsonObject | null = null;
  if (terminalExecution !== null) {
    terminalSuccess = requireSuccessfulExecution(
      terminalExecution,
      "terminal continuation action",
    );
    terminal = await localIgnorePhase(
      terminalSuccess,
      terminalCallbacks,
      root,
      false,
      undefined,
    );
  }
  const cancelledAfterTerminal = cancellation.isCancelled;

  const replays: JsonObject[] = [];
  for (const action of flow.replays) {
    try {
      await runContinuationAction(classic, continuation, action, cancellation);
      throw new RunnerContractError(
        "a replayed continuation action unexpectedly succeeded",
      );
    } catch (error) {
      if (error instanceof RunnerContractError) {
        throw error;
      }
      replays.push(replayError(action, error));
    }
  }

  return {
    initial,
    terminal,
    terminalError,
    replays,
    cancellation: {
      beforeTerminal: cancelledBeforeTerminal,
      afterTerminal: cancelledAfterTerminal,
      afterReplays: cancellation.isCancelled,
    },
    durableEffects: await localIgnoreDurableEffects(
      terminalSuccess?.result ?? null,
      input,
      root,
    ),
  };
}

/** Project one public execution envelope to the frozen normalized observation. */
async function observation(
  execution: Awaited<
    ReturnType<(typeof import("../index.js"))["scanRunExecute"]>
  >,
  callbacks: JsScanRunEvent[],
  root: string,
): Promise<JsonObject> {
  if (execution.observerError !== undefined) {
    throw new RunnerContractError(
      `observer delivery failed: ${execution.observerError}`,
    );
  }
  if ("error" in execution) {
    const errorPath =
      execution.error.path === undefined ? "" : ` (${execution.error.path})`;
    throw new RunnerContractError(
      `scan failed during ${execution.error.stage}: ${execution.error.message}${errorPath}`,
    );
  }
  const result = execution.result;
  return {
    run: {
      status: result.status,
      message: result.message ?? null,
      total: requireInteger(result.total, "run total"),
      succeeded: requireInteger(result.succeeded, "run succeeded"),
      failed: requireInteger(result.failed, "run failed"),
      cancelled: requireInteger(result.cancelled, "run cancelled"),
      setup: serializeSetup(result.setup, root),
      effectiveConcurrency:
        result.effectiveConcurrency === undefined
          ? null
          : requireInteger(
              result.effectiveConcurrency,
              "effective concurrency",
            ),
    },
    discovery: discovery(result.discovery, root),
    installedYamlData: installedYamlData(result.installedYamlData, root),
    logs: logResults(result.logs, root),
    events: events(callbacks, root),
    displayContent: displayContent(execution.displayLines, root),
    durableEffects: await durableEffects(result.logs, root),
  };
}

/** Project public typed failures as completed semantic evidence with declared artifacts. */
async function failureObservation(
  execution: Awaited<
    ReturnType<(typeof import("../index.js"))["scanRunExecute"]>
  >,
  input: ScenarioInput,
  root: string,
): Promise<JsonObject> {
  const effects = await observedDurableEffects(input, root);
  if ("error" in execution) {
    return {
      infrastructureError: {
        stage: execution.error.stage,
        messageNonEmpty: execution.error.message.length > 0,
        path:
          execution.error.path === undefined
            ? null
            : pathCarrier(
                root,
                execution.error.path,
                "infrastructure failure path",
              ),
      },
      durableEffects: effects,
    };
  }
  if (execution.observerError !== undefined) {
    throw new RunnerContractError(
      `failure scenario observer delivery failed: ${execution.observerError}`,
    );
  }
  return {
    status: execution.result.status,
    logs: execution.result.logs.map((log) => ({
      discoveryIndex: requireInteger(
        log.discoveryIndex,
        "failure log discovery index",
      ),
      crashLog: pathCarrier(root, log.crashLog, "failure Crash Log"),
      autoscanReport:
        log.autoscanReport === undefined
          ? null
          : pathCarrier(root, log.autoscanReport, "failure Autoscan Report"),
      disposition: log.disposition,
      failures: log.failures.map((failure) => ({
        stage: failure.stage,
        messageNonEmpty: failure.message.length > 0,
      })),
      messageNonEmpty: (log.message?.length ?? 0) > 0,
      movedToUnsolvedLogs: log.movedToUnsolvedLogs,
    })),
    durableEffects: effects,
  };
}

/** Project cancellation boundaries and observer delivery failure without diagnostics. */
async function lifecycleObservation(
  execution: Awaited<
    ReturnType<(typeof import("../index.js"))["scanRunExecute"]>
  >,
  callbacks: JsScanRunEvent[],
  input: ScenarioInput,
  cancellation: ScanRunCancellation,
  root: string,
): Promise<JsonObject> {
  if ("error" in execution) {
    const errorPath =
      execution.error.path === undefined ? "" : ` (${execution.error.path})`;
    throw new RunnerContractError(
      `scan failed during ${execution.error.stage}: ${execution.error.message}${errorPath}`,
    );
  }
  const expectedFailure = input.executionFlow?.observerFailure ?? null;
  if (expectedFailure === null && execution.observerError !== undefined) {
    throw new RunnerContractError(
      `unexpected observer delivery failure: ${execution.observerError}`,
    );
  }
  if (expectedFailure !== null && execution.observerError === undefined) {
    throw new RunnerContractError(
      "expected observer delivery failure was not reported",
    );
  }
  const result = execution.result;
  return {
    run: {
      status: result.status,
      message: result.message ?? null,
      total: requireInteger(result.total, "run total"),
      succeeded: requireInteger(result.succeeded, "run succeeded"),
      failed: requireInteger(result.failed, "run failed"),
      cancelled: requireInteger(result.cancelled, "run cancelled"),
      effectiveConcurrency:
        result.effectiveConcurrency === undefined
          ? null
          : requireInteger(
              result.effectiveConcurrency,
              "effective concurrency",
            ),
    },
    discovery: discovery(result.discovery, root),
    logs: logResults(result.logs, root),
    events: compactEvents(result, callbacks),
    observerFailure:
      expectedFailure === null
        ? null
        : {
            kind: "observer_delivery_failure",
            eventKind: expectedFailure.eventKind,
            messageNonEmpty: execution.observerError!.length > 0,
          },
    cancellation: { requested: cancellation.isCancelled },
    durableEffects: await lifecycleDurableEffects(result.logs, input, root),
  };
}

/** Execute one scenario through the installed public Node binding operation. */
async function executeScenario(
  plan: RunPlan,
  scenario: RunPlanScenario,
): Promise<JsonObject> {
  const root = resolve(
    await mkdtemp(join(tmpdir(), "classic-node-conformance-")),
  );
  const previousDirectory = process.cwd();
  try {
    const input = await materializeScenarioInputs(plan, scenario, root);
    await appendLocalIgnorePadding(input, root);
    const cacheRoot = join(root, "isolated-cache");
    await mkdir(cacheRoot, { recursive: true });
    // Cache selection is process-global, so scenarios run serially with a fresh empty root.
    process.env.LOCALAPPDATA = cacheRoot;
    process.env.XDG_CACHE_HOME = cacheRoot;
    process.chdir(root);

    const classic = await import("../index.js");
    const request = await buildRequest(input, root);
    const callbacks: JsScanRunEvent[] = [];
    const cancellation = new classic.ScanRunCancellation();
    const flow = input.executionFlow;
    if (input.observationProfile === "lifecycle" && flow === undefined) {
      throw new RunnerContractError(
        "the lifecycle observation profile requires executionFlow",
      );
    }
    if (input.observationProfile !== "lifecycle" && flow !== undefined) {
      throw new RunnerContractError(
        "executionFlow requires the lifecycle observation profile",
      );
    }
    if (flow?.cancellation === "on-observer-failure") {
      if (flow.observerFailure === undefined || flow.observerFailure === null) {
        throw new RunnerContractError(
          "on-observer-failure cancellation requires observerFailure",
        );
      }
      if (
        flow.observerFailure.eventKind !== "discovery_completed" ||
        flow.observerFailure.message.trim().length === 0
      ) {
        throw new RunnerContractError(
          "observerFailure requires discovery_completed and a non-empty message",
        );
      }
    } else if (
      flow?.observerFailure !== undefined &&
      flow.observerFailure !== null
    ) {
      throw new RunnerContractError(
        "observerFailure requires on-observer-failure cancellation",
      );
    }
    if (flow?.cancellation === "before-discovery") {
      cancellation.cancel();
    }
    const execution = await classic.scanRunExecute(
      request,
      cancellation,
      (event) => {
        callbacks.push(event);
        if (
          flow?.observerFailure !== null &&
          flow?.observerFailure !== undefined &&
          event.kind === flow.observerFailure.eventKind
        ) {
          // Throwing here exercises the binding's real delivery-failure envelope.
          throw new Error(flow.observerFailure.message);
        }
        if (
          flow?.cancellation === "on-first-log-queued" &&
          event.kind === "log_queued"
        ) {
          cancellation.cancel();
        }
        if (
          flow?.cancellation === "on-first-log-started" &&
          event.kind === "log_started" &&
          event.log.discoveryIndex === 0
        ) {
          cancellation.cancel();
        }
      },
      flow?.cancellation === "on-observer-failure",
    );
    if (input.observationProfile === "failure") {
      return await failureObservation(execution, input, root);
    }
    if (input.continuationFlow !== undefined) {
      if (input.observationProfile !== "local-ignore") {
        throw new RunnerContractError(
          "continuationFlow requires the local-ignore observation profile",
        );
      }
      return await continuationObservation(
        plan,
        scenario,
        input,
        root,
        classic,
        cancellation,
        execution,
        callbacks,
        input.continuationFlow,
      );
    }
    if (input.observationProfile === "local-ignore") {
      const success = requireSuccessfulExecution(execution, "scan run");
      return {
        ...(await localIgnorePhase(
          success,
          callbacks,
          root,
          success.result.continuation !== undefined,
          success.recoveryPrompt,
        )),
        durableEffects: await localIgnoreDurableEffects(
          success.result,
          input,
          root,
        ),
      };
    }
    if (input.observationProfile === "lifecycle") {
      return await lifecycleObservation(
        execution,
        callbacks,
        input,
        cancellation,
        root,
      );
    }
    return await observation(execution, callbacks, root);
  } finally {
    process.chdir(previousDirectory);
    await rm(root, { recursive: true, force: true });
  }
}

/** Execute one scenario and retain adapter failures as receipt evidence. */
async function scenarioReceipt(
  plan: RunPlan,
  scenario: RunPlanScenario,
): Promise<ScenarioReceipt> {
  try {
    return {
      id: requireString(scenario.id, "scenario id"),
      executionStatus: "completed",
      capabilityIds: scenario.capabilityIds.map((id, index) =>
        requireString(id, `scenario capabilityIds[${index}]`),
      ),
      observation: await executeScenario(plan, scenario),
      failure: null,
    };
  } catch (error) {
    return {
      id: requireString(scenario.id, "scenario id"),
      executionStatus: "failed",
      capabilityIds: scenario.capabilityIds.map((id, index) =>
        requireString(id, `scenario capabilityIds[${index}]`),
      ),
      observation: {},
      failure: {
        kind: "node-runner-error",
        message: errorMessage(error),
      },
    };
  }
}

/** Build one current receipt while copying every centrally owned identity. */
async function buildReceipt(plan: RunPlan): Promise<JsonObject> {
  const scenarios: ScenarioReceipt[] = [];
  for (const scenario of plan.scenarios) {
    // Serial execution is required because cache isolation uses process environment.
    scenarios.push(await scenarioReceipt(plan, scenario));
  }
  return {
    schemaVersion: plan.schemaVersion,
    familyId: plan.familyId,
    familyVersion: plan.familyVersion,
    expectationDigest: plan.expectationDigest,
    invocation: { ...plan.invocation },
    participant: { ...plan.participant },
    runner: {
      id: "classic-node-conformance",
      version: 1,
      platform: "windows",
      toolchain: "bun",
    },
    scenarios,
  };
}

/** Recursively sort object keys for deterministic compact JSON bytes. */
function canonicalJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalJsonValue);
  }
  if (!isObject(value)) {
    return value;
  }
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, canonicalJsonValue(value[key])]),
  );
}

/** Atomically publish one fresh JSON receipt without exposing partial bytes. */
async function publishReceipt(
  path: string,
  receipt: JsonObject,
): Promise<void> {
  if (await pathExists(path)) {
    throw new RunnerContractError(
      "conformance receipt destination already exists",
    );
  }
  await mkdir(dirname(path), { recursive: true });
  const temporary = join(
    dirname(path),
    `.${path.split(sep).at(-1)}.${randomUUID()}.tmp`,
  );
  const payload = JSON.stringify(canonicalJsonValue(receipt));
  let handle: Awaited<ReturnType<typeof open>> | undefined;
  try {
    handle = await open(temporary, "wx");
    await handle.writeFile(payload, "utf8");
    await handle.sync();
    await handle.close();
    handle = undefined;
    await rename(temporary, path);
  } catch (error) {
    if (handle !== undefined) {
      await handle.close().catch(() => {
        // Preserve the publication failure that caused cleanup to run.
      });
    }
    await rm(temporary, { force: true }).catch(() => {
      // A failed best-effort cleanup must not replace the publication failure.
    });
    throw new RunnerContractError(
      `cannot publish conformance receipt: ${errorMessage(error)}`,
    );
  }
}

/** Return whether an I/O error means the inspected path is absent. */
function isMissingPathError(error: unknown): boolean {
  return isObject(error) && error.code === "ENOENT";
}

/** Convert any caught value to non-empty receipt-safe diagnostic text. */
function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  const message = String(error);
  return message.length === 0 ? "unknown runner failure" : message;
}

/** Read the environment-only invocation, execute its plan, and emit a receipt. */
async function main(): Promise<number> {
  try {
    const runPlanPath = resolve(requireInvocationEnvironment(RUN_PLAN_ENV));
    const outputPath = resolve(requireInvocationEnvironment(OUTPUT_ENV));
    if (dirname(runPlanPath) !== dirname(outputPath)) {
      throw new RunnerContractError(
        "conformance receipt must be a sibling of its immutable run plan",
      );
    }
    const plan = await loadRunPlan(runPlanPath);
    await publishReceipt(outputPath, await buildReceipt(plan));
    return 0;
  } catch (error) {
    console.error(`classic-node-conformance: ${errorMessage(error)}`);
    return 2;
  }
}

void main().then((exitCode) => {
  process.exitCode = exitCode;
});
