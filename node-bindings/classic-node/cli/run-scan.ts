import {basename, dirname, join} from "node:path";
import type {
    JsGameId,
    JsScanRunDisplayLine,
    JsScanRunDisplaySegment,
    JsScanRunEvent,
    JsScanRunLaunchOverrides,
} from "../index.js";
// `const enum` members are inlined by tsc and the import is erased, so naming these
// here costs no runtime require of `../index.js`. That matters: this CLI resolves
// the binding at run time through `loadClassicNode`, because `dist/cli/` sits at a
// different depth than the source it was compiled from.
import {JsScanRunDisplaySegmentKind, JsScanRunDisplaySeverity,} from "../index.js";
import type {CliOptions, CliPaths, CliResult, JsonSummary} from "./types";

type ClassicNodeModule = typeof import("../index.js");

function loadClassicNode(cliDir: string): ClassicNodeModule {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require(
        join(resolvePackageRoot(cliDir), "index.js"),
    ) as ClassicNodeModule;
}

function normalizeGameVersion(value: string): string {
    return value === "AE" ? "AnniversaryEdition" : value;
}

export function resolvePackageRoot(cliDir: string): string {
    const parent = dirname(cliDir);
    return basename(parent) === "dist" ? dirname(parent) : parent;
}

/**
 * Locates the Installation Root through Config's shared locator.
 *
 * The CLI's own folder stands in for the executable folder: the Node executable lives
 * wherever Node was installed, which says nothing about the CLASSIC installation. The
 * locator's parent and grandparent candidates then cover the package root from both
 * `cli/` and `dist/cli/`. There is deliberately no fallback, so a run from the wrong
 * folder never scans it as if it were the installation.
 *
 * @throws Error whose message starts with "CLASSIC Data not found" and names both
 *   search starts, when no candidate holds `CLASSIC Data`.
 */
function locateDataRoot(
    classicNode: ClassicNodeModule,
    currentWorkingDirectory: string,
    cliDir: string,
): CliPaths {
    const root = classicNode.locateInstallationRoot(cliDir, currentWorkingDirectory);
    if (root === null) {
        throw new Error(
            "CLASSIC Data not found. Run the CLI from the CLASSIC installation folder, " +
            "or place it next to the CLASSIC Data folder. " +
            `(CLI folder: ${cliDir}; working directory: ${currentWorkingDirectory})`,
        );
    }
    return {root, data: join(root, "CLASSIC Data")};
}

function toCliGameVersion(shortName: string): string | undefined {
    switch (shortName) {
        case "OG":
            return "Original";
        case "NG":
            return "NextGen";
        case "AE":
            return "AnniversaryEdition";
        case "VR":
            return "VR";
        default:
            return undefined;
    }
}

export function getSupportedGameVersions(
    game: string,
    cliDir: string,
): string[] {
    const classicNode = loadClassicNode(cliDir);
    const allVersions = [
        ...classicNode.getAllVersionsForGame(game, false),
        ...classicNode.getAllVersionsForGame(game, true),
    ];
    const supported = new Set<string>(["auto"]);

    for (const version of allVersions) {
        const cliValue = toCliGameVersion(version.shortName);
        if (cliValue) {
            supported.add(cliValue);
        }
    }

    if (supported.has("AnniversaryEdition")) {
        supported.add("AE");
    }

    return [...supported];
}

/**
 * Projects the flags the user supplied onto Crash Log Scan Launch's override model.
 *
 * Only supplied flags become overrides; an absent flag leaves the saved User Setting in
 * force, which Rust decides. `--game` passes its `JsGameId` token straight through, so
 * the binding rather than a table here decides which games exist (an unknown token is
 * rejected by the binding). `--max-concurrent 0` is an explicit request for adaptive
 * concurrency, which the launch honours over a saved limit. The boolean flags are
 * supplied-as-on: present means on for this run.
 */
function toLaunchOverrides(options: CliOptions): JsScanRunLaunchOverrides {
    const overrides: JsScanRunLaunchOverrides = {};
    if (options.game !== undefined) {
        // `JsGameId` is a string enum whose values are the game tokens this flag takes.
        overrides.game = options.game as JsGameId;
    }
    if (options.gameVersion !== undefined) {
        overrides.gameVersion = normalizeGameVersion(options.gameVersion);
    }
    if (options.scanPath !== undefined) {
        overrides.scanPath = options.scanPath;
    }
    if (options.maxConcurrent !== undefined) {
        overrides.maxConcurrent = options.maxConcurrent;
    }
    if (options.showFidValues) {
        overrides.showFormidValues = true;
    }
    if (options.simplifyLogs) {
        overrides.simplifyLogs = true;
    }
    if (options.fcxMode) {
        overrides.fcxMode = true;
    }
    return overrides;
}

function countOrZero(count: number | undefined): number {
    return count ?? 0;
}

function pluralSuffix(count: number): "" | "s" {
    return count === 1 ? "" : "s";
}

/**
 * Formats a count this CLI owns, choosing the noun form itself.
 *
 * One caller remains: the report-write failure tally, which is an aggregate over
 * per-log outcomes that Rust does not count. Every other count this command prints
 * now arrives as a `Count` segment whose noun Rust already agreed with its value.
 */
function formatPluralizedCount(
    count: number | undefined,
    singularLabel: string,
): string {
    const resolvedCount = countOrZero(count);
    return `${resolvedCount} ${singularLabel}${pluralSuffix(resolvedCount)}`;
}

function hasPositiveCount(count: number | undefined): boolean {
    return countOrZero(count) > 0;
}

/**
 * Renders one typed segment by reading only the field its `kind` selects.
 *
 * Every branch is a read rather than a decision. The one branch that composes,
 * `Count`, prints the value beside the noun Rust already resolved to agree with it
 * — it never re-decides that noun, which is what stops a user ever reading
 * "1 logs".
 */
export function renderDisplaySegment(segment: JsScanRunDisplaySegment): string {
    switch (segment.kind) {
        case JsScanRunDisplaySegmentKind.Count:
            return `${segment.count} ${segment.text}`;
        case JsScanRunDisplaySegmentKind.Path:
            // Whole and untruncated. Truncating is a choice this frontend declines to
            // make: its output is meant to be piped, and a shortened path is not one a
            // later command can open.
            return segment.path;
        default:
            return segment.text;
    }
}

/**
 * Concatenates a line's segments in reading order, separated by single spaces.
 *
 * Segments are never reordered within a line. Styling and capitalization are both
 * the empty choice, matching the native C++ CLI: this output is meant to be piped,
 * so it gains no escape sequences, and a line-initial Display Label reaches the
 * user in the vocabulary's own casing rather than in a second copy of the wording.
 */
export function renderDisplayLine(line: JsScanRunDisplayLine): string {
    return line.segments.map(renderDisplaySegment).join(" ");
}

/**
 * Prints what Rust said, routing each line to a stream by the severity Rust gave it.
 *
 * The cut falls at `Warning` rather than `Failure` because a run paused awaiting a
 * Local Ignore decision carries that severity and belongs on stderr, where this
 * command has always reported it. Severity reaches no further than the stream
 * choice — Rust names no colour, and this frontend adds none.
 */
function printDisplayLines(lines: readonly JsScanRunDisplayLine[]): void {
    for (const line of lines) {
        const text = renderDisplayLine(line);
        const isSevere =
            line.severity === JsScanRunDisplaySeverity.Warning ||
            line.severity === JsScanRunDisplaySeverity.Failure;
        if (isSevere) {
            console.error(text);
        } else {
            console.log(text);
        }
    }
}

/**
 * Reduces a rendered block to the one line that states its outcome.
 *
 * Used only where a single string is required — the JSON summary's `message` and a
 * thrown fatal — because every render entry point opens on the line that states the
 * outcome. Returns an empty string for an empty block, which a caller treats as
 * "Rust said nothing" rather than substituting prose of its own.
 */
function displayStatusLine(lines: readonly JsScanRunDisplayLine[]): string {
    const first = lines[0];
    return first ? renderDisplayLine(first) : "";
}

function calculateScanSpeed(
    logsFound: number | undefined,
    durationSeconds: number | undefined,
): number {
    const logCount = countOrZero(logsFound);
    const duration = countOrZero(durationSeconds);
    const canCalculateSpeed = logCount > 0 && duration > 0;
    return canCalculateSpeed ? logCount / duration : 0;
}

function printOptionalPluralizedCount(
    label: string,
    count: number | undefined,
    singularLabel: string,
    shouldPrint: boolean,
): void {
    if (!shouldPrint) {
        return;
    }
    console.log(`  ${label}:   ${formatPluralizedCount(count, singularLabel)}`);
}

/**
 * Prints the totals this process measured, under a header this frontend owns.
 *
 * Scanned and errored counts used to head this block and are gone: Rust states both
 * in the lines printed above it, and repeating them here would be a second account
 * of the same run. What remains is the two aggregates over per-log outcomes that
 * the contract does not tally, and the two facts derived from a clock it does not
 * carry.
 */
function printHumanSummary(summary: JsonSummary): void {
    const shouldPrintReportFailures = hasPositiveCount(summary.reportFailures);

    console.log("\nScan Complete");
    console.log(`  Reports:  ${countOrZero(summary.reportsWritten)} written`);
    printOptionalPluralizedCount(
        "Failed",
        summary.reportFailures,
        "report",
        shouldPrintReportFailures,
    );
    console.log(
        `  Duration: ${countOrZero(summary.durationSeconds).toFixed(2)}s`,
    );
    const speed = calculateScanSpeed(summary.logsFound, summary.durationSeconds);
    console.log(`  Speed:    ${speed.toFixed(1)} logs/sec`);
}

function emitJson(summary: JsonSummary): void {
    console.log(JSON.stringify(summary, null, 2));
}

/**
 * Runs the CLI command using explicit flags as overrides over canonical User Settings.
 *
 * The request comes from Crash Log Scan Launch, which opens User Settings read-only from
 * the located Installation Root and scans from that root. The native scan service owns
 * analysis and report writes; this function reports a stable process exit result.
 */
export async function runCli(
    options: CliOptions,
    cliDir: string,
): Promise<CliResult> {
    const startedAt = performance.now();

    try {
        const classicNode = loadClassicNode(cliDir);
        const version = classicNode.getVersion();
        if (options.version) {
            const summary: JsonSummary = {
                mode: "version",
                exitCode: 0,
                version,
                message: `CLASSIC CLI Scanner v${version}`,
            };

            if (options.json) {
                emitJson(summary);
            } else {
                console.log(`CLASSIC CLI Scanner v${version}`);
                console.log("Node TypeScript build using Rust NAPI bindings");
            }
            return {exitCode: 0};
        }

        const paths = locateDataRoot(classicNode, process.cwd(), cliDir);
        // Crash Log Scan Launch owns the whole request: it reads User Settings read-only,
        // lets each supplied flag win over its saved value, selects the scanned game's
        // FormID rows (including the Fallout 4 VR read rule), applies the game-differs
        // rule, and makes the Installation Root the Standard base folder. This CLI only
        // says which flags the user supplied.
        const launch = classicNode.ScanRunLaunch.standard(
            paths.root,
            toLaunchOverrides(options),
        );
        const configuration = launch.configuration;
        const launchedGame: string = configuration.game;
        const launchedGameVersion = configuration.gameVersion;

        classicNode.registrySetGame(launchedGame);

        if (!options.json) {
            const modeSuffix =
                (launchedGameVersion !== "auto" ? ` ${launchedGameVersion}` : "") +
                (launch.fcxEnabled ? " [FCX]" : "");

            console.log(
                `CLASSIC v${version} - Crash Log Scanner (${launchedGame}${modeSuffix})\n`,
            );
            console.log(`Data root: ${paths.root}`);
            console.log(`Data dir:  ${paths.data}\n`);
            // What the launch withheld or degraded, in Rust's words. Printed before the
            // run because it describes the request the run is about to execute.
            if (launch.displayLines.length > 0) {
                printDisplayLines(launch.displayLines);
                console.log("");
            }
        }
        const launchDiagnostics = launch.diagnostics.map(({kind, code, message}) => ({
            kind,
            code,
            message,
        }));
        const request = launch.request();
        const cancellation = new classicNode.ScanRunCancellation();
        // Which event kinds earn a durable console line is this frontend's choice and
        // is unchanged: the two that describe the run about to happen. Omitting whole
        // lines is what an adapter may do; rewording them is not, so the two it does
        // show are now Rust's lines rather than sentences composed here.
        const observeScanRun = (event: JsScanRunEvent): void => {
            if (options.json) {
                return;
            }
            if (
                event.kind !== "discovery_completed" &&
                event.kind !== "effective_concurrency_selected"
            ) {
                return;
            }
            printDisplayLines(event.displayLines);
            console.log("");
        };
        const execution = await classicNode.scanRunExecute(
            request,
            cancellation,
            observeScanRun,
            false,
        );
        if ("error" in execution) {
            // Stated in Rust's words. This used to read `${stage}: ${message}`, which
            // printed a Vocabulary Token where a sentence belongs — a user was told the
            // run failed during `formid_database_access` rather than during FormID
            // database access. The token is machine-facing identity and still rides on
            // `execution.error.stage` for anything that matches on it.
            //
            // Joined into one string rather than printed line by line because this path
            // throws, and the catch below owns how a fatal reaches the user in both
            // output modes. The rendered block always opens on the failure headline.
            const rendered = execution.displayLines.map(renderDisplayLine);
            throw new Error(
                rendered.length > 0
                    ? rendered.join(" - ")
                    : // Unreachable through the binding: both failure renderers always
                    // produce a headline. Guarded anyway, because the alternative is
                    // exiting 2 in silence, which reads as the process dying rather
                    // than as a run that failed. This sentence reports a broken
                    // binding promise, not anything a run said, so it stays ours.
                    "Crash Log Scan Run failed without describing the failure",
            );
        }
        if (execution.observerError) {
            throw new Error(`scan observer: ${execution.observerError}`);
        }
        const scanResult = execution.result;
        const results = scanResult.logs;
        // What the run says, for whichever branch below claims it. Rust states the
        // outcome, the Installed YAML Data block, and the per-log lines; the branches
        // keep only their exit codes, their JSON shape, and the totals this process
        // measured.
        const runMessage =
            scanResult.message ?? displayStatusLine(execution.displayLines);
        if (scanResult.status === "setup_failed") {
            const setupMessage = runMessage;
            const summary: JsonSummary = {
                mode: "scan",
                exitCode: 1,
                game: launchedGame,
                gameVersion: launchedGameVersion,
                launchDiagnostics,
                dataRoot: paths.root,
                dataDir: paths.data,
                logsFound: scanResult.total,
                reportsWritten: 0,
                reportFailures: 0,
                scanErrors: 0,
                durationSeconds: (performance.now() - startedAt) / 1000,
                installedYamlData: scanResult.installedYamlData,
                message: setupMessage,
            };

            if (options.json) {
                emitJson(summary);
            } else {
                printDisplayLines(execution.displayLines);
            }
            return {exitCode: summary.exitCode, fatal: setupMessage};
        }

        // Terminal for this CLI. The run paused before analysing anything and handed back a
        // one-shot pending recovery that only an interactive caller can answer; this command never
        // settles it. Falling through to the generic summary below reported a clean exit 0 with
        // "0 logs" — indistinguishable from a healthy scan of an empty folder — while the real
        // cause was a malformed CLASSIC Ignore.yaml that nothing had told the user about.
        if (scanResult.status === "local_ignore_recovery_required") {
            const recoveryMessage = runMessage;
            const summary: JsonSummary = {
                mode: "scan",
                exitCode: 1,
                game: launchedGame,
                gameVersion: launchedGameVersion,
                launchDiagnostics,
                dataRoot: paths.root,
                dataDir: paths.data,
                logsFound: scanResult.total,
                reportsWritten: 0,
                reportFailures: 0,
                scanErrors: 0,
                durationSeconds: (performance.now() - startedAt) / 1000,
                installedYamlData: scanResult.installedYamlData,
                message: recoveryMessage,
            };

            if (options.json) {
                emitJson(summary);
            } else {
                printDisplayLines(execution.displayLines);
            }
            return {exitCode: summary.exitCode, fatal: recoveryMessage};
        }

        if (scanResult.status === "no_crash_logs_found") {
            // The searched locations used to be spelled out here from `process.cwd()`
            // and the configured scan path, which meant this command decided both the
            // sentence and which directories it named. Rust's discovery block states
            // them, from the paths discovery actually searched rather than from the two
            // this command happened to pass in.
            const noLogsMessage = runMessage;
            const summary: JsonSummary = {
                mode: "scan",
                exitCode: 0,
                game: launchedGame,
                gameVersion: launchedGameVersion,
                launchDiagnostics,
                dataRoot: paths.root,
                dataDir: paths.data,
                logsFound: 0,
                reportsWritten: 0,
                reportFailures: 0,
                scanErrors: 0,
                durationSeconds: (performance.now() - startedAt) / 1000,
                message: noLogsMessage,
            };

            if (options.json) {
                emitJson(summary);
            } else {
                printDisplayLines(execution.displayLines);
            }
            return {exitCode: 0};
        }

        const reportsWritten = results.filter(
            (result) => result.autoscanReport,
        ).length;
        const reportFailures = results.filter((result) =>
            result.failures.some((failure) => failure.stage === "report_write"),
        ).length;

        const scanErrors = results.filter(
            (result) =>
                result.disposition === "failed" &&
                !result.failures.some(
                    (failure) => failure.stage === "report_write",
                ),
        ).length;
        const durationSeconds = (performance.now() - startedAt) / 1000;
        const summary: JsonSummary = {
            mode: "scan",
            exitCode: scanErrors > 0 || reportFailures > 0 ? 1 : 0,
            game: launchedGame,
            gameVersion: launchedGameVersion,
            launchDiagnostics,
            dataRoot: paths.root,
            dataDir: paths.data,
            logsFound: scanResult.total,
            reportsWritten,
            reportFailures,
            scanErrors,
            durationSeconds,
            installedYamlData: scanResult.installedYamlData,
        };

        if (options.json) {
            emitJson(summary);
        } else {
            // Rust's account of the run first, this process's measurements after. The
            // order is this frontend's; the words in the first block are not.
            printDisplayLines(execution.displayLines);
            printHumanSummary(summary);
        }

        return {exitCode: summary.exitCode};
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const summary: JsonSummary = {
            mode: "fatal",
            exitCode: 2,
            // What the user asked for; a fatal can precede the launch that would have
            // settled the game and version, so absent flags stay absent.
            game: options.game,
            gameVersion:
                options.gameVersion === undefined
                    ? undefined
                    : normalizeGameVersion(options.gameVersion),
            message,
        };

        if (options.json) {
            emitJson(summary);
        } else {
            console.error(`Fatal: ${message}`);
        }

        return {exitCode: 2, fatal: message};
    }
}
