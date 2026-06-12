import { describe, test, expect } from "bun:test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  applyYamlUpdate,
  // Yaml-update orchestrator
  checkYamlUpdate,
  rollbackYamlUpdate,
  type JsApprovedUpdate,
  type JsYamlApplyRequest,
  // Input / output DTOs
  type JsYamlClientSchemaEntry,
  type JsYamlUpdateStatus,
  type JsYamlRollbackOutcome,
} from "../index.js";

/**
 * Bun smoke tests for the yaml-update-delivery NAPI surface.
 *
 * These tests mirror the CXX bridge's `yaml_check_update_disabled_short_circuits`
 * and `yaml_rollback_update_returns_no_prev_for_unknown_file` round-trips:
 * they prove the NAPI entry points are reachable, correctly typed, and do
 * not perform network I/O in the short-circuit / unknown-file paths.
 *
 * Full happy-path (fetch + download + install) coverage lives in the
 * classic-update-core integration tests (mockito-driven) rather than here,
 * because the download URL allowlist refuses non-github.com hosts.
 */

const MAIN_ENTRY: JsYamlClientSchemaEntry = {
  name: "CLASSIC Main.yaml",
  acceptedMajor: 1,
  acceptedMinimumMinor: 0,
  hasInstalled: false,
  installedMajor: 0,
  installedMinor: 0,
};

describe("yaml-update NAPI surface", () => {
  test("checkYamlUpdate short-circuits to 'disabled' when enabled=false", async () => {
    // The Pages URL is deliberately unroutable (127.0.0.1:1). If the
    // Disabled short-circuit regresses, this test would hang on connect
    // or come back with tag !== 'disabled'.
    const status: JsYamlUpdateStatus = await checkYamlUpdate(
      "http://127.0.0.1:1/manifest-latest.json",
      "yaml-data-v",
      [MAIN_ENTRY],
      /*enabled*/ false,
    );
    expect(status.tag).toBe("disabled");
    expect(status.compatibleFiles.length).toBe(0);
    expect(status.incompatibleFiles.length).toBe(0);
    expect(status.unknownReason).toBe("");
  });

  test("checkYamlUpdate accepts bundledYamlDir override", async () => {
    // Regression for Codex adversarial review finding: Node hosts run
    // inside `node.exe` / `bun.exe`, so the bridge's `current_exe()`
    // fallback cannot locate the bundled YAML root. The NAPI surface
    // MUST accept an explicit `bundledYamlDir` so clean installs whose
    // package-local bytes match the manifest are classified as `upToDate`
    // instead of false-positive `updateAvailable`.
    //
    // This spec only asserts the binding accepts the optional arg
    // without a runtime type error. End-to-end classification behavior
    // is covered by the mockito-driven Rust integration test
    // `check_yaml_update_uses_explicit_bundled_dir_for_clean_install`
    // in `business-logic/classic-update-core/tests/yaml_update_tests.rs`.
    const status: JsYamlUpdateStatus = await checkYamlUpdate(
      "http://127.0.0.1:1/manifest-latest.json",
      "yaml-data-v",
      [MAIN_ENTRY],
      /*enabled*/ false,
      "/nonexistent/path",
    );
    expect(status.tag).toBe("disabled");
  });

  test("applyYamlUpdate accepts a structured request object", async () => {
    const approved: JsApprovedUpdate = {
      releaseTag: "yaml-data-v-test",
      fileNames: ["CLASSIC Main.yaml"],
      fileSha256: ["deadbeef"],
    };
    const request: JsYamlApplyRequest = {
      pagesUrl: "http://127.0.0.1:1/manifest-latest.json",
      tagPrefix: "yaml-data-v",
      entries: [MAIN_ENTRY],
      enabled: false,
      approved,
      bundledYamlDir: "/nonexistent/path",
    };

    await expect(applyYamlUpdate(request)).rejects.toThrow(
      /update check.*disabled/i,
    );
  });

  test("rollbackYamlUpdate returns rolledBack=false for unknown file", () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-yaml-rollback-"));
    const originalLocalAppData = process.env.LOCALAPPDATA;

    try {
      process.env.LOCALAPPDATA = root;

      const outcome: JsYamlRollbackOutcome = rollbackYamlUpdate(
        "__bun_spec_definitely_nonexistent_file_xyzzy__.yaml",
      );
      expect(outcome).toHaveProperty("rolledBack");
      expect(outcome).toHaveProperty("fileName");
      expect(outcome.rolledBack).toBe(false);
    } finally {
      if (originalLocalAppData === undefined) {
        delete process.env.LOCALAPPDATA;
      } else {
        process.env.LOCALAPPDATA = originalLocalAppData;
      }
    }
  });
});
