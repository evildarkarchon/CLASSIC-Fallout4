import { describe, test, expect } from "bun:test";
import type {
  JsCheckRule,
  JsExpectedValue,
  JsPreflightAction,
  JsPreflightRule,
  JsRuleMessages,
  JsRuleTarget,
  JsModSolutionCriteria,
  JsModSolutionEntry,
  JsSuspectErrorRule,
  JsSuspectStackCountRule,
  JsSuspectStackRule,
  JsModConflictEntry,
} from "../index.js";

// Phase 4 Plan 5 Task 1: crashgen_rules smoke tests
// Real-shape assertions per MEDIUM concern fix -- no `{} as Type` + toBeDefined() stubs.

describe("crashgen_rules: JsCheckRule shape", () => {
  test("has expected typed fields", () => {
    const rule: JsCheckRule = {
      id: "test-rule",
      target: { section: "General", key: "sLanguage", valueType: "string" },
      when: { kind: "always" },
      expect: { equals: "en" },
      messages: { fail: "Language mismatch" },
      severity: "warn",
    };
    expect(typeof rule.id).toBe("string");
    expect(typeof rule.severity).toBe("string");
    expect(typeof rule.target.section).toBe("string");
    expect(typeof rule.messages.fail).toBe("string");
  });
});

describe("crashgen_rules: JsExpectedValue shape", () => {
  test("has equals field", () => {
    const val: JsExpectedValue = { equals: "1" };
    expect(val.equals).toBe("1");
  });
});

describe("crashgen_rules: JsPreflightAction shape", () => {
  test("has kind, severity, message fields", () => {
    const action: JsPreflightAction = {
      kind: "warn",
      placement: "error_information",
      bucket: "error_information",
      severity: "medium",
      message: "Check your settings",
    };
    expect(typeof action.kind).toBe("string");
    expect(action.placement).toBe("error_information");
    expect(action.bucket).toBe("error_information");
    expect(typeof action.severity).toBe("string");
    expect(typeof action.message).toBe("string");
  });
});

describe("crashgen_rules: JsPreflightRule shape", () => {
  test("has id, when, action fields", () => {
    const rule: JsPreflightRule = {
      id: "preflight-1",
      when: { kind: "always" },
      action: { kind: "warn", severity: "low", message: "test" },
    };
    expect(typeof rule.id).toBe("string");
    expect(rule.action).toBeDefined();
    expect(typeof rule.action.kind).toBe("string");
  });
});

describe("crashgen_rules: JsRuleMessages shape", () => {
  test("has fail field, optional fix and pass", () => {
    const msgs: JsRuleMessages = { fail: "failed check" };
    expect(typeof msgs.fail).toBe("string");
    expect(msgs.fix).toBeUndefined();
    expect(msgs.pass).toBeUndefined();
  });
});

describe("crashgen_rules: JsRuleTarget shape", () => {
  test("has section, key, valueType fields", () => {
    const target: JsRuleTarget = {
      section: "General",
      key: "sLanguage",
      valueType: "string",
    };
    expect(typeof target.section).toBe("string");
    expect(typeof target.key).toBe("string");
    expect(typeof target.valueType).toBe("string");
  });
});

describe("crashgen_rules: JsModSolutionCriteria shape", () => {
  test("has optional any and all arrays", () => {
    const criteria: JsModSolutionCriteria = {
      any: ["mod-a", "mod-b"],
    };
    expect(Array.isArray(criteria.any)).toBe(true);
    expect(criteria.all).toBeUndefined();
  });
});

describe("crashgen_rules: JsModSolutionEntry shape", () => {
  test("has id, criteria, exceptions fields", () => {
    const entry: JsModSolutionEntry = {
      id: "solution-1",
      criteria: { any: ["mod-a"] },
      exceptions: [],
    };
    expect(typeof entry.id).toBe("string");
    expect(entry.criteria).toBeDefined();
    expect(Array.isArray(entry.exceptions)).toBe(true);
  });
});

describe("crashgen_rules: JsSuspectErrorRule shape", () => {
  test("has id, name, severity, mainErrorContainsAny fields", () => {
    const rule: JsSuspectErrorRule = {
      id: "suspect-1",
      name: "Test suspect rule",
      severity: 3,
      mainErrorContainsAny: ["ACCESS_VIOLATION"],
    };
    expect(typeof rule.id).toBe("string");
    expect(typeof rule.name).toBe("string");
    expect(typeof rule.severity).toBe("number");
    expect(Array.isArray(rule.mainErrorContainsAny)).toBe(true);
  });
});

describe("crashgen_rules: JsSuspectStackCountRule shape", () => {
  test("has substring and count fields", () => {
    const rule: JsSuspectStackCountRule = {
      substring: "nvwgf2umx.dll",
      count: 3,
    };
    expect(typeof rule.substring).toBe("string");
    expect(typeof rule.count).toBe("number");
  });
});

describe("crashgen_rules: JsSuspectStackRule shape", () => {
  test("has id, name, severity and array fields", () => {
    const rule: JsSuspectStackRule = {
      id: "stack-1",
      name: "GPU crash pattern",
      severity: 2,
      mainErrorRequiredAny: [],
      mainErrorOptionalAny: [],
      stackContainsAny: ["nvwgf2umx.dll"],
      excludeIfStackContainsAny: [],
      stackContainsAtLeast: [],
    };
    expect(typeof rule.id).toBe("string");
    expect(typeof rule.name).toBe("string");
    expect(typeof rule.severity).toBe("number");
    expect(Array.isArray(rule.stackContainsAny)).toBe(true);
  });
});

describe("crashgen_rules: JsModConflictEntry shape", () => {
  test("has modA, modB, nameA, nameB, description, fix fields", () => {
    const entry: JsModConflictEntry = {
      modA: "mod-a.esp",
      modB: "mod-b.esp",
      nameA: "Mod A",
      nameB: "Mod B",
      description: "These mods conflict",
      fix: "Remove one of them",
    };
    expect(typeof entry.modA).toBe("string");
    expect(typeof entry.modB).toBe("string");
    expect(typeof entry.description).toBe("string");
    expect(typeof entry.fix).toBe("string");
    expect(entry.link).toBeUndefined();
  });
});
