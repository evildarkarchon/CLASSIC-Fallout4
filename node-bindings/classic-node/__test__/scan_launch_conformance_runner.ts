/**
 * Execute Crash Log Scan Launch plans through the public Node `ScanRunLaunch` surface.
 *
 * The launcher hands this runner an input-only plan. Each scenario launches in a fresh
 * Installation Root and records only what the Node surface reports; comparison against the
 * pack happens centrally (ADR-0008).
 */
import {randomUUID} from "node:crypto";
import {lstat, mkdir, mkdtemp, open, readFile, rename, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, join, relative, resolve, sep} from "node:path";
import type {JsGameId, JsScanRunLaunchOverrides, ScanRunLaunch} from "../index.js";

type JsonObject = Record<string, unknown>;

const FAMILY_ID = "crash-log-scan-launch";
const SETTINGS_FILE = "CLASSIC Settings.yaml";
/** The `JsGameId` string values, which are also the pack's game tokens. */
const GAME_TOKENS: readonly string[] = ["Fallout4", "Fallout4VR", "Skyrim", "Starfield"];
const INSTALLATION_ROOT_PLACEHOLDER = "{{installationRoot}}";

/** One centrally supplied input-only scenario. */
interface Scenario {
    id: string;
    capabilityIds: string[];
    fixtureRefs: string[];
    input: {
        settingsFixtureRef: string;
        intent: "standard" | "targeted";
        targetedInputs: string[];
        overrides: JsonObject;
        files?: string[];
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

/** Require one non-empty string. */
function string(value: unknown, label: string): string {
    if (typeof value !== "string" || value.length === 0) throw new Error(`${label} must be a non-empty string`);
    return value;
}

/** Render an error for a receipt or stderr. */
function errorMessage(error: unknown): string {
    return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

/** Read the plan and validate this participant's identity. */
async function loadPlan(path: string): Promise<RunPlan> {
    const plan = JSON.parse(await readFile(path, "utf8")) as RunPlan;
    if (plan.familyId !== FAMILY_ID) throw new Error(`run plan family must be ${FAMILY_ID}`);
    const participant = plan.participant;
    if (participant.id !== "node" || participant.role !== "semantic-adapter" || participant.executionInstanceId !== "node") {
        throw new Error("run plan is not the Node semantic-adapter invocation");
    }
    for (const scenario of plan.scenarios) {
        if ("expected" in scenario) throw new Error("input-only run plan must not contain expectations");
    }
    return plan;
}

/** Join a scenario-supplied relative path that must stay beneath the Installation Root. */
function beneath(root: string, value: string): string {
    if (value.includes("\\") || value.includes(":") || value.split("/").some(part => part === "" || part === "." || part === "..")) {
        throw new Error(`${value} must stay beneath the Installation Root`);
    }
    return join(root, ...value.split("/"));
}

/** Render a reported path relative to the Installation Root; the root itself is `.`. */
function rootRelative(root: string, value: string | null | undefined): string | null {
    if (value == null) return null;
    const relativePath = relative(root, value);
    if (relativePath.startsWith("..")) throw new Error(`${value} escapes the Installation Root`);
    return relativePath === "" ? "." : relativePath.split(sep).join("/");
}

/** Build the binding's overrides object from the scenario's overrides. */
function overrides(value: JsonObject, root: string): JsScanRunLaunchOverrides {
    const result: JsScanRunLaunchOverrides = {};
    if ("game" in value) {
        const game = string(value.game, "game");
        // `JsGameId` is a declared const enum with no runtime object to enumerate, so the
        // pack tokens, which equal its string values, are checked against them directly.
        if (!GAME_TOKENS.includes(game)) throw new Error(`unsupported game ${game}`);
        result.game = game as JsGameId;
    }
    if ("gameVersion" in value) result.gameVersion = string(value.gameVersion, "gameVersion");
    if ("scanPath" in value) result.scanPath = beneath(root, string(value.scanPath, "scanPath"));
    if ("maxConcurrent" in value) result.maxConcurrent = value.maxConcurrent as number;
    if (value.showFormidValues === true) result.showFormidValues = true;
    if (value.simplifyLogs === true) result.simplifyLogs = true;
    if (value.fcxMode === true) result.fcxMode = true;
    return result;
}

/**
 * Replace the fixture's `{{installationRoot}}` placeholder with this run's root.
 *
 * The root is written with `/` separators so it reads the same inside any YAML quoting;
 * both separators name the same folders on Windows.
 */
function installationRootFixture(fixture: string, root: string): string {
    return fixture.split(INSTALLATION_ROOT_PLACEHOLDER).join(root.split(sep).join("/"));
}

/** Project the FCX setup facts root-relatively, or `null` when FCX Mode is off. */
function setupContextView(launch: ScanRunLaunch, root: string): JsonObject | null {
    const context = launch.setupContext;
    if (context == null) return null;
    return {
        gameRoot: rootRelative(root, context.gameRoot),
        docsRoot: rootRelative(root, context.docsRoot),
        gameExePath: rootRelative(root, context.gameExePath),
        xseLogPath: rootRelative(root, context.xseLogPath),
    };
}

/** Frozen launch error tokens; any other thrown error is a runner failure. */
const LAUNCH_ERROR_KINDS = new Set(["targeted_without_inputs", "xse_log_inspect"]);

/** Map the Node camelCase Unsolved Logs token onto the pack's snake_case vocabulary. */
function unsolvedLogsToken(value: string | null): string | null {
    if (value === null) return null;
    return value.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

/** Project the launched request through the binding's read-only getters. */
function requestView(launch: ScanRunLaunch, root: string): JsonObject {
    const configuration = launch.configuration;
    const standard = launch.standardSource;
    const targeted = launch.targetedSource;
    return {
        intent: launch.intent,
        game: configuration.game,
        gameVersion: configuration.gameVersion,
        showFormidValues: configuration.showFormidValues,
        simplifyLogs: configuration.simplifyLogs,
        formidDatabasePaths: configuration.formidDatabasePaths.map(path => path.split("\\").join("/")),
        unsolvedLogsDestination: rootRelative(root, configuration.unsolvedLogsDestination),
        maxConcurrent: configuration.maxConcurrent ?? null,
        baseDirectory: standard === null ? null : rootRelative(root, standard.baseDirectory),
        customScanDirectory: standard === null ? null : rootRelative(root, standard.customScanDirectory),
        configuredDocumentsRoot: standard === null ? null : rootRelative(root, standard.configuredDocumentsRoot),
        unsolvedLogs: unsolvedLogsToken(launch.unsolvedLogs),
        targetedInputs: targeted === null ? null : targeted.inputs.map(path => rootRelative(root, path)),
        fcxEnabled: launch.fcxEnabled,
        setupContext: setupContextView(launch, root),
    };
}

/** Launch one scenario in a fresh Installation Root and observe the outcome. */
async function executeScenario(plan: RunPlan, scenario: Scenario): Promise<JsonObject> {
    const classic = await import("../index.js");
    const reference = string(scenario.input.settingsFixtureRef, "settingsFixtureRef");
    if (!scenario.fixtureRefs.includes(reference)) throw new Error("settings fixture is not declared by the scenario");
    const root = resolve(await mkdtemp(join(tmpdir(), "classic-scan-launch-conformance-")));
    try {
        const settings = join(root, SETTINGS_FILE);
        const fixture = await readFile(string(plan.fixtures[reference], "settings fixture"), "utf8");
        await writeFile(settings, installationRootFixture(fixture, root), "utf8");
        const before = await readFile(settings);
        // Scenario files (game executables, XSE logs) are empty files beneath the root.
        for (const item of scenario.input.files ?? []) {
            const path = beneath(root, string(item, "file"));
            await mkdir(dirname(path), {recursive: true});
            await writeFile(path, "");
        }
        const launchOverrides = overrides(scenario.input.overrides, root);
        let launch: ScanRunLaunch;
        try {
            if (scenario.input.intent === "standard") {
                launch = classic.ScanRunLaunch.standard(root, launchOverrides);
            } else if (scenario.input.intent === "targeted") {
                const inputs = scenario.input.targetedInputs.map(item => beneath(root, string(item, "targeted input")));
                launch = classic.ScanRunLaunch.targeted(root, inputs, launchOverrides);
            } else {
                throw new Error(`unsupported intent ${String(scenario.input.intent)}`);
            }
        } catch (error) {
            const code = (error as { code?: unknown }).code;
            if (typeof code !== "string" || !LAUNCH_ERROR_KINDS.has(code)) throw error;
            return {
                outcome: "error",
                errorKind: code,
                request: null,
                diagnostics: [],
                settingsUnchanged: (await readFile(settings)).equals(before),
            };
        }
        // Every launch must yield an executable copy; executing is the scan-run family's job.
        launch.request();
        return {
            outcome: "launched",
            errorKind: null,
            request: requestView(launch, root),
            // Node publishes camelCase kind tokens; the pack speaks the frozen snake_case ones.
            diagnostics: launch.diagnostics.map(diagnostic => ({
                kind: diagnostic.kind.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`),
                code: diagnostic.code,
            })),
            settingsUnchanged: (await readFile(settings)).equals(before),
        };
    } finally {
        await rm(root, {recursive: true, force: true});
    }
}

/** Run every scenario, keeping failed executions as explicit receipt evidence. */
async function buildReceipt(plan: RunPlan): Promise<JsonObject> {
    const scenarios: JsonObject[] = [];
    for (const scenario of plan.scenarios) {
        const identity = {id: scenario.id, capabilityIds: scenario.capabilityIds};
        try {
            scenarios.push({...identity, executionStatus: "completed", observation: await executeScenario(plan, scenario), failure: null});
        } catch (error) {
            scenarios.push({
                ...identity,
                executionStatus: "failed",
                observation: {},
                failure: {kind: "node-runner-error", message: errorMessage(error)},
            });
        }
    }
    return {
        schemaVersion: plan.schemaVersion,
        familyId: plan.familyId,
        familyVersion: plan.familyVersion,
        expectationDigest: plan.expectationDigest,
        invocation: {...plan.invocation},
        participant: {...plan.participant},
        runner: {id: "classic-node-scan-launch-conformance", version: 1, platform: "windows", toolchain: "bun"},
        scenarios,
    };
}

/** Recursively sort object keys for deterministic receipt serialization. */
function canonical(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(canonical);
    if (typeof value !== "object" || value === null) return value;
    const record = value as JsonObject;
    return Object.fromEntries(Object.keys(record).sort().map(key => [key, canonical(record[key])]));
}

/** Atomically publish a fresh sibling receipt. */
async function publishReceipt(path: string, receipt: JsonObject): Promise<void> {
    try {
        await lstat(path);
        throw new Error("conformance receipt destination already exists");
    } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    await mkdir(dirname(path), {recursive: true});
    const temporary = join(dirname(path), `.scan-launch-${randomUUID()}.tmp`);
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
        await rm(temporary, {force: true});
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
        console.error(`classic-node-scan-launch-conformance: ${errorMessage(error)}`);
        process.exitCode = 2;
    }
}

void main();
