export const dtsSignatureFragments = [
  "export declare function createAnalysisConfigFromYamlContent(mainContent: string, gameContent: string, ignoreContent: string, game: string, vrMode: boolean, options?: JsAnalysisBuildOptions | undefined | null): JsAnalysisConfig",
  "export declare function processLogWithYamlContent(logPath: string, mainContent: string, gameContent: string, ignoreContent: string, game: string, vrMode: boolean, options?: JsAnalysisBuildOptions | undefined | null): Promise<JsAnalysisResult>",
  "export declare function processLogsBatchWithYamlContent(logPaths: Array<string>, mainContent: string, gameContent: string, ignoreContent: string, game: string, vrMode: boolean, options?: JsAnalysisBuildOptions | undefined | null): Promise<Array<JsAnalysisResult>>",
  "export declare function getAllVersionsForGame(game: string, isVr?: boolean | undefined | null): Array<JsVersionInfo>",
  "export declare function getAllExeHashes(game?: string | undefined | null, isVr?: boolean | undefined | null): Array<string>",
  "export declare function getAllScriptHashes(game?: string | undefined | null, isVr?: boolean | undefined | null): Record<string, Array<string>>",
] as const;

export const confidenceValues = [
  "exact",
  "range",
  "nearest",
  "default",
  "unknown",
] as const;

export const unknownVersionStrategies = [
  "nearest_match",
  "strict",
  "default_only",
] as const;

export const unknownVersionLogLevels = ["debug", "warning", "error"] as const;

export const crashgenStatusCases = [
  { detected: "1.28.6", validVersions: ["1.28.6", "1.37.0"], expected: "Valid" },
  { detected: "1.26.0", validVersions: ["1.28.6", "1.37.0"], expected: "Outdated" },
  { detected: "1.40.0", validVersions: ["1.28.6", "1.37.0"], expected: "NewerThanKnown" },
  { detected: "1.28.6", validVersions: [], expected: "NoSupportedVersion" },
] as const;

export const yamlDisplayNameCases = [
  { source: "Main", expected: "Main Database" },
  { source: "Settings", expected: "Settings" },
  { source: "Ignore", expected: "Ignore List" },
] as const;
