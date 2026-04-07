export const dtsSignatureFragments = [
  "export declare function createAnalysisConfigFromYamlContent(mainContent: string, gameContent: string, ignoreContent: string, game: string, gameVersion: string, options?: JsAnalysisBuildOptions | undefined | null): JsAnalysisConfig",
  "export declare function processLogWithYamlContent(logPath: string, mainContent: string, gameContent: string, ignoreContent: string, game: string, gameVersion: string, options?: JsAnalysisBuildOptions | undefined | null): Promise<JsAnalysisResult>",
  "export declare function processLogsBatchWithYamlContent(logPaths: Array<string>, mainContent: string, gameContent: string, ignoreContent: string, game: string, gameVersion: string, options?: JsAnalysisBuildOptions | undefined | null, maxConcurrent?: number | undefined | null): Promise<Array<JsAnalysisResult>>",
  "export declare function processLogsBatch(logPaths: Array<string>, config: JsAnalysisConfig, maxConcurrent?: number | undefined | null): Promise<Array<JsAnalysisResult>>",
  "export declare function getAllVersionsForGame(game: string, isVr?: boolean | undefined | null): Array<JsVersionInfo>",
  "export declare function getAllExeHashes(game?: string | undefined | null, isVr?: boolean | undefined | null): Array<string>",
  "export declare function getAllScriptHashes(game?: string | undefined | null, isVr?: boolean | undefined | null): Record<string, Array<string>>",
  "export declare function getAllGameIds(): Array<JsGameId>",
  "export declare function getGameName(id: JsGameId): string",
  "export declare function checkDriveExists(path: string): void",
  "export declare function calculateTextSimilarity(text1: string, text2: string): number",
  "export interface FileIoConfig {",
  "export const CRASH_AUTOSCAN_PATTERN: string",
  "export declare function writeAutoscanReport(logPath: string, content: string): Promise<string>",
  "export const DEFAULT_CACHE_TTL: number",
  "export declare class YamlDocument {",
  "export declare function loadSettingsSync(key: string, path: string): any",
  "export declare function loadSettingsAsync(key: string, path: string): Promise<any>",
  "export declare function getSettingsCacheStats(): SettingsCacheStats",
  "export declare function getHashCacheStats(): HashCacheStats",
  "export declare function yamlGetCacheStats(): { hits: number; misses: number; hit_rate: number; size: number; capacity: number }",
  "export declare class JsFileIO {",
  "export declare class JsLogCollector {",
  "export type JsDDSAnalyzer = JsDdsAnalyzer",
  "export interface JsDdsIssue {",
  "export interface JsDdsBatchResult {",
  "export interface JsIniCheckResult {",
  "export declare class GamePathFinder {",
  "export declare function normalizePath(path: string): string",
  "export declare function validatePathsBatch(paths: Array<string>): Record<string, boolean>",
  "export declare function loadBatchSync(paths: Array<string>): number",
  "export declare function loadBatchAsync(paths: Array<string>): Promise<number>",
  "export declare function recordTimingMetric(label: string, durationMs: number): void",
  "export declare function getMetricsSummary(): MetricsSummaryResult",
  "export declare function getRuntimeInfo(): RuntimeInfo",
  "export declare function createMessage(msgType: JsMessageType, content: string, target?: JsMessageTarget | undefined | null): JsMessage",
  "export declare const enum JsMessageType {",
  "export declare const enum JsMessageTarget {",
  "export interface MetricsSummaryResult {",
  "export interface RuntimeInfo {",
  "export interface TimingStats {",
  "export declare class JsDatabasePool {",
  "export declare function detectResourceType(path: string): string",
  "export declare function parseXseType(typeName: string): JsXseType",
  "export declare class GithubClient {",
  "export declare function getModSiteUrl(site: JsModSite): string",
  "export declare function checkForUpdates(owner: string, repo: string, currentVersion: string): Promise<JsUpdateCheckResult>",
  "export declare function runGameChecks(config: JsGameScanConfig): Promise<JsGameScanResult>",
  "export interface JsBa2ScanResult {",
  "export declare const enum JsGameId {",
  "export interface JsCompatibleRange {",
  "export interface JsMatchResult {",
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
