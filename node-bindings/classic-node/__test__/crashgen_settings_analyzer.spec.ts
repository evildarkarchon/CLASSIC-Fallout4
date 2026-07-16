import { describe, expect, test } from "bun:test";
import {
  CrashgenSettingsAnalyzer,
  type JsCrashgenConfigLayout,
  type JsCrashgenRegistryEntry,
  type JsCrashgenSettingsAnalysisInput,
} from "../index.js";

function registryEntry(version = 1): JsCrashgenRegistryEntry {
  return {
    displaySection: "[Compatibility]",
    ignoreKeys: ["IgnoredSetting"],
    checks: [],
    settingsRulesVersion: version,
    settingsRules: {
      version,
      preflight: [
        {
          id: "compatibility_notice",
          when: { plugin_any: ["MixedCase.DLL"] },
          action: {
            kind: "notice",
            placement: "error_information",
            severity: "warning",
            message: "Compatibility guidance for {crashgen_name}",
            fix: "Compatibility fix",
          },
        },
      ],
      checks: [
        {
          id: "setting_check",
          target: {
            section: "Patches",
            key: "Achievements",
            valueType: "bool",
          },
          when: {},
          expect: { equals: false },
          messages: {
            fail: "Expectation failed",
            fix: "Expectation fix",
          },
          severity: "error",
        },
      ],
    },
  };
}

function populatedInput(): JsCrashgenSettingsAnalysisInput {
  return {
    settings: [
      { section: "Patches", key: "Achievements", value: "true" },
      {
        section: "Compatibility",
        key: "DisabledSetting",
        value: "false",
      },
      {
        section: "Compatibility",
        key: "IgnoredSetting",
        value: "false",
      },
    ],
    installedPlugins: ["MIXEDCASE.DLL"],
    crashgenVersion: { major: 1, minor: 30, patch: 0 },
    configLayout: "og" as JsCrashgenConfigLayout,
  };
}

const emptyInput: JsCrashgenSettingsAnalysisInput = {
  settings: [],
  installedPlugins: [],
  configLayout: "unknown" as JsCrashgenConfigLayout,
};

describe("CrashgenSettingsAnalyzer", () => {
  test("returns exact typed outcomes and separate disabled-setting notices", () => {
    const analyzer = new CrashgenSettingsAnalyzer("Buffout 4", registryEntry());

    const result = analyzer.analyze(populatedInput());

    expect(analyzer.kind as string).toBe("crashgen_settings");
    expect(result as unknown).toEqual({
      expectationOutcomes: [
        {
          ruleId: "compatibility_notice",
          kind: "notice",
          severity: "warning",
          message: "Compatibility guidance for Buffout 4",
          fix: "Compatibility fix",
          placement: "error_information",
        },
        {
          ruleId: "setting_check",
          kind: "issue",
          severity: "error",
          message: "Expectation failed",
          fix: "Expectation fix",
          placement: "settings",
          section: "Patches",
          setting: "Achievements",
          expected: "false",
          actual: "true",
        },
      ],
      disabledSettingNotices: [{ settingName: "DisabledSetting" }],
    });
    expect("lines" in result).toBe(false);
  });

  test("returns an explicit completed-empty result and supports handle reuse", () => {
    const analyzer = new CrashgenSettingsAnalyzer("Buffout 4", registryEntry());

    expect(analyzer.analyze(emptyInput)).toEqual({
      expectationOutcomes: [],
      disabledSettingNotices: [],
    });
    expect(analyzer.analyze(populatedInput()).expectationOutcomes).toHaveLength(2);
    expect(analyzer.analyze(emptyInput)).toEqual({
      expectationOutcomes: [],
      disabledSettingNotices: [],
    });
  });

  test("preserves the core stable constructor error code and human message", () => {
    try {
      new CrashgenSettingsAnalyzer("Buffout 4", registryEntry(2));
      throw new Error("expected unsupported configuration to fail");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("crashgen_settings");
      expect(analyzerError.code).toBe("unsupported_configuration_version");
      expect(analyzerError.message).toBe(
        "unsupported Crashgen Expectations version 2",
      );
    }
  });

  test("rejects malformed rule tokens through shared core validation", () => {
    const entry = registryEntry();
    entry.settingsRules!.checks[0]!.severity = "loud";

    try {
      new CrashgenSettingsAnalyzer("Buffout 4", entry);
      throw new Error("expected malformed configuration to fail");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("crashgen_settings");
      expect(analyzerError.code).toBe("invalid_configuration");
      expect(analyzerError.message).toBe(
        "Crashgen Expectations configuration is invalid: $.checks[0].severity: invalid severity; defaulting to warning",
      );
    }
  });
});
