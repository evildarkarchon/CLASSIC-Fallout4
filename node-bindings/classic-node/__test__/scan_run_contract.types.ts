import {
	ScanRunRequest,
	ScanRunUnsolvedLogs,
	scanRunExecute,
	JsGameId,
	JsScanRunInstalledYamlDataDiagnosticKind,
	JsScanRunLocalIgnoreRecoveryDecision,
	JsScanRunLocalIgnoreState,
	type JsScanRunConfiguration,
	type JsScanRunEvent,
	type JsScanRunSetupContext,
} from "../index.js";

const configuration: JsScanRunConfiguration = {
	installationRoot: "C:/CLASSIC",
	game: JsGameId.Fallout4,
	gameVersion: "auto",
	showFormidValues: false,
	simplifyLogs: false,
	formidDatabasePaths: [],
};
const standardSource = { baseDirectory: "C:/Crash Logs" };
const targetedSource = { inputs: ["C:/Crash Logs/crash-1.log"] };
const movement = ScanRunUnsolvedLogs.leaveInPlace();
const setupContext: JsScanRunSetupContext = {};

ScanRunRequest.standard(configuration, standardSource, movement);
ScanRunRequest.standardWithFcx(
	configuration,
	standardSource,
	movement,
	setupContext,
);
ScanRunRequest.targeted(configuration, targetedSource);
ScanRunRequest.targetedWithFcx(configuration, targetedSource, setupContext);

declare const event: JsScanRunEvent;
const eventKind:
	| "discovery_completed"
	| "effective_concurrency_selected"
	| "log_queued"
	| "log_started"
	| "log_phase"
	| "log_finished" = event.kind;
void eventKind;

type Execution = Awaited<ReturnType<typeof scanRunExecute>>;
declare const execution: Execution;
if ("result" in execution) {
	execution.result.status;
	execution.result.installedYamlData?.main.sha256;
	execution.result.installedYamlData?.gameFile.provenance;
	const localIgnoreState: JsScanRunLocalIgnoreState | undefined =
		execution.result.installedYamlData?.localIgnoreState;
	void localIgnoreState;
	execution.result.installedYamlData?.localIgnoreIdentity.byteLen;
	execution.result.installedYamlData?.localIgnoreReset?.backupPath;
	const diagnosticKind: JsScanRunInstalledYamlDataDiagnosticKind | undefined =
		execution.result.installedYamlData?.diagnostics[0]?.kind;
	void diagnosticKind;
	// @ts-expect-error A successful envelope cannot also contain an infrastructure error.
	execution.error;
} else {
	execution.error.stage;
	// @ts-expect-error A failed envelope cannot also contain a terminal run result.
	execution.result;
}

const resetRunState: JsScanRunLocalIgnoreState =
	JsScanRunLocalIgnoreState.ResetToDefault;
const resetRunDiagnostic: JsScanRunInstalledYamlDataDiagnosticKind =
	JsScanRunInstalledYamlDataDiagnosticKind.LocalIgnoreReset;
const resetDecision = JsScanRunLocalIgnoreRecoveryDecision.ResetToDefault;
void resetRunState;
void resetRunDiagnostic;
void resetDecision;

// @ts-expect-error Targeted requests deliberately expose no movement capability.
ScanRunRequest.targeted(configuration, targetedSource, movement);
// @ts-expect-error FCX Standard requests require explicit run-scoped setup facts.
ScanRunRequest.standardWithFcx(configuration, standardSource, movement);
// @ts-expect-error FCX Targeted requests require explicit run-scoped setup facts.
ScanRunRequest.targetedWithFcx(configuration, targetedSource);
