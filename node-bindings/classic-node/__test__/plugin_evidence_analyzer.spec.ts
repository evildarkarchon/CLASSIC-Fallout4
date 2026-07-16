import { describe, expect, test } from "bun:test";
import {
  PluginEvidenceAnalyzer,
  type JsPluginEvidenceAnalysisInput,
} from "../index.js";

const populatedInput: JsPluginEvidenceAnalysisInput = {
  callStack: ["Example.ESP", "example.esp", "modified by: example.esp"],
  plugins: ["Example.ESP", " "],
};

describe("PluginEvidenceAnalyzer", () => {
  test("returns typed plugin identities and occurrence counts", () => {
    const analyzer = new PluginEvidenceAnalyzer([]);

    expect(analyzer.kind as string).toBe("plugin_evidence");
    expect(analyzer.analyze(populatedInput)).toEqual({
      evidence: [{ plugin: "example.esp", occurrences: 2 }],
    });
  });

  test("returns explicit empty results without leaking prior evidence", () => {
    const analyzer = new PluginEvidenceAnalyzer([]);

    expect(analyzer.analyze(populatedInput).evidence).toHaveLength(1);
    expect(analyzer.analyze({ callStack: [], plugins: ["Example.ESP"] })).toEqual({
      evidence: [],
    });
  });

  test("preserves the shared constructor error contract", () => {
    try {
      new PluginEvidenceAnalyzer([" "]);
      throw new Error("expected invalid configuration to fail");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("plugin_evidence");
      expect(analyzerError.code).toBe("invalid_configuration");
      expect(analyzerError.message).toBe(
        "Plugin Evidence ignored plugin must not be empty",
      );
    }
  });
});
