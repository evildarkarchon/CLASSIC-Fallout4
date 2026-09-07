import { randomUUID } from "node:crypto";
import { lstat, mkdir, open, readFile, rename, rm } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import * as classic from "../index.js";
import { observeInstalledYaml } from "./installed_yaml_conformance.js";

type JsonObject = Record<string, any>;
const families = ["crash-suspect", "crashgen-settings", "mod-guidance", "formid-lookup", "named-record", "plugin-evidence", "installed-yaml-data"];

/** Reject malformed invocation objects before invoking native operations. */
function object(value: unknown, label: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as JsonObject;
}

/** Require centrally supplied identities without silently coercing invalid input. */
function string(value: unknown, label: string): string {
  if (typeof value !== "string" || !value) throw new Error(`${label} must be a non-empty string`);
  return value;
}

/** Load only the input-only plan and validate the participant and invocation envelope. */
async function loadPlan(path: string): Promise<JsonObject> {
  const plan = object(JSON.parse(await readFile(path, "utf8")), "run plan");
  if (plan.schemaVersion !== 1 || !families.includes(plan.familyId)) throw new Error("unsupported semantic family or schema");
  if (!Number.isSafeInteger(plan.familyVersion) || plan.familyVersion < 1) throw new Error("invalid familyVersion");
  string(plan.expectationDigest, "expectationDigest");
  object(plan.fixtures, "fixtures");
  const participant = object(plan.participant, "participant");
  if (participant.id !== "node" || participant.role !== "semantic-adapter" || participant.executionInstanceId !== "node") throw new Error("not a Node semantic-adapter invocation");
  const invocation = object(plan.invocation, "invocation");
  for (const key of ["id", "sourceIdentity", "runPlanDigest"]) string(invocation[key], `invocation.${key}`);
  if (!Array.isArray(plan.scenarios) || !plan.scenarios.length) throw new Error("plan must contain scenarios");
  for (const raw of plan.scenarios) {
    const scenario = object(raw, "scenario");
    if ("expected" in scenario) throw new Error("input-only plan contains expectations");
    string(scenario.id, "scenario.id");
    for (const key of ["capabilityIds", "fixtureRefs"]) {
      if (!Array.isArray(scenario[key])) throw new Error(`${key} must be an array`);
      scenario[key].forEach((value: unknown) => string(value, key));
    }
    const actions = plan.familyId === "installed-yaml-data" ? ["installed-yaml-data.inspect", "installed-yaml-data.load"]
      : plan.familyId === "formid-lookup" ? ["formid-lookup.lookup"] : [`${plan.familyId}.analyze`];
    if (!actions.includes(scenario.action)) throw new Error("unsupported semantic action");
    object(scenario.input, "scenario.input");
  }
  return plan;
}

/** Select complete public fields, preserving absent optionals as explicit nulls. */
function fields(value: JsonObject, names: string[]): JsonObject {
  return Object.fromEntries(names.map((name) => [name, value[name] ?? null]));
}

/** Translate the Python/YAML-shaped registry carrier into the public Node carrier. */
function crashgenEntry(entry: JsonObject): classic.JsCrashgenRegistryEntry {
  return {
    displaySection: entry.display_section,
    ignoreKeys: entry.ignore_keys,
    checks: entry.checks ?? [],
    settingsRulesVersion: entry.settings_rules_version,
    settingsRules: entry.settings_rules === undefined ? undefined : {
      ...entry.settings_rules,
      version: entry.settings_rules.version ?? entry.settings_rules_version ?? 1,
      preflight: entry.settings_rules.preflight ?? [],
      checks: entry.settings_rules.checks ?? [],
    },
  };
}

/** Convert owned section mappings and version tuples without evaluating any rules. */
function crashgenRequest(request: JsonObject): classic.JsCrashgenSettingsAnalysisInput {
  return {
    settings: Object.entries(object(request.settings, "settings")).flatMap(([section, values]) =>
      Object.entries(object(values, "section settings")).map(([key, value]) => ({ section, key, value: value as string }))),
    installedPlugins: request.installedPlugins,
    crashgenVersion: request.crashgenVersion == null ? undefined : Array.isArray(request.crashgenVersion)
      ? { major: request.crashgenVersion[0], minor: request.crashgenVersion[1], patch: request.crashgenVersion[2] }
      : request.crashgenVersion,
    configLayout: request.configLayout,
  };
}

/** Execute the real public handle, optionally warming the same instance before observation. */
async function analyze(family: string, fixture: JsonObject): Promise<JsonObject> {
  const config = object(fixture.configuration, "configuration");
  const request = object(fixture.request, "request");
  let analyzerKind: string | null = null;
  try {
    if (family === "formid-lookup") {
      let lookup: classic.JsFormIdValueLookup;
      switch (config.mode) {
        case "disabled": lookup = classic.JsFormIdValueLookup.disabled(); break;
        case "in-memory": lookup = classic.JsFormIdValueLookup.inMemory(config.entries.map((entry: JsonObject) => ({
          formid: entry.formid, plugin: entry.plugin, value: entry.value ?? undefined,
          operationalFailure: entry.operationalFailure ?? undefined,
        }))); break;
        case "sqlite-missing": lookup = classic.JsFormIdValueLookup.sqlite(config.databasePath, config.gameTable); break;
        case "shared-pool": lookup = classic.JsFormIdValueLookup.fromSharedPool(new classic.JsDatabasePool(config.gameTable)); break;
        default: throw new Error("unsupported lookup mode");
      }
      if (config.mode === "sqlite-missing") return { analyzerKind: null, result: { constructed: true }, error: null };
      if (fixture.warmupRequest) await lookup.lookup(fixture.warmupRequest.formid, fixture.warmupRequest.plugin);
      if ("pairs" in request) {
        const results = await lookup.lookupBatch(request.pairs.map((pair: JsonObject) => [pair.formid, pair.plugin]));
        return { analyzerKind: null, result: { outcomes: results.map((result) => fields(result, ["kind", "value"])) }, error: null };
      }
      const result = await lookup.lookup(request.formid, request.plugin);
      return { analyzerKind: null, result: fields(result, ["kind", "value"]), error: null };
    }
    let handle: { kind: string; analyze: (request: any) => any };
    let convert = (value: JsonObject): any => value;
    let project: (value: JsonObject) => JsonObject;
    switch (family) {
      case "crash-suspect":
        handle = new classic.CrashSuspectAnalyzer(config.mainErrorRules, config.stackRules);
        project = (result) => ({ findings: result.findings.map((item: JsonObject) => fields(item, ["kind", "ruleId", "name", "severity"])) });
        break;
      case "crashgen-settings":
        handle = new classic.CrashgenSettingsAnalyzer(config.crashgenName, crashgenEntry(object(config.entry, "entry")));
        convert = crashgenRequest;
        project = (result) => ({
          expectationOutcomes: result.expectationOutcomes.map((item: JsonObject) => fields(item, ["ruleId", "kind", "severity", "message", "fix", "placement", "section", "setting", "expected", "actual"])),
          disabledSettingNotices: result.disabledSettingNotices.map((item: JsonObject) => fields(item, ["settingName"])),
        });
        break;
      case "mod-guidance":
        // NAPI object optionals accept undefined; central JSON uses null for absence.
        handle = new classic.ModGuidanceAnalyzer(config.conflicts.map((rule: JsonObject) => ({
          ...rule, fix: rule.fix ?? undefined, link: rule.link ?? undefined,
        })), config.frequentCrashes, config.solutions, config.importantMods.map((rule: JsonObject) => ({
          ...rule, gpu: rule.gpu ?? undefined, gpuMismatchWarning: rule.gpuMismatchWarning ?? undefined,
          excludeWhenPluginAny: rule.excludeWhenPluginAny ?? rule.exclude ?? undefined,
        })));
        convert = (value) => ({ ...value, userGpu: value.userGpu ?? undefined });
        project = (result) => ({
          conflicts: result.conflicts.map((item: JsonObject) => fields(item, ["state", "modA", "modB", "nameA", "nameB", "description", "fix", "link"])),
          frequentCrashes: result.frequentCrashes.map((item: JsonObject) => fields(item, ["state", "id", "name", "description", "matchedPluginIds"])),
          solutions: result.solutions.map((item: JsonObject) => fields(item, ["state", "id", "name", "description", "matchedPluginIds"])),
          importantMods: result.importantMods.map((item: JsonObject) => fields(item, ["state", "detect", "name", "description", "gpu", "gpuMismatchWarning"])),
        });
        break;
      case "named-record":
        handle = new classic.NamedRecordFindingAnalyzer(config.targetRecords, config.ignoreRecords);
        project = (result) => ({ findings: result.findings.map((item: JsonObject) => fields(item, ["record", "occurrences"])) });
        break;
      case "plugin-evidence":
        handle = new classic.PluginEvidenceAnalyzer(config.ignoredPlugins);
        convert = (value) => ({ callStack: value.crashLines, plugins: value.plugins });
        project = (result) => ({ evidence: result.evidence.map((item: JsonObject) => fields(item, ["plugin", "occurrences"])) });
        break;
      default: throw new Error("unsupported semantic family");
    }
    analyzerKind = handle.kind;
    if (fixture.warmupRequest) await handle.analyze(convert(fixture.warmupRequest));
    return { analyzerKind, result: project(await handle.analyze(convert(request))), error: null };
  } catch (error) {
    // Only native domain errors are successful observations; adapter defects fail execution.
    if (!(error instanceof Error) || !("code" in error)) throw error;
    const native = error as Error & { code: string; analyzerKind?: string; formid?: string; plugin?: string };
    if (family !== "formid-lookup" && !native.analyzerKind) throw error;
    if (family === "formid-lookup" && !["malformed_result", "operational_failure"].includes(native.code)) throw error;
    analyzerKind = native.analyzerKind ?? null;
    return { analyzerKind, result: null, error: {
      analyzerKind, code: native.code, message: native.message,
      ...(family === "formid-lookup" ? { formid: native.formid ?? null, plugin: native.plugin ?? null } : {}),
    } };
  }
}

/** Read exclusively the declared input fixture and observe the selected native operation. */
async function executeScenario(plan: JsonObject, scenario: JsonObject): Promise<JsonObject> {
  const reference = string(scenario.input.fixtureRef, "fixtureRef");
  if (!scenario.fixtureRefs.includes(reference)) throw new Error("fixtureRef is not declared by scenario");
  const fixture = object(JSON.parse(await readFile(string(plan.fixtures[reference], "fixture path"), "utf8")), "fixture");
  if ("expected" in fixture) throw new Error("input fixture contains expectations");
  if (plan.familyId === "installed-yaml-data") {
    if (scenario.action !== `installed-yaml-data.${fixture.operation}`) throw new Error("installed-data action disagrees with fixture operation");
    return observeInstalledYaml(fixture);
  }
  return analyze(plan.familyId, fixture);
}

/** Preserve failed executions explicitly, independently of expected domain failures. */
async function buildReceipt(plan: JsonObject): Promise<JsonObject> {
  const scenarios = [];
  for (const scenario of plan.scenarios) {
    const identity = { id: scenario.id, capabilityIds: scenario.capabilityIds };
    try {
      scenarios.push({ ...identity, executionStatus: "completed", observation: await executeScenario(plan, scenario), failure: null });
    } catch (error) {
      scenarios.push({ ...identity, executionStatus: "failed", observation: {}, failure: { kind: "node-runner-error", message: error instanceof Error ? `${error.name}: ${error.message}` : String(error) } });
    }
  }
  return {
    ...fields(plan, ["schemaVersion", "familyId", "familyVersion", "expectationDigest", "participant", "invocation"]),
    runner: { id: "classic-node-semantic-conformance", version: 1, platform: process.platform === "win32" ? "windows" : process.platform === "darwin" ? "macos" : "linux", toolchain: "bun" },
    scenarios,
  };
}

/** Sort only object keys; result array ordering remains semantic evidence. */
function canonical(value: any): any {
  if (Array.isArray(value)) return value.map(canonical);
  if (typeof value !== "object" || value === null) return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
}

/** Publish a fresh receipt atomically beside its immutable plan. */
async function publishReceipt(path: string, receipt: JsonObject): Promise<void> {
  try {
    await lstat(path);
    throw new Error("conformance receipt destination already exists");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  await mkdir(dirname(path), { recursive: true });
  const temporary = join(dirname(path), `.semantic-${randomUUID()}.tmp`);
  try {
    const output = await open(temporary, "wx");
    try {
      await output.writeFile(JSON.stringify(canonical(receipt)), "utf8");
      await output.sync();
    } finally {
      await output.close();
    }
    await rename(temporary, path);
  } finally {
    await rm(temporary, { force: true });
  }
}

/** Consume environment-only paths and report infrastructure errors with a failing status. */
async function main(): Promise<void> {
  try {
    const planPath = resolve(string(process.env.CLASSIC_CONFORMANCE_RUN_PLAN, "CLASSIC_CONFORMANCE_RUN_PLAN"));
    const outputPath = resolve(string(process.env.CLASSIC_CONFORMANCE_OUTPUT, "CLASSIC_CONFORMANCE_OUTPUT"));
    if (dirname(planPath) !== dirname(outputPath)) throw new Error("receipt must be a sibling of its run plan");
    await publishReceipt(outputPath, await buildReceipt(await loadPlan(planPath)));
  } catch (error) {
    console.error(`classic-node-semantic-conformance: ${error}`);
    process.exitCode = 2;
  }
}

void main();
