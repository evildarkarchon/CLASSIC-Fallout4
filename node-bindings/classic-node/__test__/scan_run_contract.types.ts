import {
	ScanRunRequest,
	ScanRunUnsolvedLogs,
	scanRunExecute,
	JsGameId,
	JsScanRunDisplaySegmentKind,
	JsScanRunDisplaySeverity,
	JsScanRunInstalledYamlDataDiagnosticKind,
	JsScanRunLocalIgnoreRecoveryDecision,
	JsScanRunLocalIgnoreState,
	type JsScanRunConfiguration,
	type JsScanRunDisplayLine,
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

// Display Content is a sibling of the tagged payload, not part of it, so it is
// present on every event kind rather than narrowed away by the discriminant.
const eventDisplayLines: JsScanRunDisplayLine[] = event.displayLines;
void eventDisplayLines;

// A segment is read through its kind tag: the flattening is the C++ bridge's, so
// the fields the kind does not select are empty strings rather than absent, and
// TypeScript types them as required.
declare const segment: JsScanRunDisplayLine["segments"][number];
const segmentKind: JsScanRunDisplaySegmentKind = segment.kind;
const segmentText: string = segment.text;
const segmentPath: string = segment.path;
const segmentCount: number = segment.count;
void segmentKind;
void segmentText;
void segmentPath;
void segmentCount;
const severity: JsScanRunDisplaySeverity = JsScanRunDisplaySeverity.Warning;
void severity;
const countKind: JsScanRunDisplaySegmentKind = JsScanRunDisplaySegmentKind.Count;
void countKind;

type Execution = Awaited<ReturnType<typeof scanRunExecute>>;
declare const execution: Execution;
if ("result" in execution) {
	// Both envelopes carry what the run says. A consumer that only reports the
	// outcome never has to compose a sentence, whichever way the run went.
	const successLines: JsScanRunDisplayLine[] = execution.displayLines;
	void successLines;
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
	const failureLines: JsScanRunDisplayLine[] = execution.displayLines;
	void failureLines;
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
