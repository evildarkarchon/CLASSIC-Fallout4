import type {JsInstalledYamlDataRunData, JsScanRunLaunchDiagnostic} from "../index.js";

/** One launch diagnostic as the JSON summary carries it: Rust's kind, code and message. */
export type JsonLaunchDiagnostic = Pick<JsScanRunLaunchDiagnostic, "kind" | "code" | "message">;

export type CliOptions = {
    /**
     * The `--game` token, passed to Crash Log Scan Launch as a `JsGameId` override.
     * Absent means the managed game; the binding rejects a token it does not know.
     */
    game?: string;
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
    /** Crash Log Scan Launch's typed diagnostics, in the order the launch produced them. */
    launchDiagnostics?: JsonLaunchDiagnostic[];
    version?: string;
    message?: string;
};
