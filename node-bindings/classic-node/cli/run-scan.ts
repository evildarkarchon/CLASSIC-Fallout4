import { existsSync, readFileSync } from "node:fs";
import { availableParallelism } from "node:os";
import { basename, dirname, join } from "node:path";
import type {
	CliOptions,
	CliPaths,
	CliResult,
	JsonSummary,
} from "./types";

type BindingVersionInfo = {
	shortName: string;
};

type BindingScanResult = {
  logPath: string;
  success: boolean;
  autoscanReportPath?: string;
  cancelled: boolean;
  movedToUnsolvedLogs: boolean;
  reportWriteFailed?: boolean;
  error?: string;
};

type BindingScanRunResult = {
	status: string;
	message?: string;
	total: number;
	succeeded: number;
	failed: number;
	cancelled: number;
	logs: BindingScanResult[];
};

type ClassicNodeModule = {
	getAllVersionsForGame: (
		game: string,
		isVr?: boolean | null,
	) => BindingVersionInfo[];
	getVersion: () => string;
	scanRunExecute: (
		logPaths: string[],
		options: {
			yamlDirRoot: string;
			yamlDirData: string;
			game: string;
			gameVersion: string;
			baseDirectory?: string;
			customScanDirectory?: string;
			configuredDocumentsRoot?: string;
			showFormidValues?: boolean;
			fcxMode?: boolean;
			simplifyLogs?: boolean;
			moveUnsolvedLogs?: boolean;
			targetedMode?: boolean;
			targetedInputs?: string[];
			maxConcurrent?: number | null;
			preserveOrder?: boolean;
		},
	) => Promise<BindingScanRunResult>;
  registrySetGame: (game: string) => void;
};

function loadClassicNode(cliDir: string): ClassicNodeModule {
	// eslint-disable-next-line @typescript-eslint/no-var-requires
	return require(
		join(resolvePackageRoot(cliDir), "index.js"),
	) as ClassicNodeModule;
}

function normalizeGameVersion(value: string): string {
	return value === "AE" ? "AnniversaryEdition" : value;
}

export function autoConcurrencyForCpuCount(cpuCount: number): number {
	const recommended = Math.max(cpuCount - 2, 2);
	return Math.min(recommended, 32);
}

export function effectiveConcurrency(
	requested: number,
	cpuCount = availableParallelism(),
): number {
	if (requested > 0) {
		return requested;
	}
	return autoConcurrencyForCpuCount(cpuCount);
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

function readRequiredFile(path: string, label: string): string {
	if (!existsSync(path)) {
		throw new Error(`${label} not found at ${path}`);
	}
	return readFileSync(path, "utf8");
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

function validateScanData(paths: CliPaths, options: CliOptions): void {
	const mainYamlPath = join(paths.data, "databases", "CLASSIC Main.yaml");
	const gameYamlPath = join(
		paths.data,
		"databases",
		`CLASSIC ${options.game}.yaml`,
	);

	readRequiredFile(mainYamlPath, "CLASSIC Main.yaml");
	readRequiredFile(gameYamlPath, `CLASSIC ${options.game}.yaml`);
}

function countOrZero(count: number | undefined): number {
	return count ?? 0;
}

function pluralSuffix(count: number): "" | "s" {
	return count === 1 ? "" : "s";
}

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

function printHumanSummary(summary: JsonSummary): void {
	const shouldPrintScanErrors = hasPositiveCount(summary.scanErrors);
    const shouldPrintReportFailures = hasPositiveCount(summary.reportFailures);

	console.log("\nScan Complete");
	console.log(`  Scanned:  ${formatPluralizedCount(summary.logsFound, "log")}`);
	printOptionalPluralizedCount(
		"Errors",
		summary.scanErrors,
		"log",
		shouldPrintScanErrors,
	);
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

		const normalizedGameVersion = normalizeSupportedGameVersion(
			options.game,
			options.gameVersion,
			cliDir,
		);
		const paths = findDataRoot(process.cwd(), cliDir);
		validateScanData(paths, options);

		classicNode.registrySetGame(options.game);

		if (!options.json) {
			let modeSuffix = "";
			if (normalizedGameVersion === "VR") {
				modeSuffix += " VR";
			} else if (normalizedGameVersion !== "auto") {
				modeSuffix += ` ${normalizedGameVersion}`;
			}
			if (options.fcxMode) {
				modeSuffix += " [FCX]";
			}

			console.log(
				`CLASSIC v${version} - Crash Log Scanner (${options.game}${modeSuffix})\n`,
			);
			console.log(`Data root: ${paths.root}`);
			console.log(`Data dir:  ${paths.data}\n`);
		}

		const concurrency = effectiveConcurrency(options.maxConcurrent);
    if (!options.json) {
			console.log(
				`Scanning with ${concurrency} worker thread${concurrency === 1 ? "" : "s"}\n`,
			);
		}

		const scanResult = await classicNode.scanRunExecute(
      [],
      {
        yamlDirRoot: paths.root,
        yamlDirData: paths.data,
        game: options.game,
        gameVersion: normalizedGameVersion,
				baseDirectory: process.cwd(),
				customScanDirectory: options.scanPath,
        showFormidValues: options.showFidValues,
        fcxMode: options.fcxMode,
        simplifyLogs: options.simplifyLogs,
        moveUnsolvedLogs: false,
        targetedMode: false,
        maxConcurrent: concurrency,
        preserveOrder: false,
      },
    );
		const results = scanResult.logs;
		if (scanResult.status === "setup_failed") {
			const setupMessage = scanResult.message ?? "Crash Log Scan setup failed";
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
				message: setupMessage,
			};

			if (options.json) {
				emitJson(summary);
			} else {
				console.error(setupMessage);
			}
			return { exitCode: summary.exitCode, fatal: setupMessage };
		}

		if (scanResult.status === "no_crash_logs_found") {
			const noLogsMessage = scanResult.message ??
				(options.scanPath
					? `No crash logs found in: ${process.cwd()} or ${options.scanPath}`
					: `No crash logs found in: ${process.cwd()}`);
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
				console.log(noLogsMessage);
			}
			return { exitCode: 0 };
		}

    const reportsWritten = results.filter(
      (result) => result.success && result.autoscanReportPath,
    ).length;
    const reportFailures = results.filter(
      (result) => result.reportWriteFailed,
    ).length;

		const scanErrors = results.filter(
			(result) => !result.success && !result.reportWriteFailed,
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
		};

		if (options.json) {
			emitJson(summary);
		} else {
			printHumanSummary(summary);
		}

		return { exitCode: summary.exitCode };
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		const summary: JsonSummary = {
			mode: "fatal",
			exitCode: 2,
			game: options.game,
			gameVersion: normalizeGameVersion(options.gameVersion),
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
