import { describe, expect, test } from "bun:test";
import {
  FormIdFindingAnalyzer,
  JsFormIdValueLookup,
  type JsFormIdFindingAnalysisInput,
} from "../index.js";

const populatedInput: JsFormIdFindingAnalysisInput = {
  crashLines: [
    "Form ID: 0x01123456",
    "Form ID: 0x01123456",
    "Form ID: 0x02ABCDEF",
    "Form ID: 0x03999999",
  ],
  plugins: [
    { name: "Found.esp", prefix: "01" },
    { name: "Missing.esp", prefix: "02" },
  ],
};

describe("FormIdFindingAnalyzer", () => {
  test("returns typed resolved and unresolved findings", async () => {
    const lookup = JsFormIdValueLookup.inMemory([
      {
        formid: "123456",
        plugin: "Found.esp",
        value: "Resolved value",
      },
    ]);
    const analyzer = new FormIdFindingAnalyzer(lookup);

    expect(analyzer.kind as string).toBe("formid_finding");
    expect(await analyzer.analyze(populatedInput)).toEqual({
      findings: [
        {
          identifier: "01123456",
          occurrences: 2,
          plugin: "Found.esp",
          valueLookupStatus: "found",
          value: "Resolved value",
        },
        {
          identifier: "02ABCDEF",
          occurrences: 1,
          plugin: "Missing.esp",
          valueLookupStatus: "missing",
          value: undefined,
        },
        {
          identifier: "03999999",
          occurrences: 1,
          plugin: undefined,
          valueLookupStatus: "not_applicable",
          value: undefined,
        },
      ],
    });
  });

  test("preserves shared typed lookup failures", async () => {
    const lookup = JsFormIdValueLookup.inMemory([
      {
        formid: "123456",
        plugin: "Broken.esp",
        operationalFailure: "fixture offline",
      },
    ]);
    const analyzer = new FormIdFindingAnalyzer(lookup);

    try {
      await analyzer.analyze({
        crashLines: ["Form ID: 0x01123456"],
        plugins: [{ name: "Broken.esp", prefix: "01" }],
      });
      throw new Error("expected lookup failure to reject");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("formid_finding");
      expect(analyzerError.code).toBe("operational_failure");
      expect(analyzerError.message).toContain("fixture offline");
    }
  });
});
