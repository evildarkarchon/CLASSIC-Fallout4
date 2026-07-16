import { describe, expect, test } from "bun:test";
import {
  ModGuidanceAnalyzer,
  type JsImportantModRule,
  type JsModConflictRule,
  type JsModGuidanceAnalysisInput,
  type JsModSolutionRule,
} from "../index.js";

const conflicts: JsModConflictRule[] = [
  {
    modA: "alpha",
    modB: "beta",
    nameA: "Alpha Mod",
    nameB: "Beta Mod",
    description: "Authored conflict description",
    fix: "Install the compatibility patch",
    link: "https://example.invalid/patch",
  },
];

const frequentCrashes: JsModSolutionRule[] = [
  {
    id: "frequent",
    criteriaKind: "any",
    criteria: ["frequent.esp"],
    exceptions: [],
    name: "Frequent Crash Mod",
    description: "Authored frequent-crash guidance",
  },
];

const solutions: JsModSolutionRule[] = [
  {
    id: "solution",
    criteriaKind: "all",
    criteria: ["solution.esp", "dependency.esm"],
    exceptions: [],
    name: "Solution Mod",
    description: "Authored solution guidance",
  },
];

const importantMods: JsImportantModRule[] = [
  {
    detect: "installed.dll",
    name: "Installed Important Mod",
    description: "Installed authored description",
  },
  {
    detect: "missing.dll",
    name: "Missing Important Mod",
    description: "Missing authored description\nwith a second line",
    gpu: "amd",
  },
  {
    detect: "rival.dll",
    name: "Rival GPU Mod",
    description: "Rival authored description",
    gpu: "nvidia",
    gpuMismatchWarning: "Authored mismatch warning\nkeep this line",
  },
];

const populatedInput: JsModGuidanceAnalysisInput = {
  plugins: [
    { name: "Alpha.esp", id: "02" },
    { name: "Beta.esp", id: "03" },
    { name: "Frequent.esp", id: "04" },
    { name: "Solution.esp", id: "05" },
    { name: "Dependency.esm", id: "06" },
  ],
  userGpu: "amd",
  xseModules: ["Installed.dll", "Rival.dll"],
};

describe("ModGuidanceAnalyzer", () => {
  test("returns all semantic families with authored fields and stable states", () => {
    const analyzer = new ModGuidanceAnalyzer(
      conflicts,
      frequentCrashes,
      solutions,
      importantMods,
    );

    const result = analyzer.analyze(populatedInput);

    expect(analyzer.kind as string).toBe("mod_guidance");
    expect(result).toEqual({
      conflicts: [
        {
          state: "matched",
          modA: "alpha",
          modB: "beta",
          nameA: "Alpha Mod",
          nameB: "Beta Mod",
          description: "Authored conflict description",
          fix: "Install the compatibility patch",
          link: "https://example.invalid/patch",
        },
      ],
      frequentCrashes: [
        {
          state: "matched",
          id: "frequent",
          name: "Frequent Crash Mod",
          description: "Authored frequent-crash guidance",
          matchedPluginIds: ["04"],
        },
      ],
      solutions: [
        {
          state: "matched",
          id: "solution",
          name: "Solution Mod",
          description: "Authored solution guidance",
          matchedPluginIds: ["05", "06"],
        },
      ],
      importantMods: [
        {
          state: "matched",
          detect: "installed.dll",
          name: "Installed Important Mod",
          description: "Installed authored description",
        },
        {
          state: "missing",
          detect: "missing.dll",
          name: "Missing Important Mod",
          description: "Missing authored description\nwith a second line",
          gpu: "amd",
        },
        {
          state: "gpu_mismatch",
          detect: "rival.dll",
          name: "Rival GPU Mod",
          description: "Rival authored description",
          gpu: "nvidia",
          gpuMismatchWarning: "Authored mismatch warning\nkeep this line",
        },
      ],
    });
    expect("lines" in result).toBe(false);
  });

  test("returns explicit empty results without leaking prior findings", () => {
    const analyzer = new ModGuidanceAnalyzer(
      conflicts,
      frequentCrashes,
      solutions,
      importantMods,
    );

    expect(analyzer.analyze(populatedInput).conflicts).toHaveLength(1);
    expect(
      analyzer.analyze({ plugins: [], xseModules: [] }),
    ).toEqual({
      conflicts: [],
      frequentCrashes: [],
      solutions: [],
      importantMods: [],
    });
  });

  test("preserves the shared constructor error contract", () => {
    try {
      new ModGuidanceAnalyzer(
        [{ ...conflicts[0]!, modA: "" }],
        frequentCrashes,
        solutions,
        importantMods,
      );
      throw new Error("expected invalid configuration to fail");
    } catch (error) {
      const analyzerError = error as Error & {
        analyzerKind?: string;
        code?: string;
      };
      expect(analyzerError.analyzerKind).toBe("mod_guidance");
      expect(analyzerError.code).toBe("invalid_configuration");
      expect(analyzerError.message).toBe(
        "Mod Guidance conflict mod_a must not be empty",
      );
    }
  });
});
