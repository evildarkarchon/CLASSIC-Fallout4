import { existsSync, readFileSync } from "node:fs";
import { availableParallelism } from "node:os";
import { basename, dirname, join } from "node:path";
import type { CliOptions, CliPaths, CliResult, JsonSummary, ScanInputs } from "./types";

type YamlDoc = Record<string, unknown>;

type BindingVersionInfo = {
  shortName: string;
};

type BindingScanResult = {
  logPath: string;
  reportLines: string[];
  success: boolean;
  error?: string;
};

type DocsPathFinderInstance = {
  findDocsPath(cachedPath?: string | null): string | null;
};

type LogCollectorInstance = {
  collectAll(): Promise<string[]>;
};

type ClassicNodeModule = {
  DocsPathFinder: new (relativePath: string) => DocsPathFinderInstance;
  JsLogCollector: new (
    baseFolder: string,
    xseFolder?: string | null,
    customFolder?: string | null,
  ) => LogCollectorInstance;
  createAnalysisConfigFromYamlContent: (
    mainContent: string,
    gameContent: string,
    ignoreContent: string,
    game: string,
    gameVersion: string,
    options?: {
      showFormidValues?: boolean;
      fcxMode?: boolean;
      simplifyLogs?: boolean;
    },
  ) => unknown;
  getAllVersionsForGame: (game: string, isVr?: boolean | null) => BindingVersionInfo[];
  getVersion: () => string;
  processLogsBatch: (
    logPaths: string[],
    config: unknown,
    maxConcurrent?: number | null,
  ) => Promise<BindingScanResult[]>;
  registrySetGame: (game: string) => void;
  writeAutoscanReport: (logPath: string, content: string) => Promise<string>;
  yamlParse: (content: string) => unknown;
};

function loadClassicNode(cliDir: string): ClassicNodeModule {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  return require(join(resolvePackageRoot(cliDir), "index.js")) as ClassicNodeModule;
}

function normalizeGameVersion(value: string): string {
  return value === "AE" ? "AnniversaryEdition" : value;
}

export function autoConcurrencyForCpuCount(cpuCount: number): number {
  const recommended = Math.max(cpuCount - 2, 2);
  return Math.min(recommended, 32);
}

export function effectiveConcurrency(requested: number, cpuCount = availableParallelism()): number {
  if (requested > 0) {
    return requested;
  }
  return autoConcurrencyForCpuCount(cpuCount);
}

export function resolvePackageRoot(cliDir: string): string {
  const parent = dirname(cliDir);
  return basename(parent) === "dist" ? dirname(parent) : parent;
}

function findDataRoot(currentWorkingDirectory: string, cliDir: string): CliPaths {
  const packageRoot = resolvePackageRoot(cliDir);
  const cwdDataDir = join(currentWorkingDirectory, "CLASSIC Data");
  if (existsSync(cwdDataDir)) {
    return { root: currentWorkingDirectory, data: cwdDataDir };
  }

  const packageDataDir = join(packageRoot, "CLASSIC Data");
  if (existsSync(packageDataDir)) {
    return { root: packageRoot, data: packageDataDir };
  }

  throw new Error(`Unable to resolve CLASSIC Data from ${currentWorkingDirectory} or ${packageRoot}`);
}

function readRequiredFile(path: string, label: string): string {
  if (!existsSync(path)) {
    throw new Error(`${label} not found at ${path}`);
  }
  return readFileSync(path, "utf8");
}

function readOptionalFile(path: string, fallback: string): string {
  return existsSync(path) ? readFileSync(path, "utf8") : fallback;
}

function readYamlDocument(path: string): YamlDoc | undefined {
  if (!existsSync(path)) {
    return undefined;
  }
  const classicNode = loadClassicNode(__dirname);
  return classicNode.yamlParse(readFileSync(path, "utf8")) as YamlDoc;
}

function readNestedString(document: YamlDoc | undefined, ...keys: string[]): string | undefined {
  let current: unknown = document;
  for (const key of keys) {
    if (!current || typeof current !== "object" || !(key in current)) {
      return undefined;
    }
    current = (current as Record<string, unknown>)[key];
  }

  return typeof current === "string" && current.length > 0 ? current : undefined;
}

function resolveXsePath(
  gameYamlPath: string,
  localYamlPath: string,
  gameVersion: string,
): string | undefined {
  const gameDoc = readYamlDocument(gameYamlPath);
  const localDoc = readYamlDocument(localYamlPath);
  const localKey = gameVersion === "VR" ? "GameVR_Info" : "Game_Info";

  const localXsePath = readNestedString(localDoc, localKey, "Docs_Folder_XSE");
  if (localXsePath) {
    return localXsePath;
  }

  const mainRootName = readNestedString(gameDoc, "Game_Info", "Main_Root_Name");
  const xseAcronym = readNestedString(gameDoc, "Game_Info", "XSE_Acronym");
  if (!mainRootName || !xseAcronym) {
    return undefined;
  }

  const classicNode = loadClassicNode(__dirname);
  const docsFinder = new classicNode.DocsPathFinder(`My Games\\${mainRootName}`);
  const docsRoot = docsFinder.findDocsPath(null);
  return docsRoot ? join(docsRoot, xseAcronym) : undefined;
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

export function getSupportedGameVersions(game: string, cliDir: string): string[] {
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
  const normalized = requested === "AE" ? "AnniversaryEdition" : requested;
  const supported = new Set(
    getSupportedGameVersions(game, cliDir).map((value) => (value === "AE" ? "AnniversaryEdition" : value)),
  );
  if (!supported.has(normalized)) {
    throw new Error(`--game-version must be one of: ${getSupportedGameVersions(game, cliDir).join(", ")}`);
  }
  return normalized;
}

function loadScanInputs(paths: CliPaths, options: CliOptions): ScanInputs {
  const mainYamlPath = join(paths.data, "databases", "CLASSIC Main.yaml");
  const gameYamlPath = join(paths.data, "databases", `CLASSIC ${options.game}.yaml`);
  const ignoreYamlPath = join(paths.root, "CLASSIC Ignore.yaml");
  const localYamlPath = join(paths.data, `CLASSIC ${options.game} Local.yaml`);

  const normalizedVersion = normalizeGameVersion(options.gameVersion);

  return {
    mainYaml: readRequiredFile(mainYamlPath, "CLASSIC Main.yaml"),
    gameYaml: readRequiredFile(gameYamlPath, `CLASSIC ${options.game}.yaml`),
    ignoreYaml: readOptionalFile(ignoreYamlPath, `CLASSIC_Ignore_${options.game}: []\n`),
    xsePath: resolveXsePath(gameYamlPath, localYamlPath, normalizedVersion),
  };
}

function printHumanSummary(summary: JsonSummary): void {
  console.log("\nScan Complete");
  console.log(`  Scanned:  ${summary.logsFound ?? 0} log${summary.logsFound === 1 ? "" : "s"}`);
  if ((summary.scanErrors ?? 0) > 0) {
    console.log(`  Errors:   ${summary.scanErrors} log${summary.scanErrors === 1 ? "" : "s"}`);
  }
  console.log(`  Reports:  ${summary.reportsWritten ?? 0} written`);
  if ((summary.reportFailures ?? 0) > 0) {
    console.log(
      `  Failed:   ${summary.reportFailures} report${summary.reportFailures === 1 ? "" : "s"}`,
    );
  }
  console.log(`  Duration: ${(summary.durationSeconds ?? 0).toFixed(2)}s`);
  const speed = (summary.logsFound ?? 0) > 0 && (summary.durationSeconds ?? 0) > 0
    ? (summary.logsFound ?? 0) / (summary.durationSeconds ?? 1)
    : 0;
  console.log(`  Speed:    ${speed.toFixed(1)} logs/sec`);
}

function emitJson(summary: JsonSummary): void {
  console.log(JSON.stringify(summary, null, 2));
}

export async function runCli(options: CliOptions, cliDir: string): Promise<CliResult> {
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

    const normalizedGameVersion = normalizeSupportedGameVersion(options.game, options.gameVersion, cliDir);
    const paths = findDataRoot(process.cwd(), cliDir);
    const scanInputs = loadScanInputs(paths, options);

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

      console.log(`CLASSIC v${version} - Crash Log Scanner (${options.game}${modeSuffix})\n`);
      console.log(`Data root: ${paths.root}`);
      console.log(`Data dir:  ${paths.data}\n`);
    }

    const collector = new classicNode.JsLogCollector(
      process.cwd(),
      scanInputs.xsePath,
      options.scanPath ?? null,
    );
    const logPaths = await collector.collectAll();

    if (logPaths.length === 0) {
      const noLogsMessage = options.scanPath
        ? `No crash logs found in: ${process.cwd()} or ${options.scanPath}`
        : `No crash logs found in: ${process.cwd()}`;
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
        durationSeconds: 0,
        message: noLogsMessage,
      };

      if (options.json) {
        emitJson(summary);
      } else {
        console.log(noLogsMessage);
      }
      return { exitCode: 0 };
    }

    const concurrency = effectiveConcurrency(options.maxConcurrent);
    const analysisConfig = classicNode.createAnalysisConfigFromYamlContent(
      scanInputs.mainYaml,
      scanInputs.gameYaml,
      scanInputs.ignoreYaml,
      options.game,
      normalizedGameVersion,
      {
        showFormidValues: options.showFidValues,
        fcxMode: options.fcxMode,
        simplifyLogs: options.simplifyLogs,
      },
    );

    if (!options.json) {
      console.log(`Found ${logPaths.length} crash log${logPaths.length === 1 ? "" : "s"}\n`);
      console.log(`Scanning with ${concurrency} worker thread${concurrency === 1 ? "" : "s"}\n`);
    }

    const results: BindingScanResult[] = await classicNode.processLogsBatch(
      logPaths,
      analysisConfig,
      concurrency,
    );
    let reportsWritten = 0;
    let reportFailures = 0;

    for (const result of results) {
      if (!result.success || result.reportLines.length === 0) {
        continue;
      }
      try {
        await classicNode.writeAutoscanReport(result.logPath, result.reportLines.join(""));
        reportsWritten += 1;
      } catch {
        reportFailures += 1;
      }
    }

    const scanErrors = results.filter((result) => !result.success).length;
    const durationSeconds = (performance.now() - startedAt) / 1000;
    const summary: JsonSummary = {
      mode: "scan",
      exitCode: scanErrors > 0 ? 1 : 0,
      game: options.game,
      gameVersion: normalizedGameVersion,
      dataRoot: paths.root,
      dataDir: paths.data,
      logsFound: logPaths.length,
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
