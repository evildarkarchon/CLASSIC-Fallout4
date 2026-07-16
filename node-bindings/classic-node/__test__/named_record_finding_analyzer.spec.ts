import { describe, expect, test } from "bun:test";
import {
  NamedRecordFindingAnalyzer,
  type JsNamedRecordFindingAnalysisInput,
} from "../index.js";

const populatedInput: JsNamedRecordFindingAnalysisInput = {
  crashLines: ["ActorBase_Player", "ActorBase_System", "ActorBase_Player"],
};

describe("NamedRecordFindingAnalyzer", () => {
  test("returns distinct typed records and occurrence counts", () => {
    const analyzer = new NamedRecordFindingAnalyzer(["ActorBase"], ["System"]);

    expect(analyzer.kind as string).toBe("named_record_finding");
    expect(analyzer.analyze(populatedInput)).toEqual({
      findings: [{ record: "ActorBase_Player", occurrences: 2 }],
    });
  });

  test("returns explicit empty results without leaking prior findings", () => {
    const analyzer = new NamedRecordFindingAnalyzer(["ActorBase"], ["System"]);

    expect(analyzer.analyze(populatedInput).findings).toHaveLength(1);
    expect(analyzer.analyze({ crashLines: ["unrelated"] })).toEqual({
      findings: [],
    });
  });

  test("preserves the shared constructor error contract", () => {
    try {
      new NamedRecordFindingAnalyzer([" "], []);
      throw new Error("expected invalid configuration to fail");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("named_record_finding");
      expect(analyzerError.code).toBe("invalid_configuration");
      expect(analyzerError.message).toBe(
        "Named Record Finding target record must not be empty",
      );
    }
  });
});
