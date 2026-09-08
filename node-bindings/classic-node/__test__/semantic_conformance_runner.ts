import { observeDatabaseOperations } from "./database_operations_conformance.js";
import { observeFileFingerprint } from "./file_fingerprint_conformance.js";
import { observePerformance } from "./performance_conformance.js";
import { observeMessageLogging } from "./message_logging_conformance.js";
import { observeUpdateRejection } from "./update_rejection_conformance.js";
import { observeWindowsPlatformPaths } from "./windows_platform_paths_conformance.js";
import { observeUpdateDecisions } from "./update_decisions_conformance.js";
import { observeUpdateServices } from "./update_services_conformance.js";
import { observeSharedRegistry } from "./shared_registry_conformance.js";
import { observeAuxOperations } from "./aux_operations_conformance.js";
import { observeInstallationPaths } from "./installation_paths_conformance.js";
import { observeXseOperations } from "./xse_operations_conformance.js";
import { observeSharedIdentity } from "./shared_identity_conformance.js";
import { observeYamlFileValues } from "./yaml_file_values_conformance.js";
import { observeSettingsLoad } from "./settings_load_conformance.js";
import { observeVersionRegistry } from "./version_registry_conformance.js";
import { observeScanGame } from "./scan_game_conformance.js";
import { observePapyrusMonitor } from "./papyrus_monitor_conformance.js";
import { observeFileGeneration } from "./file_generation_conformance.js";
import { observeModIni } from "./mod_ini_conformance.js";
import { observeWryeReport } from "./wrye_report_conformance.js";
import { observeLogCollection } from "./log_collection_conformance.js";
import { observeLogParsing } from "./log_parsing_conformance.js";
import { observeCrashPattern } from "./crash_pattern_conformance.js";
import { observeDdsHeader } from "./dds_header_conformance.js";
import { observeFormidFinding } from "./formid_finding_conformance.js";
import { observeBa2Scan } from "./ba2_scan_conformance.js";
import { observeUnpackedScan } from "./unpacked_scan_conformance.js";
import { observeCrashgenCheck } from "./crashgen_check_conformance.js";
import { randomUUID } from "node:crypto";
import { lstat, mkdir, open, readFile, rename, rm } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import * as classic from "../index.js";
import { observeInstalledYaml } from "./installed_yaml_conformance.js";
import { observeVocabulary } from "./vocabulary_conformance.js";
import { observeConfigOperations } from "./config_operations_conformance.js";
import { observeFileOperations } from "./file_operations_conformance.js";
import { observePathMessage } from "./path_message_conformance.js";

type JsonObject = Record<string, any>;
import { observeRegistryAccessors } from "./registry_accessors_conformance";

import { observeSettingsExtended } from "./settings_extended_conformance";

import { observeVersionValues } from "./version_values_conformance";

const families = ["game-version-parse", "game-version-distance", "fallout4-identity", "settings-yaml-batch", "settings-yaml", "settings-cached-docs", "version-registry-details", "version-extraction", "version-pe", "version-pe-path", "registry-game", "registry-paths", "settings-load", "xse-operations", "installation-paths", "game-identity", "runtime-access", "file-fingerprint", "performance", "update-decisions", "string-operations", "registry-operations", "web-operations", "resource-operations", "version-operations", "crash-suspect", "crashgen-settings", "mod-guidance", "formid-lookup", "named-record", "plugin-evidence", "installed-yaml-data", "config-vocabulary", "scan-run-vocabulary", "config-operations", "yaml-source-values", "file-backups", "xse-plugin-validation", "path-backups", "game-integrity", "game-orchestration", "game-setup-intake", "file-operations", "path-operations", "path-normalization", "message-operations", "database-operations", "version-registry", "scan-game"];

families.push("update-services", "message-logging", "update-rejection", "windows-platform-paths");
families.push("papyrus-monitor");
families.push("file-generation");
families.push("mod-ini");
families.push("wrye-report");
families.push("log-collection");
families.push("log-parsing");
families.push("crash-pattern");
families.push("yaml-file-values");
families.push("dds-header");
families.push("formid-finding");
families.push("ba2-scan");
families.push("unpacked-scan");
families.push("crashgen-check");

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
    const operationActions: Record<string, string[]> = {
      "settings-load": ["settings-load.execute"],
      "settings-yaml": ["settings-yaml.execute"],
      "game-version-parse": ["game-version-parse.observe"],
      "game-version-distance": ["game-version-distance.observe"],
      "fallout4-identity": ["fallout4-identity.observe"],

      "settings-yaml-batch": ["settings-yaml-batch.execute"],
      "settings-cached-docs": ["settings-cached-docs.observe"],
      "version-registry-details": ["version-registry-details.execute"],

      "xse-operations": ["xse-operations.inspect"],
      "installation-paths": ["installation-paths.inspect"],
      "game-identity": ["game-identity.observe", "game-identity.metadata"],
      "runtime-access": ["runtime-access.observe"],
      "file-fingerprint": ["file-fingerprint.inspect"],
      "performance": ["performance.metrics"],
      "message-logging": ["message-logging.basic"],
      "update-rejection": ["update-rejection.latest"],
      "windows-platform-paths": ["windows-platform-paths.observe"],
      "update-decisions": ["update-decisions.compare"],
      "update-services": ["update-services.notification"],
      "string-operations": ["string-operations.execute"],
      "registry-operations": ["registry-operations.execute"],
      "registry-game": ["registry-game.observe"],
      "registry-paths": ["registry-paths.observe"],
      "web-operations": ["web-operations.observe", "web-operations.routes"],
      "resource-operations": ["resource-operations.observe"],
      "version-operations": ["version-operations.observe"],
      "version-extraction": ["version-extraction.observe"],
      "version-pe": ["version-pe.observe"],
      "version-pe-path": ["version-pe-path.observe"],

      "config-operations": ["config-operations.load-explicit", "config-operations.main-version", "config-operations.persist-local"],
      "yaml-source-values": ["yaml-source-values.matrix"],
      "yaml-file-values": ["yaml-file-values.observe"],
      "file-backups": ["file-backups.managed", "file-backups.game-files"],
      "xse-plugin-validation": ["xse-plugin-validation.check"],
      "path-backups": ["path-backups.versioned"],
      "game-integrity": ["game-integrity.basic", "game-integrity.options"],
      "game-orchestration": ["game-orchestration.composed"],
      "game-setup-intake": ["game-setup-intake.run", "game-setup-intake.normalize"],
      "file-operations": ["file-operations.read-text", "file-operations.write-text"],
      "path-operations": ["path-operations.validate"],
      "path-normalization": ["path-normalization.resolve"],
      "message-operations": ["message-operations.format"],
      "database-operations": ["database-operations.pool", "database-operations.cache-defaults"],
      "version-registry": ["version-registry.query", "version-registry.enumerate", "version-registry.crashgen", "version-registry.xse"],
      "scan-game": ["scan-game.validate-ini", "scan-game.validate-enb", "scan-game.process-logs"],
      "papyrus-monitor": ["papyrus-monitor.full"],
      "file-generation": ["file-generation.generate"],
      "mod-ini": ["mod-ini.scan", "mod-ini.duplicates"],
      "wrye-report": ["wrye-report.format"],
      "log-collection": ["log-collection.collect"],
      "log-parsing": ["log-parsing.gpu", "log-parsing.node-parser", "log-parsing.crashgen-version"],
      "crash-pattern": ["crash-pattern.classify", "crash-pattern.vr"],
      "dds-header": ["dds-header.validate"],
      "formid-finding": ["formid-finding.analyze"],
      "ba2-scan": ["ba2-scan.full"],
      "unpacked-scan": ["unpacked-scan.scan"],
      "crashgen-check": ["crashgen-check.check"],
    };
    const actions = operationActions[plan.familyId] ?? (["config-vocabulary", "scan-run-vocabulary"].includes(plan.familyId) ? ["vocabulary.resolve"]
      : plan.familyId === "installed-yaml-data" ? ["installed-yaml-data.inspect", "installed-yaml-data.load"]
      : plan.familyId === "formid-lookup" ? ["formid-lookup.lookup"] : [`${plan.familyId}.analyze`]);
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
  if (["config-vocabulary", "scan-run-vocabulary"].includes(plan.familyId)) {
    return observeVocabulary(plan.familyId, scenario.input);
  }
  const reference = string(scenario.input.fixtureRef, "fixtureRef");
  if (!scenario.fixtureRefs.includes(reference)) throw new Error("fixtureRef is not declared by scenario");
  const fixture = object(JSON.parse(await readFile(string(plan.fixtures[reference], "fixture path"), "utf8")), "fixture");
  if ("expected" in fixture) throw new Error("input fixture contains expectations");
  if (plan.familyId === "installed-yaml-data") {
    if (scenario.action !== `installed-yaml-data.${fixture.operation}`) throw new Error("installed-data action disagrees with fixture operation");
    return observeInstalledYaml(fixture);
  }
  if (plan.familyId === "config-operations") return observeConfigOperations(fixture);
  if (plan.familyId === "game-setup-intake") return (await import("./game_setup_intake_conformance.js")).observeSetup(fixture);
  if (plan.familyId === "game-orchestration") return (await import("./game_orchestration_conformance.js")).observeOrchestration(fixture);
  if (plan.familyId === "file-backups") return (await import("./file_backups_conformance.js")).observeFileBackups(fixture);
  if (plan.familyId === "xse-plugin-validation") return (await import("./xse_plugin_validation_conformance.js")).observeXsePlugins(fixture);
  if (plan.familyId === "path-backups") return (await import("./path_backups_conformance.js")).observePathBackups(fixture);
  if (plan.familyId === "game-integrity") return (await import("./game_integrity_conformance.js")).observeIntegrity(fixture);
  if (plan.familyId === "yaml-source-values") return (await import("./yaml_source_values_conformance.js")).observeYamlSources(fixture);
  if (plan.familyId === "database-operations") return observeDatabaseOperations(fixture);
  if (["version-registry", "version-registry-details"].includes(plan.familyId)) return observeVersionRegistry(fixture);
  if (plan.familyId === "scan-game") return observeScanGame(fixture);
  if (plan.familyId === "papyrus-monitor") return observePapyrusMonitor(fixture);
  if (plan.familyId === "file-generation") return observeFileGeneration(fixture);
  if (plan.familyId === "mod-ini") return observeModIni(fixture);
  if (plan.familyId === "wrye-report") return observeWryeReport(fixture);
  if (plan.familyId === "log-collection") return observeLogCollection(fixture);
  if (plan.familyId === "log-parsing") return observeLogParsing(fixture);
  if (plan.familyId === "crash-pattern") return observeCrashPattern(fixture);
  if (plan.familyId === "dds-header") return observeDdsHeader(fixture);
  if (plan.familyId === "formid-finding") return observeFormidFinding(fixture);
  if (plan.familyId === "ba2-scan") return observeBa2Scan(fixture);
  if (plan.familyId === "unpacked-scan") return observeUnpackedScan(fixture);
  if (plan.familyId === "crashgen-check") return observeCrashgenCheck(fixture);
  if (plan.familyId === "file-fingerprint") return observeFileFingerprint(fixture);
  if (["registry-game", "registry-paths"].includes(plan.familyId)) return observeRegistryAccessors(plan.familyId, fixture);
  if (["game-version-parse", "game-version-distance", "fallout4-identity"].includes(plan.familyId)) return observeVersionValues(plan.familyId, fixture);
  if (plan.familyId === "settings-cached-docs") return observeSettingsExtended(plan.familyId, fixture);
  if (["settings-load", "settings-yaml", "settings-yaml-batch"].includes(plan.familyId)) return observeSettingsLoad(fixture);
  if (plan.familyId === "installation-paths") return observeInstallationPaths(fixture);
  if (plan.familyId === "xse-operations") return observeXseOperations(fixture);
  if (["game-identity", "runtime-access"].includes(plan.familyId)) return observeSharedIdentity(plan.familyId, fixture);
  if (plan.familyId === "yaml-file-values") return observeYamlFileValues(fixture);
  if (plan.familyId === "message-logging") return observeMessageLogging(fixture);
  if (plan.familyId === "update-rejection") return observeUpdateRejection(fixture);
  if (plan.familyId === "windows-platform-paths") return observeWindowsPlatformPaths(fixture);
  if (plan.familyId === "performance") return observePerformance(fixture);
  if (plan.familyId === "update-decisions") return observeUpdateDecisions(fixture);
  if (plan.familyId === "update-services") return observeUpdateServices(fixture, scenario.id);
  if (["string-operations", "registry-operations"].includes(plan.familyId)) return observeSharedRegistry(plan.familyId, fixture);
  if (["web-operations", "resource-operations", "version-operations", "version-extraction", "version-pe", "version-pe-path"].includes(plan.familyId)) return observeAuxOperations(plan.familyId, fixture);
  if (plan.familyId === "file-operations") {
    if (scenario.action !== `file-operations.${fixture.operation}`) throw new Error("file action disagrees with fixture operation");
    return observeFileOperations(fixture);
  }
  if (["path-operations", "path-normalization", "message-operations"].includes(plan.familyId)) return observePathMessage(plan.familyId, fixture);
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
