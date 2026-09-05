import { createHash, randomUUID } from "node:crypto";
import { copyFile, lstat, mkdir, mkdtemp, open, readdir, readFile, rename, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import type { JsUserSettingsSnapshot, JsWindowGeometry } from "../index.js";

type JsonObject = Record<string, unknown>;

/** One centrally supplied input-only scenario; fixture bytes are the only external inputs read. */
interface Scenario {
  id: string;
  action: string;
  capabilityIds: string[];
  fixtureRefs: string[];
  input: {
    installationData: { fixtureRef: string; path: string }[];
    observationFields: string[];
  };
}

/** Private invocation envelope shared with the central conformance harness. */
interface RunPlan {
  schemaVersion: number;
  familyId: string;
  familyVersion: number;
  expectationDigest: string;
  fixtures: Record<string, string>;
  participant: JsonObject;
  invocation: JsonObject;
  scenarios: Scenario[];
}

/** Exact pre-operation evidence includes empty directories as well as file bytes. */
interface TreeSnapshot {
  directories: string[];
  files: Map<string, Buffer>;
}

/** Return an object while rejecting malformed plan structure. */
function object(value: unknown, label: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as JsonObject;
}

/** Return a non-empty string without coercing malformed plan fields. */
function string(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

/** Validate a string array before using any centrally owned identity or field selector. */
function strings(value: unknown, label: string): string[] {
  if (!Array.isArray(value)) throw new Error(`${label} must be an array`);
  return value.map((item, index) => string(item, `${label}[${index}]`));
}

/** Load an input-only plan without opening the expectation corpus or another participant's receipt. */
async function loadPlan(path: string): Promise<RunPlan> {
  const plan = object(JSON.parse(await readFile(path, "utf8")), "run plan");
  if (plan.schemaVersion !== 1 || plan.familyId !== "user-settings") {
    throw new Error("run plan must be User Settings schema version 1");
  }
  if (!Number.isSafeInteger(plan.familyVersion) || Number(plan.familyVersion) < 1) {
    throw new Error("run plan familyVersion must be a positive integer");
  }
  string(plan.expectationDigest, "expectationDigest");
  object(plan.fixtures, "fixtures");
  const participant = object(plan.participant, "participant");
  if (participant.id !== "node" || participant.role !== "semantic-adapter" || participant.executionInstanceId !== "node") {
    throw new Error("run plan is not the Node semantic-adapter invocation");
  }
  const invocation = object(plan.invocation, "invocation");
  for (const key of ["id", "sourceIdentity", "runPlanDigest"]) string(invocation[key], `invocation.${key}`);
  if (!Array.isArray(plan.scenarios) || plan.scenarios.length === 0) {
    throw new Error("run plan must contain scenarios");
  }
  for (const value of plan.scenarios) {
    const scenario = object(value, "scenario");
    if ("expected" in scenario) throw new Error("input-only run plan must not contain expectations");
    string(scenario.id, "scenario.id");
    if (scenario.action !== "user-settings.open") throw new Error("unsupported User Settings action");
    strings(scenario.capabilityIds, "scenario.capabilityIds");
    strings(scenario.fixtureRefs, "scenario.fixtureRefs");
    const input = object(scenario.input, "scenario.input");
    strings(input.observationFields, "observationFields");
    if (!Array.isArray(input.installationData)) throw new Error("installationData must be an array");
    for (const value of input.installationData) {
      const item = object(value, "installationData item");
      string(item.fixtureRef, "installationData.fixtureRef");
      string(item.path, "installationData.path");
    }
  }
  return plan as unknown as RunPlan;
}

/** Resolve a canonical relative path while keeping all fixture writes beneath the fresh root. */
function runtimePath(root: string, path: string): string {
  const parts = path.split("/");
  if (isAbsolute(path) || path.includes("\\") || path.includes(":") || parts.some((part) => ["", ".", ".."].includes(part))) {
    throw new Error("fixture path must stay beneath the runtime root");
  }
  return resolve(root, ...parts);
}

/** Normalize an observed source path while rejecting output outside the isolated installation. */
function relativePath(root: string, path: string): string {
  const projected = relative(root, resolve(path));
  if (projected === "" || projected === ".." || projected.startsWith(`..${sep}`) || isAbsolute(projected)) {
    throw new Error("observed source path is outside the runtime root");
  }
  return projected.split(sep).join("/");
}

/** Capture the entire runtime tree so even unexpected empty-directory creation remains observable. */
async function snapshotTree(root: string): Promise<TreeSnapshot> {
  const snapshot: TreeSnapshot = { directories: [], files: new Map() };
  /** Visit only regular files and directories, refusing links rather than following external state. */
  async function visit(directory: string): Promise<void> {
    for (const item of (await readdir(directory, { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name))) {
      const path = join(directory, item.name);
      const key = relativePath(root, path);
      if (item.isDirectory()) {
        snapshot.directories.push(key);
        await visit(path);
      } else if (item.isFile()) {
        snapshot.files.set(key, await readFile(path));
      } else {
        throw new Error(`unsupported runtime tree entry: ${key}`);
      }
    }
  }
  await visit(root);
  return snapshot;
}

/** Compare exact tree contents without depending on filesystem timestamp resolution. */
function treeUnchanged(before: TreeSnapshot, after: TreeSnapshot): boolean {
  return JSON.stringify(before.directories) === JSON.stringify(after.directories)
    && before.files.size === after.files.size
    && [...before.files].every(([path, bytes]) => after.files.get(path)?.equals(bytes) === true);
}

/** Convert public camel-case classification and policy tokens to the family vocabulary. */
function token(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}

/** Project only semantic geometry values; provenance is outside this family's observations. */
function geometry(value: JsWindowGeometry): JsonObject {
  return { maximized: value.maximized, width: value.width, height: value.height };
}

/** Select requested public snapshot fields without deriving values from fixture text. */
function projectView(snapshot: JsUserSettingsSnapshot, fields: string[]): JsonObject {
  const scan = snapshot.crashLogScanSettings;
  const windows = snapshot.frontendState.windowGeometry;
  const values: JsonObject = {
    update_check: snapshot.updatePreferences.updateCheck,
    game_version: scan.gameVersionSelection,
    move_unsolved_logs: scan.moveUnsolvedLogs,
    max_concurrent_scans: scan.maxConcurrentScans,
    formid_databases: scan.formidDatabases,
    fcx_mode: scan.fcxMode,
    simplify_logs: scan.simplifyLogs,
    show_formid_values: scan.formidValueLookup,
    custom_scan_folder: scan.customScanInput ?? null,
    mods_folder: snapshot.gameSetupSettings.modsRoot ?? null,
    main_tab_width: windows.mainTab.width,
    main_tab_maximized: windows.mainTab.maximized,
    main_tab: geometry(windows.mainTab),
    backups_tab: geometry(windows.backupsTab),
    articles_tab: geometry(windows.articlesTab),
    results_tab: geometry(windows.resultsTab),
  };
  return Object.fromEntries(fields.map((field) => {
    if (!Object.hasOwn(values, field)) throw new Error(`unsupported observation field: ${field}`);
    return [field, values[field]];
  }));
}

/** Materialize declared inputs, call only the public read-only open API, and measure durable effects. */
async function executeScenario(plan: RunPlan, scenario: Scenario): Promise<JsonObject> {
  const root = resolve(await mkdtemp(join(tmpdir(), "classic-node-user-settings-")));
  try {
    for (const item of scenario.input.installationData) {
      if (!scenario.fixtureRefs.includes(item.fixtureRef)) throw new Error("fixtureRef is not declared by the scenario");
      const source = string(plan.fixtures[item.fixtureRef], `fixture ${item.fixtureRef}`);
      const destination = runtimePath(root, item.path);
      await mkdir(dirname(destination), { recursive: true });
      await copyFile(source, destination);
    }
    const before = await snapshotTree(root);
    const classic = await import("../index.js");
    const snapshot = classic.openUserSettings(root);
    const after = await snapshotTree(root);
    const sourcePath = snapshot.sourcePath === undefined ? null : relativePath(root, snapshot.sourcePath);
    // Compare against pre-open bytes so a mutating implementation cannot validate its own rewrite.
    const sourceBytes = sourcePath === null ? undefined : before.files.get(sourcePath);
    const original = snapshot.originalContent;
    return {
      source: {
        location: token(snapshot.sourceLocation),
        path: sourcePath === null ? null : { path: sourcePath },
        classification: token(snapshot.classification),
      },
      commitEligibility: token(snapshot.commitEligibility),
      diagnostics: snapshot.diagnostics.map((diagnostic) => diagnostic.code),
      view: projectView(snapshot, scenario.input.observationFields),
      durableEffects: { treeUnchanged: treeUnchanged(before, after) },
      revision: {
        kind: snapshot.revision.startsWith("sha256:") ? "sha256" : snapshot.revision,
        matchesSourceBytes: sourceBytes === undefined
          ? sourcePath === null && snapshot.revision === "missing"
          : snapshot.revision === `sha256:${createHash("sha256").update(sourceBytes).digest("hex")}`,
      },
      originalContent: {
        present: original !== undefined,
        matchesSourceBytes: sourceBytes === undefined
          ? sourcePath === null && original === undefined
          : original?.equals(sourceBytes) === true,
      },
    };
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

/** Convert a caught error to receipt-safe text. */
function errorMessage(error: unknown): string {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

/** Preserve central identities while recording adapter failures as explicit scenario evidence. */
async function buildReceipt(plan: RunPlan): Promise<JsonObject> {
  const scenarios: JsonObject[] = [];
  for (const scenario of plan.scenarios) {
    const identity = { id: scenario.id, capabilityIds: scenario.capabilityIds };
    try {
      scenarios.push({ ...identity, executionStatus: "completed", observation: await executeScenario(plan, scenario), failure: null });
    } catch (error) {
      scenarios.push({ ...identity, executionStatus: "failed", observation: {}, failure: { kind: "node-runner-error", message: errorMessage(error) } });
    }
  }
  return {
    schemaVersion: plan.schemaVersion,
    familyId: plan.familyId,
    familyVersion: plan.familyVersion,
    expectationDigest: plan.expectationDigest,
    invocation: { ...plan.invocation },
    participant: { ...plan.participant },
    runner: { id: "classic-node-user-settings-conformance", version: 1, platform: "windows", toolchain: "bun" },
    scenarios,
  };
}

/** Recursively sort object keys for deterministic receipt serialization. */
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (typeof value !== "object" || value === null) return value;
  const record = value as JsonObject;
  return Object.fromEntries(Object.keys(record).sort().map((key) => [key, canonical(record[key])]));
}

/** Atomically publish a fresh sibling receipt after all scenario observations have completed. */
async function publishReceipt(path: string, receipt: JsonObject): Promise<void> {
  try {
    await lstat(path);
    throw new Error("conformance receipt destination already exists");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  await mkdir(dirname(path), { recursive: true });
  const temporary = join(dirname(path), `.user-settings-${randomUUID()}.tmp`);
  try {
    const handle = await open(temporary, "wx");
    try {
      await handle.writeFile(JSON.stringify(canonical(receipt)), "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    await rename(temporary, path);
  } finally {
    await rm(temporary, { force: true });
  }
}

/** Consume the environment-only invocation and report infrastructure failures through the exit status. */
async function main(): Promise<void> {
  try {
    const planPath = resolve(string(process.env.CLASSIC_CONFORMANCE_RUN_PLAN, "CLASSIC_CONFORMANCE_RUN_PLAN"));
    const outputPath = resolve(string(process.env.CLASSIC_CONFORMANCE_OUTPUT, "CLASSIC_CONFORMANCE_OUTPUT"));
    if (dirname(planPath) !== dirname(outputPath)) throw new Error("conformance receipt must be a sibling of its immutable run plan");
    await publishReceipt(outputPath, await buildReceipt(await loadPlan(planPath)));
  } catch (error) {
    console.error(`classic-node-user-settings-conformance: ${errorMessage(error)}`);
    process.exitCode = 2;
  }
}

void main();
