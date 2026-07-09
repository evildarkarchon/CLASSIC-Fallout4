import { afterEach, beforeAll, describe, expect, test } from "bun:test";
import {
	existsSync,
	mkdirSync,
	mkdtempSync,
	readFileSync,
	rmSync,
	writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import {
	autoConcurrencyForCpuCount,
	effectiveConcurrency,
} from "../cli/run-scan";
import { getVersion } from "../index.js";
import {
	CLI_GAME_YAML,
	CLI_IGNORE_YAML,
	CLI_LOCAL_YAML,
	CLI_MAIN_YAML,
	CLI_SAMPLE_LOG,
} from "./fixtures/cli.fixtures";

const PACKAGE_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const DIST_CLI_PATH = join(PACKAGE_ROOT, "dist", "cli", "main.js");

const tempDirs: string[] = [];

type CliResult = {
	exitCode: number;
	stdout: string;
	stderr: string;
	output: string;
};

function rememberTempDir(prefix: string): string {
	const dir = mkdtempSync(join(tmpdir(), prefix));
	tempDirs.push(dir);
	return dir;
}

function replaceEvery(
	value: string,
	search: string,
	replacement: string,
): string {
	return value.split(search).join(replacement);
}

function replaceDocsPlaceholder(content: string, docsPath: string): string {
	const escapedDocsPath = replaceEvery(docsPath, "\\", "\\\\");
	return replaceEvery(content, "DOCS_XSE_PLACEHOLDER", escapedDocsPath);
}

function writeWorkspaceDataRoot(workspace: string): string {
	const classicDataDir = join(workspace, "CLASSIC Data");
	const databaseDir = join(classicDataDir, "databases");
	const docsDir = join(workspace, "docs", "F4SE");

	mkdirSync(databaseDir, { recursive: true });
	mkdirSync(docsDir, { recursive: true });

	writeFileSync(join(databaseDir, "CLASSIC Main.yaml"), CLI_MAIN_YAML, "utf8");
	writeFileSync(
		join(databaseDir, "CLASSIC Fallout4.yaml"),
		replaceDocsPlaceholder(CLI_GAME_YAML, docsDir),
		"utf8",
	);
	writeFileSync(
		join(workspace, "CLASSIC Ignore.yaml"),
		CLI_IGNORE_YAML,
		"utf8",
	);
	writeFileSync(
		join(classicDataDir, "CLASSIC Fallout4 Local.yaml"),
		replaceDocsPlaceholder(CLI_LOCAL_YAML, docsDir),
		"utf8",
	);

	return docsDir;
}

function ensureCliBuilt(): void {
	const build = spawnSync(process.execPath, ["run", "build:cli"], {
		cwd: PACKAGE_ROOT,
		encoding: "utf8",
	});

	expect(build.status).toBe(0);
	expect(existsSync(DIST_CLI_PATH)).toBe(true);
}

function runCli(
	args: string[],
	workingDirectory: string,
	env?: NodeJS.ProcessEnv,
): CliResult {
	const result = spawnSync(process.execPath, [DIST_CLI_PATH, ...args], {
		cwd: workingDirectory,
		encoding: "utf8",
		env: env ? { ...process.env, ...env } : process.env,
	});

	return {
		exitCode: result.status ?? -1,
		stdout: result.stdout ?? "",
		stderr: result.stderr ?? "",
		output: `${result.stdout ?? ""}${result.stderr ?? ""}`,
	};
}

beforeAll(() => {
	ensureCliBuilt();
});

afterEach(() => {
	while (tempDirs.length > 0) {
		const dir = tempDirs.pop();
		if (dir) {
			rmSync(dir, { recursive: true, force: true });
		}
	}
});

describe("classic-node CLI concurrency helpers", () => {
	test("auto concurrency keeps a minimum floor of two workers", () => {
		expect(autoConcurrencyForCpuCount(1)).toBe(2);
		expect(autoConcurrencyForCpuCount(2)).toBe(2);
		expect(autoConcurrencyForCpuCount(3)).toBe(2);
	});

	test("auto concurrency still reserves two cores when possible and caps at 32", () => {
		expect(autoConcurrencyForCpuCount(8)).toBe(6);
		expect(autoConcurrencyForCpuCount(40)).toBe(32);
	});

	test("effective concurrency preserves explicit overrides", () => {
		expect(effectiveConcurrency(5, 3)).toBe(5);
		expect(effectiveConcurrency(0, 3)).toBe(2);
	});
});

describe("classic-node CLI", () => {
	test("prints version output without scanning", () => {
		const workspace = rememberTempDir("classic-node-cli-version-");
		writeWorkspaceDataRoot(workspace);
		const expectedVersion = getVersion();

		const result = runCli(["--version"], workspace);

		expect(result.exitCode).toBe(0);
		expect(result.output).toContain("CLASSIC CLI Scanner");
		expect(result.output).toContain(expectedVersion);
	});

	test("returns success when no logs are found", () => {
		const workspace = rememberTempDir("classic-node-cli-empty-");
		const scanDir = join(workspace, "incoming");

		writeWorkspaceDataRoot(workspace);
		mkdirSync(scanDir, { recursive: true });

		const result = runCli(
			["--scan-path", scanDir, "--game-version", "auto"],
			workspace,
		);

		expect(result.exitCode).toBe(0);
		expect(result.output).toContain("No crash logs found");
	});

	test("writes AUTOSCAN reports next to scanned logs", () => {
		const workspace = rememberTempDir("classic-node-cli-success-");
		const scanDir = join(workspace, "incoming");
		const logPath = join(scanDir, "crash-2026-03-06-12-00-00.log");

		writeWorkspaceDataRoot(workspace);
		mkdirSync(scanDir, { recursive: true });
		writeFileSync(logPath, CLI_SAMPLE_LOG, "utf8");

		const result = runCli(
			["--scan-path", scanDir, "--game-version", "auto"],
			workspace,
		);
		const reportPath = join(scanDir, "crash-2026-03-06-12-00-00-AUTOSCAN.md");

		expect(result.exitCode).toBe(0);
		expect(result.output).toContain("Found 1 crash log");
		expect(existsSync(reportPath)).toBe(true);
		expect(readFileSync(reportPath, "utf8")).toContain("AUTOSCAN REPORT");
	});

	test("emits structured report failure counts when AUTOSCAN writing fails", () => {
		const workspace = rememberTempDir("classic-node-cli-report-failure-json-");
		const scanDir = join(workspace, "incoming");
		const logPath = join(scanDir, "crash-2026-03-06-12-00-00.log");
		const reportPath = join(scanDir, "crash-2026-03-06-12-00-00-AUTOSCAN.md");

		writeWorkspaceDataRoot(workspace);
		mkdirSync(scanDir, { recursive: true });
		writeFileSync(logPath, CLI_SAMPLE_LOG, "utf8");
		mkdirSync(reportPath);

		const result = runCli(
			["--json", "--scan-path", scanDir, "--game-version", "auto"],
			workspace,
		);
		const summary = JSON.parse(result.stdout);

		expect(result.exitCode).toBe(1);
		expect(summary).toMatchObject({
			mode: "scan",
			exitCode: 1,
			logsFound: 1,
			reportsWritten: 0,
			reportFailures: 1,
			scanErrors: 0,
		});
	});

	test("prints report failures separately from scan errors", () => {
		const workspace = rememberTempDir("classic-node-cli-report-failure-human-");
		const scanDir = join(workspace, "incoming");
		const logPath = join(scanDir, "crash-2026-03-06-12-00-00.log");
		const reportPath = join(scanDir, "crash-2026-03-06-12-00-00-AUTOSCAN.md");

		writeWorkspaceDataRoot(workspace);
		mkdirSync(scanDir, { recursive: true });
		writeFileSync(logPath, CLI_SAMPLE_LOG, "utf8");
		mkdirSync(reportPath);

		const result = runCli(
			["--scan-path", scanDir, "--game-version", "auto"],
			workspace,
		);

		expect(result.exitCode).toBe(1);
		expect(result.output).toContain("Reports:  0 written");
		expect(result.output).toContain("Failed:   1 report");
		expect(result.output).not.toContain("Errors:");
	});

	test("returns nonfatal exit code when one discovered log fails", () => {
		const workspace = rememberTempDir("classic-node-cli-nonfatal-");
		const scanDir = join(workspace, "incoming");
		const goodLogPath = join(scanDir, "crash-2026-03-06-12-00-00.log");
		const badLogDir = join(scanDir, "crash-2026-03-06-12-01-00.log");

		writeWorkspaceDataRoot(workspace);
		mkdirSync(scanDir, { recursive: true });
		writeFileSync(goodLogPath, CLI_SAMPLE_LOG, "utf8");
		mkdirSync(badLogDir, { recursive: true });

		const result = runCli(
			["--scan-path", scanDir, "--game-version", "auto"],
			workspace,
		);

		expect(result.exitCode).toBe(1);
		expect(result.output).toContain("Found 2 crash logs");
		expect(result.output).toContain("Errors:");
	});

	test("returns fatal exit code when CLASSIC Data cannot be resolved", () => {
		const workspace = rememberTempDir("classic-node-cli-fatal-");

		const result = runCli([], workspace);

		expect(result.exitCode).toBe(2);
		expect(result.output).toContain("Fatal:");
	});

	test("returns fatal exit code when the native binding fails during startup", () => {
		const workspace = rememberTempDir("classic-node-cli-binding-fatal-");
		writeWorkspaceDataRoot(workspace);

		const result = runCli(["--version"], workspace, {
			NAPI_RS_FORCE_WASI: "error",
		});

		expect(result.exitCode).toBe(2);
		expect(result.output).toContain("Fatal:");
		expect(result.output).toContain("WASI binding not found");
	});

	test("emits structured fatal json when the native binding fails during startup", () => {
		const workspace = rememberTempDir("classic-node-cli-binding-fatal-json-");
		writeWorkspaceDataRoot(workspace);

		const result = runCli(["--json", "--version"], workspace, {
			NAPI_RS_FORCE_WASI: "error",
		});

		expect(result.exitCode).toBe(2);
		expect(result.stderr).toBe("");
		expect(JSON.parse(result.stdout)).toMatchObject({
			mode: "fatal",
			exitCode: 2,
			message: expect.stringContaining("WASI binding not found"),
		});
	});
});
