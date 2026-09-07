import * as classic from "../index.js";

/** Translate carrier spelling without maintaining a domain token or label table. */
function pascal(token: string): string {
  return token.replace(/(^|_)([a-z])/g, (_, _separator: string, letter: string) => letter.toUpperCase());
}

const operations = {
  "config-vocabulary": {
    installed_yaml_data_provenance_label: { resolve: classic.installedYamlDataProvenanceLabel, enumInput: true },
    // Node shares the config resolver for provenance carried by scan-run observations.
    scan_run_installed_yaml_data_provenance_label: { resolve: classic.installedYamlDataProvenanceLabel, enumInput: true },
    installed_yaml_data_diagnostic_kind_label: { resolve: classic.installedYamlDataDiagnosticKindLabel, enumInput: true },
    local_ignore_yaml_data_state_label: { resolve: classic.localIgnoreYamlDataStateLabel, enumInput: true },
  },
  "scan-run-vocabulary": {
    scan_run_installed_yaml_data_diagnostic_kind_label: { resolve: classic.scanRunInstalledYamlDataDiagnosticKindLabel, enumInput: true },
    scan_run_local_ignore_yaml_data_state_label: { resolve: classic.scanRunLocalIgnoreYamlDataStateLabel, enumInput: true },
    scan_run_log_disposition_label: { resolve: classic.scanRunLogDispositionLabel, enumInput: false },
    scan_run_log_failure_stage_label: { resolve: classic.scanRunLogFailureStageLabel, enumInput: false },
    scan_run_infrastructure_error_stage_label: { resolve: classic.scanRunInfrastructureErrorStageLabel, enumInput: false },
    scan_run_local_ignore_reset_failure_stage_label: { resolve: classic.scanRunLocalIgnoreResetFailureStageLabel, enumInput: false },
  },
};

/** Observe public label resolution in input order, including native rejection of invalid tokens. */
export function observeVocabulary(family: string, input: Record<string, unknown>): Record<string, unknown> {
  const operation = input.operation;
  const bindings = operations[family as keyof typeof operations];
  if (!bindings || typeof operation !== "string" || !Object.hasOwn(bindings, operation)) {
    throw new Error("unsupported vocabulary operation for family");
  }
  const tokens = input.tokens;
  if (!Array.isArray(tokens) || tokens.some((token) => typeof token !== "string" || !token)) {
    throw new Error("vocabulary tokens must be non-empty strings");
  }
  // Widen only the transport input: invalid enum values must reach NAPI's real decoder.
  const { resolve, enumInput } = (bindings as Record<string, {
    resolve: (token: string) => string; enumInput: boolean;
  }>)[operation];
  return { operation, entries: tokens.map((token: string) => {
    const carrier = enumInput ? pascal(token) : token;
    try {
      return { token, label: resolve(carrier), rejected: false };
    } catch (error) {
      // NAPI enum decoding uses InvalidArg; Rust string-token resolvers use GenericFailure.
      // Adapter defects must fail the scenario instead of becoming token rejection.
      if (!(error instanceof Error) || !("code" in error)
        || !["InvalidArg", "GenericFailure"].includes(String(error.code))) throw error;
      return { token, label: null, rejected: true };
    }
  }) };
}
