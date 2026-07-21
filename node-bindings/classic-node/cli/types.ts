import type { JsInstalledYamlDataRunData } from "../index.js";

export const SUPPORTED_GAMES = ["Fallout4"] as const;

export type SupportedGame = (typeof SUPPORTED_GAMES)[number];

export type CliOptions = {
  game: SupportedGame;
  gameVersion?: string;
  scanPath?: string;
  fcxMode?: boolean;
  showFidValues?: boolean;
  simplifyLogs?: boolean;
  maxConcurrent?: number;
  version: boolean;
  json: boolean;
};

export type CliPaths = {
  root: string;
  data: string;
};

export type CliResult = {
  exitCode: number;
  fatal?: string;
};

export type JsonSummary = {
  mode: "version" | "scan" | "fatal";
  exitCode: number;
  game?: string;
  gameVersion?: string;
  dataRoot?: string;
  dataDir?: string;
  logsFound?: number;
  reportsWritten?: number;
  reportFailures?: number;
  scanErrors?: number;
  durationSeconds?: number;
  installedYamlData?: JsInstalledYamlDataRunData;
  version?: string;
  message?: string;
};
