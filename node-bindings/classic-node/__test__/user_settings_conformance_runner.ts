import { createHash, randomUUID } from "node:crypto";
import { copyFile, lstat, mkdir, mkdtemp, open, readdir, readFile, rename, rm, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import type { JsUserSettingsMigrationEndpoint, JsUserSettingsMigrationPlan, JsUserSettingsMigrationPlanningResult, JsUserSettingsMigrationReceipt, JsUserSettingsSnapshot, JsUserSettingsUpdate, JsWindowGeometry } from "../index.js";

type JsonObject = Record<string, unknown>;

/** Caller-controlled disturbance between public migration phases. */
type MigrationIntervention =
  | { kind: "external-edit"; fixtureRef: string; path: string }
  | { kind: "block-backup-directory" }
  | { kind: "tamper-backup"; fixtureRef: string }
  | { kind: "remove-backup" };

/** One centrally supplied input-only scenario; fixture bytes are the only external inputs read. */
interface Scenario {
  id: string;
  action: string;
  capabilityIds: string[];
  fixtureRefs: string[];
  input: {
    installationData: { fixtureRef: string; path: string }[];
    observationFields?: string[];
    requestedUpdate?: JsonObject;
    previewMode?: "update" | "bootstrap";
    installationRootExists?: boolean;
    commit?: boolean;
    externalEdit?: { fixtureRef: string; path: string } | null;
    apply?: boolean;
    restore?: boolean;
    beforeApply?: MigrationIntervention | null;
    beforeRestore?: MigrationIntervention | null;
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
    if (!["user-settings.open", "user-settings.update", "user-settings.migrate"].includes(String(scenario.action))) {
      throw new Error("unsupported User Settings action");
    }
    strings(scenario.capabilityIds, "scenario.capabilityIds");
    strings(scenario.fixtureRefs, "scenario.fixtureRefs");
    const input = object(scenario.input, "scenario.input");
    if (scenario.action === "user-settings.open") {
      strings(input.observationFields, "observationFields");
    } else if (scenario.action === "user-settings.update") {
      object(input.requestedUpdate, "requestedUpdate");
      if (input.previewMode !== "update" && input.previewMode !== "bootstrap") throw new Error("previewMode must be update or bootstrap");
      if (typeof input.installationRootExists !== "boolean") throw new Error("installationRootExists must be a boolean");
      if (typeof input.commit !== "boolean") throw new Error("commit must be a boolean");
      if (input.externalEdit !== null) {
        const edit = object(input.externalEdit, "externalEdit");
        string(edit.fixtureRef, "externalEdit.fixtureRef");
        string(edit.path, "externalEdit.path");
      }
    } else {
      if (typeof input.apply !== "boolean" || typeof input.restore !== "boolean") {
        throw new Error("migration apply and restore must be booleans");
      }
      for (const [phase, kinds] of [
        ["beforeApply", ["external-edit", "block-backup-directory"]],
        ["beforeRestore", ["external-edit", "tamper-backup", "remove-backup"]],
      ] as const) {
        if (input[phase] === null) continue;
        const intervention = object(input[phase], phase);
        if (!(kinds as readonly string[]).includes(string(intervention.kind, `${phase}.kind`))) {
          throw new Error(`unsupported ${phase} intervention`);
        }
        if (["external-edit", "tamper-backup"].includes(String(intervention.kind))) {
          string(intervention.fixtureRef, `${phase}.fixtureRef`);
        }
        if (intervention.kind === "external-edit") string(intervention.path, `${phase}.path`);
      }
    }
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

/** Dispatch explicit operations or observe the public read-only open API and its durable effects. */
async function executeScenario(plan: RunPlan, scenario: Scenario): Promise<JsonObject> {
  if (scenario.action === "user-settings.migrate") return executeMigration(plan, scenario);
  if (scenario.action !== "user-settings.open") return executeOperation(plan, scenario);
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
      view: projectView(snapshot, strings(scenario.input.observationFields, "observationFields")),
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

/** Translate centrally selected fields into public binding arguments without owning validation. */
function requestedUpdate(fields: JsonObject): JsUserSettingsUpdate {
  const update: JsUserSettingsUpdate = {};
  for (const [path, value] of Object.entries(fields)) {
    switch (path) {
      case "/CLASSIC_Settings/Update Check":
        if (typeof value !== "boolean") throw new Error("Update Check input must be a boolean");
        update.updateCheck = value;
        break;
      case "/CLASSIC_Settings/Max Concurrent Scans":
        if (typeof value !== "number" || !Number.isSafeInteger(value)) throw new Error("Max Concurrent Scans input must be an integer");
        update.maxConcurrentScans = value;
        break;
      default:
        throw new Error(`unsupported requested field: ${path}`);
    }
  }
  return update;
}

/** Copy one declared input, including a caller-controlled edit between preview and commit. */
async function installFixture(plan: RunPlan, scenario: Scenario, root: string, item: { fixtureRef: string; path: string }): Promise<void> {
  if (!scenario.fixtureRefs.includes(item.fixtureRef)) throw new Error("fixtureRef is not declared by the scenario");
  const source = string(plan.fixtures[item.fixtureRef], `fixture ${item.fixtureRef}`);
  const destination = runtimePath(root, item.path);
  await mkdir(dirname(destination), { recursive: true });
  await copyFile(source, destination);
}

/** Observe every durable entry and exact bytes, preserving the difference between absent and empty roots. */
async function durableTree(root: string): Promise<JsonObject[]> {
  try {
    const entry = await lstat(root);
    if (!entry.isDirectory() || entry.isSymbolicLink()) throw new Error("runtime root must be a regular directory");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  }
  const tree = await snapshotTree(root);
  const entries: JsonObject[] = [{ path: { path: "." }, kind: "directory" }];
  const paths = [...tree.directories, ...tree.files.keys()].sort();
  for (const path of paths) {
    const bytes = tree.files.get(path);
    entries.push(bytes === undefined
      ? { path: { path }, kind: "directory" }
      : { path: { path }, kind: "file", bytesHex: bytes.toString("hex") });
  }
  return entries;
}

/** Project an endpoint's public fields without interpreting its document content. */
function migrationEndpoint(endpoint: JsUserSettingsMigrationEndpoint): JsonObject {
  return {
    location: token(endpoint.location),
    schemaVersion: endpoint.schemaVersion === undefined ? null : {
      major: endpoint.schemaVersion.major, minor: endpoint.schemaVersion.minor,
    },
  };
}

/** Retain exact proposal bytes and ordered public review rows for the central oracle. */
function migrationPlan(plan: JsUserSettingsMigrationPlan): JsonObject {
  return {
    required: plan.required,
    baseRevision: plan.baseRevision,
    source: migrationEndpoint(plan.source),
    target: migrationEndpoint(plan.target),
    changes: plan.changes.map((change) => ({
      kind: token(change.kind), sourcePath: change.sourcePath ?? null,
      targetPath: change.targetPath ?? null, before: change.before ?? null, after: change.after ?? null,
    })),
    originalHex: plan.originalContent.toString("hex"),
    proposedHex: plan.proposedContent.toString("hex"),
  };
}

/** Normalize the binding's planning status spelling and preserve its diagnostics. */
function migrationPlanning(outcome: JsUserSettingsMigrationPlanningResult): JsonObject {
  return {
    status: outcome.status === "notRequired" ? "not-required" : outcome.status,
    diagnostics: outcome.diagnostics.map((diagnostic) => diagnostic.code),
    plan: outcome.plan === undefined ? null : migrationPlan(outcome.plan),
  };
}

/** Observe a native receipt's getters while leaving its restore authority opaque. */
function migrationReceipt(root: string, receipt: JsUserSettingsMigrationReceipt): JsonObject {
  return {
    sourcePath: { path: relativePath(root, receipt.sourcePath) },
    destinationPath: { path: relativePath(root, receipt.destinationPath) },
    backupPath: { path: relativePath(root, receipt.backupPath) },
    source: migrationEndpoint(receipt.source), target: migrationEndpoint(receipt.target),
    backupRevision: receipt.backupRevision, publishedRevision: receipt.publishedRevision,
  };
}

/** Extract only the stable native error code; unexpected JS errors fail the scenario. */
function migrationErrorCode(error: unknown): string {
  if (!(error instanceof Error) || !("code" in error)) throw error;
  return string(error.code, "migration error code");
}

/** Apply declared external bytes or backup disturbances only at their requested phase. */
async function migrationIntervention(
  plan: RunPlan, scenario: Scenario, root: string, intervention: MigrationIntervention | null | undefined,
  receipt?: JsUserSettingsMigrationReceipt,
): Promise<void> {
  if (intervention === null || intervention === undefined) return;
  if (intervention.kind === "external-edit") {
    await installFixture(plan, scenario, root, intervention);
  } else if (intervention.kind === "block-backup-directory") {
    await writeFile(runtimePath(root, "CLASSIC Backup"), "blocked");
  } else {
    if (receipt === undefined) throw new Error("backup intervention requires an applied native receipt");
    // Validate the observed backup path before writing, but keep the original native receipt for restore.
    const backup = runtimePath(root, relativePath(root, receipt.backupPath));
    if (intervention.kind === "remove-backup") {
      await unlink(backup);
    } else {
      if (!scenario.fixtureRefs.includes(intervention.fixtureRef)) throw new Error("fixtureRef is not declared by the scenario");
      await copyFile(string(plan.fixtures[intervention.fixtureRef], "backup fixture"), backup);
    }
  }
}

/** Exercise public planning, reversal, application, and opaque-receipt restoration. */
async function executeMigration(plan: RunPlan, scenario: Scenario): Promise<JsonObject> {
  const root = resolve(await mkdtemp(join(tmpdir(), "classic-node-user-settings-migration-")));
  try {
    for (const item of scenario.input.installationData) await installFixture(plan, scenario, root, item);
    const classic = await import("../index.js");
    const planning = classic.planUserSettingsMigration(root);
    const repeatedPlanning = classic.planUserSettingsMigration(root);
    const approved = planning.plan;
    const reversed = approved === undefined ? undefined : classic.reverseUserSettingsMigrationPlan(approved);
    const roundTrip = reversed === undefined ? undefined : classic.reverseUserSettingsMigrationPlan(reversed);
    const afterPlanningTree = await durableTree(root);
    let appliedReceipt: JsUserSettingsMigrationReceipt | undefined;
    let apply: JsonObject = {
      status: "not-attempted", expectedRevision: null, actualRevision: null, errorCode: null, receipt: null,
    };
    if (scenario.input.apply && approved !== undefined) {
      await migrationIntervention(plan, scenario, root, scenario.input.beforeApply);
      try {
        const outcome = classic.applyUserSettingsMigration(root, approved.baseRevision, approved.proposedContent);
        appliedReceipt = outcome.receipt;
        apply = {
          status: outcome.status,
          // Python/core expose expected revisions only on conflict; Node repeats approval on success.
          expectedRevision: outcome.status === "conflict" ? outcome.expectedRevision : null,
          actualRevision: outcome.actualRevision ?? null, errorCode: null,
          receipt: appliedReceipt === undefined ? null : migrationReceipt(root, appliedReceipt),
        };
      } catch (error) {
        apply = { ...apply, status: "error", errorCode: migrationErrorCode(error) };
      }
    }
    const afterApplyTree = await durableTree(root);
    let restore: JsonObject = {
      status: "not-attempted", revision: null, expectedRevision: null, actualRevision: null, errorCode: null,
    };
    if (scenario.input.restore && appliedReceipt !== undefined) {
      await migrationIntervention(plan, scenario, root, scenario.input.beforeRestore, appliedReceipt);
      try {
        const outcome = appliedReceipt.restore(root);
        restore = {
          status: outcome.status, revision: outcome.revision ?? null,
          expectedRevision: outcome.status === "conflict" ? outcome.expectedRevision : null,
          actualRevision: outcome.actualRevision ?? null, errorCode: null,
        };
      } catch (error) {
        restore = { ...restore, status: "error", errorCode: migrationErrorCode(error) };
      }
    }
    return {
      planning: migrationPlanning(planning), repeatedPlanning: migrationPlanning(repeatedPlanning),
      reversedPlan: reversed === undefined ? null : migrationPlan(reversed),
      roundTripPlan: roundTrip === undefined ? null : migrationPlan(roundTrip),
      afterPlanningTree, apply, afterApplyTree, restore, finalTree: await durableTree(root),
    };
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

/** Execute an explicit public preview and optional commit, measuring each durable phase separately. */
async function executeOperation(plan: RunPlan, scenario: Scenario): Promise<JsonObject> {
  const temporary = resolve(await mkdtemp(join(tmpdir(), "classic-node-user-settings-operation-")));
  // An absent installation is itself an input: previews must not silently create its root.
  const root = join(temporary, "installation");
  try {
    if (scenario.input.installationRootExists) await mkdir(root);
    for (const item of scenario.input.installationData) await installFixture(plan, scenario, root, item);
    const classic = await import("../index.js");
    const update = requestedUpdate(object(scenario.input.requestedUpdate, "requestedUpdate"));
    const bootstrap = scenario.input.previewMode === "bootstrap";
    const preview = bootstrap
      ? classic.previewUserSettingsBootstrap(root, update)
      : classic.previewUserSettingsUpdate(root, update);
    const afterPreviewTree = await durableTree(root);
    if (scenario.input.externalEdit) await installFixture(plan, scenario, root, scenario.input.externalEdit);
    let commit: JsonObject = { status: "not-attempted", revision: null, expectedRevision: null, actualRevision: null };
    if (scenario.input.commit && preview.accepted) {
      const baseRevision = string(preview.baseRevision, "accepted preview baseRevision");
      const outcome = bootstrap
        ? classic.commitUserSettingsBootstrap(root, baseRevision, update)
        : classic.commitUserSettingsUpdate(root, baseRevision, update);
      commit = {
        status: outcome.status,
        revision: outcome.revision ?? null,
        expectedRevision: outcome.status === "conflict" ? outcome.expectedRevision : null,
        actualRevision: outcome.actualRevision ?? null,
      };
    }
    return {
      preview: {
        status: preview.accepted ? "accepted" : "rejected",
        baseRevision: preview.baseRevision ?? null,
        acceptedFields: preview.fields.map((field) => ({ fieldPath: field.fieldPath, value: field.value })),
        diagnostics: preview.diagnostics.map((diagnostic) => ({
          fieldPath: diagnostic.fieldPath ?? null, code: diagnostic.code, message: diagnostic.message,
        })),
      },
      afterPreviewTree,
      commit,
      finalTree: await durableTree(root),
    };
  } finally {
    await rm(temporary, { recursive: true, force: true });
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
