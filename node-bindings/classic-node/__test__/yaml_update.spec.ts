import { describe, test, expect } from "bun:test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  applyYamlDataUpdateWithDecision,
  // First-party YAML Data Update Channel
  checkYamlDataUpdate,
  rollbackYamlDataUpdate,
  rollbackYamlUpdate,
  type JsApprovedUpdate,
  // Input / output DTOs
  type JsYamlUpdateStatus,
  type JsYamlRollbackOutcome,
  type JsYamlRollbackTargetOutcome,
} from "../index.js";

/**
 * Bun smoke tests for the yaml-update-delivery NAPI surface.
 *
 * These tests mirror the CXX bridge's `yaml_check_update_disabled_short_circuits`
 * and `yaml_rollback_update_returns_no_prev_for_unknown_file` round-trips:
 * they prove the NAPI entry points are reachable, correctly typed, and do
 * not perform network I/O in the short-circuit / unknown-file paths.
 *
 * The binding intentionally exposes no generic `checkYamlUpdate` /
 * `applyYamlUpdate` variant taking caller-supplied channel coordinates and
 * schema entries: an adapter able to declare its own accepted ranges could
 * classify — and then install — under a policy `classic-config-core` does not
 * own. Rust therefore owns the Pages URL, the `yaml-data-v` tag namespace, and
 * the accepted schema ranges, and these tests drive the first-party API only.
 *
 * Full happy-path (fetch + download + install) coverage lives in the
 * classic-update-core integration tests (mockito-driven) rather than here,
 * because the download URL allowlist refuses non-github.com hosts and the
 * first-party entry points do not accept a mock Pages endpoint.
 */

describe("yaml-update NAPI surface", () => {
  test("checkYamlDataUpdate short-circuits to 'disabled' when enabled=false", async () => {
    // Core returns Disabled before resolving the installation root or opening
    // any socket. If that short-circuit regresses, this test would hit the
    // network (or throw on root resolution) instead of returning 'disabled'.
    const status: JsYamlUpdateStatus = await checkYamlDataUpdate(
      /*enabled*/ false,
    );
    expect(status.tag).toBe("disabled");
    expect(status.compatibleFiles.length).toBe(0);
    expect(status.incompatibleFiles.length).toBe(0);
    expect(status.unknownReason).toBe("");
  });

  test("checkYamlDataUpdate accepts installationRoot override", async () => {
    // Regression for Codex adversarial review finding: Node hosts run
    // inside `node.exe` / `bun.exe`, so the bridge's `current_exe()`
    // fallback cannot locate the installed YAML root. The NAPI surface
    // MUST accept an explicit `installationRoot` so clean installs whose
    // package-local bytes match the manifest are classified as `upToDate`
    // instead of false-positive `updateAvailable`.
    //
    // This spec only asserts the binding accepts the optional arg
    // without a runtime type error. End-to-end classification behavior
    // is covered by the mockito-driven Rust integration tests in
    // `business-logic/classic-update-core/tests/yaml_update_tests.rs`.
    const status: JsYamlUpdateStatus = await checkYamlDataUpdate(
      /*enabled*/ false,
      "/nonexistent/path",
    );
    expect(status.tag).toBe("disabled");
  });

  test("applyYamlDataUpdateWithDecision refuses when the update check is disabled", async () => {
    const approved: JsApprovedUpdate = {
      releaseTag: "yaml-data-v-test",
      fileNames: ["CLASSIC Main.yaml"],
      fileSha256: ["deadbeef"],
    };

    await expect(
      applyYamlDataUpdateWithDecision(
        /*enabled*/ false,
        approved,
        "/nonexistent/path",
      ),
    ).rejects.toThrow(/update check is disabled/i);
  });

  test("rollbackYamlDataUpdate reports one outcome per first-party target", async () => {
    const root = mkdtempSync(join(tmpdir(), "classic-node-yaml-data-rollback-"));
    const originalLocalAppData = process.env.LOCALAPPDATA;

    try {
      // An empty cache root means no target has a `.prev` sibling, so every
      // target should come back as a non-error `rolledBack: false`.
      process.env.LOCALAPPDATA = root;

      const outcomes: JsYamlRollbackTargetOutcome[] =
        await rollbackYamlDataUpdate();

      // Rust expands the target list, so the caller never names files; the
      // list is derived from shippable schema metadata and is never empty.
      expect(outcomes.length).toBeGreaterThan(0);

      for (const target of outcomes) {
        expect(typeof target.fileName).toBe("string");
        expect(target.fileName.length).toBeGreaterThan(0);
        expect(target.outcome).toHaveProperty("rolledBack");
        expect(target.outcome).toHaveProperty("fileName");
        expect(target.outcome.rolledBack).toBe(false);
        // A per-target failure is reported as data, not a rejection. With an
        // empty cache root there is nothing to fail on, so errorMessage is
        // absent for every target.
        expect(target.errorMessage ?? null).toBeNull();
      }
    } finally {
      if (originalLocalAppData === undefined) {
        delete process.env.LOCALAPPDATA;
      } else {
        process.env.LOCALAPPDATA = originalLocalAppData;
      }
    }
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
