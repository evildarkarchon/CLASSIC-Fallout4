import { describe, expect, test } from "bun:test";
import {
  CrashSuspectAnalyzer,
  type JsCrashSuspectAnalysisInput,
  type JsCrashSuspectMainErrorRule,
  type JsCrashSuspectStackRule,
} from "../index.js";

const mainErrorRules: JsCrashSuspectMainErrorRule[] = [
  {
    id: "main-rule",
    name: "Main Rule",
    severity: 5,
    mainErrorContainsAny: ["plugin.dll"],
  },
];

const stackRules: JsCrashSuspectStackRule[] = [
  {
    id: "stack-rule",
    name: "Stack Rule",
    severity: 4,
    mainErrorRequiredAny: [],
    mainErrorOptionalAny: [],
    stackContainsAny: ["StackSignal"],
    excludeIfStackContainsAny: [],
    stackContainsAtLeast: [],
  },
];

const populatedInput: JsCrashSuspectAnalysisInput = {
  mainError: "plugin.dll",
  callStack: "StackSignal",
};

describe("CrashSuspectAnalyzer", () => {
  test("returns one typed finding for each rule and DLL notice", () => {
    const analyzer = new CrashSuspectAnalyzer(mainErrorRules, stackRules);

    const result = analyzer.analyze(populatedInput);

    expect(analyzer.kind as string).toBe("crash_suspect");
    expect(result).toEqual({
      findings: [
        {
          kind: "main_error_rule",
          ruleId: "main-rule",
          name: "Main Rule",
          severity: 5,
        },
        {
          kind: "stack_rule",
          ruleId: "stack-rule",
          name: "Stack Rule",
          severity: 4,
        },
        { kind: "dll_involvement" },
      ],
    });
    expect("lines" in result).toBe(false);
  });

  test("returns explicit empty results without leaking prior findings", () => {
    const analyzer = new CrashSuspectAnalyzer(mainErrorRules, stackRules);

    expect(analyzer.analyze(populatedInput).findings).toHaveLength(3);
    expect(
      analyzer.analyze({ mainError: "", callStack: "" }),
    ).toEqual({ findings: [] });
  });

  test("preserves the shared constructor error contract", () => {
    try {
      new CrashSuspectAnalyzer(
        [{ ...mainErrorRules[0]!, id: "" }],
        stackRules,
      );
      throw new Error("expected invalid configuration to fail");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("crash_suspect");
      expect(analyzerError.code).toBe("invalid_configuration");
      expect(analyzerError.message).toBe(
        "Crash Suspect main-error rule id must not be empty",
      );
    }
  });
});
