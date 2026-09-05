import { existsSync } from "node:fs";
import { basename, dirname, join } from "node:path";
// `const enum` members are inlined by tsc and the import is erased, so naming these
// here costs no runtime require of `../index.js`. That matters: this CLI resolves
// the binding at run time through `loadClassicNode`, because `dist/cli/` sits at a
// different depth than the source it was compiled from.
import {
	JsScanRunDisplaySegmentKind,
	JsScanRunDisplaySeverity,
} from "../index.js";
import type {
	JsGameId,
	JsScanRunConfiguration,
	JsScanRunDisplayLine,
	JsScanRunDisplaySegment,
	JsScanRunEvent,
} from "../index.js";
import type {
	CliOptions,
	CliPaths,
	CliResult,
	JsonSummary,
	SupportedGame,
} from "./types";

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

function findDataRoot(
	currentWorkingDirectory: string,
	cliDir: string,
): CliPaths {
	const packageRoot = resolvePackageRoot(cliDir);
	const cwdDataDir = join(currentWorkingDirectory, "CLASSIC Data");
	if (existsSync(cwdDataDir)) {
		return { root: currentWorkingDirectory, data: cwdDataDir };
	}

	const packageDataDir = join(packageRoot, "CLASSIC Data");
	if (existsSync(packageDataDir)) {
		return { root: packageRoot, data: packageDataDir };
	}

	throw new Error(
		`Unable to resolve CLASSIC Data from ${currentWorkingDirectory} or ${packageRoot}`,
	);
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

export function normalizeSupportedGameVersion(
	game: string,
	requested: string,
	cliDir: string,
): string {
	const supportedGameVersions = getSupportedGameVersions(game, cliDir);
	const normalized = normalizeGameVersion(requested);
	const supported = new Set(supportedGameVersions.map(normalizeGameVersion));
	const isSupportedVersion = supported.has(normalized);
	if (!isSupportedVersion) {
		throw new Error(
			`--game-version must be one of: ${supportedGameVersions.join(", ")}`,
		);
	}
	return normalized;
}

/** Maps the CLI's supported-game vocabulary onto the binding's typed game enum. */
function toJsGameId(
	classicNode: ClassicNodeModule,
	game: SupportedGame,
): JsGameId {
	switch (game) {
		case "Fallout4":
			return classicNode.JsGameId.Fallout4;
	}
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
 * Scan settings are opened read-only from the discovered CLASSIC root. The native scan service
 * owns analysis and report writes; this function reports a stable process exit result.
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
			return { exitCode: 0 };
		}

		const paths = findDataRoot(process.cwd(), cliDir);
		const userSettings = classicNode.openUserSettings(paths.root);
		const scanSettings = userSettings.crashLogScanSettings;
		const normalizedGameVersion = normalizeSupportedGameVersion(
			options.game,
			options.gameVersion ?? scanSettings.gameVersionSelection,
			cliDir,
		);
		const fcxMode = options.fcxMode ?? scanSettings.fcxMode;
		const showFidValues =
			options.showFidValues ?? scanSettings.formidValueLookup;
		const simplifyLogs = options.simplifyLogs ?? scanSettings.simplifyLogs;
		const scanPath = options.scanPath ?? scanSettings.customScanInput;
		const requestedConcurrency =
			options.maxConcurrent ?? scanSettings.maxConcurrentScans;

		classicNode.registrySetGame(options.game);

		if (!options.json) {
			let modeSuffix = "";
			if (normalizedGameVersion === "VR") {
				modeSuffix += " VR";
			} else if (normalizedGameVersion !== "auto") {
				modeSuffix += ` ${normalizedGameVersion}`;
			}
			if (fcxMode) {
				modeSuffix += " [FCX]";
			}

			console.log(
				`CLASSIC v${version} - Crash Log Scanner (${options.game}${modeSuffix})\n`,
			);
			console.log(`Data root: ${paths.root}`);
			console.log(`Data dir:  ${paths.data}\n`);
		}

		const configuredConcurrency =
			requestedConcurrency > 0 ? requestedConcurrency : undefined;
		const configuration: JsScanRunConfiguration = {
			installationRoot: paths.root,
			game: toJsGameId(classicNode, options.game),
			gameVersion: normalizedGameVersion,
			showFormidValues: showFidValues,
			simplifyLogs,
			formidDatabasePaths:
				scanSettings.formidDatabases[options.game] ?? [],
			unsolvedLogsDestination: scanSettings.unsolvedLogsDestination,
			maxConcurrent: configuredConcurrency,
		};
		const source = {
			baseDirectory: process.cwd(),
			customScanDirectory: scanPath,
			configuredDocumentsRoot:
				userSettings.gameSetupSettings.documentsRoot,
		};
		const unsolvedLogs = scanSettings.moveUnsolvedLogs
			? classicNode.ScanRunUnsolvedLogs.moveToConfiguredOrDefault()
			: classicNode.ScanRunUnsolvedLogs.leaveInPlace();
		const request = fcxMode
			? classicNode.ScanRunRequest.standardWithFcx(
					configuration,
					source,
					unsolvedLogs,
					{
						gameRoot: userSettings.gameSetupSettings.gameRoot,
						docsRoot: userSettings.gameSetupSettings.documentsRoot,
						gameExePath:
							userSettings.gameSetupSettings.gameExecutable,
					},
				)
			: classicNode.ScanRunRequest.standard(
					configuration,
					source,
					unsolvedLogs,
				);
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
				game: options.game,
				gameVersion: normalizedGameVersion,
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
			return { exitCode: summary.exitCode, fatal: setupMessage };
		}

		// Terminal for this CLI. The run paused before analysing anything and handed back a
		// one-shot continuation that only an interactive caller can answer; this command never
		// resumes it. Falling through to the generic summary below reported a clean exit 0 with
		// "0 logs" — indistinguishable from a healthy scan of an empty folder — while the real
		// cause was a malformed CLASSIC Ignore.yaml that nothing had told the user about.
		if (scanResult.status === "local_ignore_recovery_required") {
			const recoveryMessage = runMessage;
			const summary: JsonSummary = {
				mode: "scan",
				exitCode: 1,
				game: options.game,
				gameVersion: normalizedGameVersion,
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
			return { exitCode: summary.exitCode, fatal: recoveryMessage };
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
				game: options.game,
				gameVersion: normalizedGameVersion,
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
			return { exitCode: 0 };
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
			game: options.game,
			gameVersion: normalizedGameVersion,
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

		return { exitCode: summary.exitCode };
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		const summary: JsonSummary = {
			mode: "fatal",
			exitCode: 2,
			game: options.game,
			gameVersion: normalizeGameVersion(options.gameVersion ?? "auto"),
			message,
		};

		if (options.json) {
			emitJson(summary);
		} else {
			console.error(`Fatal: ${message}`);
		}

		return { exitCode: 2, fatal: message };
	}
}
