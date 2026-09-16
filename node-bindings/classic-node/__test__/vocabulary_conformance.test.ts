import {expect, test} from "bun:test";
import {mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import * as classic from "../index.js";
import {observeVocabulary} from "./vocabulary_conformance.js";

test("vocabulary transport resolves PascalCase enum carriers and preserves mixed outcomes", () => {
    expect(observeVocabulary("config-vocabulary", {
        operation: "installed_yaml_data_provenance_label", tokens: ["updated", "not_a_real_token", "bundled"],
    })).toEqual({
        operation: "installed_yaml_data_provenance_label",
        entries: [
            {
                token: "updated",
                label: classic.installedYamlDataProvenanceLabel(classic.JsInstalledYamlDataProvenance.Updated),
                rejected: false
            },
            {token: "not_a_real_token", label: null, rejected: true},
            {
                token: "bundled",
                label: classic.installedYamlDataProvenanceLabel(classic.JsInstalledYamlDataProvenance.Bundled),
                rejected: false
            },
        ],
    });
    expect(observeVocabulary("scan-run-vocabulary", {
        operation: "scan_run_local_ignore_yaml_data_state_label", tokens: ["proceed_without_ignore"],
    })).toEqual({
        operation: "scan_run_local_ignore_yaml_data_state_label",
        entries: [{
            token: "proceed_without_ignore",
            label: classic.scanRunLocalIgnoreYamlDataStateLabel(classic.JsScanRunLocalIgnoreState.ProceedWithoutIgnore),
            rejected: false
        }],
    });
});

test("vocabulary transport invokes native string-token rejection", () => {
    expect(observeVocabulary("scan-run-vocabulary", {
        operation: "scan_run_log_disposition_label", tokens: ["not_a_real_token"],
    })).toEqual({
        operation: "scan_run_log_disposition_label",
        entries: [{token: "not_a_real_token", label: null, rejected: true}],
    });
});

test("vocabulary transport rejects carrier defects before native resolution", () => {
    expect(() => observeVocabulary("config-vocabulary", {
        operation: "scan_run_log_disposition_label", tokens: ["not_a_real_token"],
    })).toThrow("unsupported vocabulary operation for family");
    expect(() => observeVocabulary("config-vocabulary", {
        operation: "installed_yaml_data_provenance_label", tokens: [null],
    })).toThrow("vocabulary tokens must be non-empty strings");
});

test("vocabulary runner preserves unknown-token rejection without fixtures", async () => {
    const root = await mkdtemp(join(tmpdir(), "classic-vocabulary-"));
    try {
        const planPath = join(root, "plan.json");
        const outputPath = join(root, "receipt.json");
        await writeFile(planPath, JSON.stringify({
            schemaVersion: 1, familyId: "config-vocabulary", familyVersion: 1,
            expectationDigest: "transport-test", fixtures: {},
            participant: {id: "node", role: "semantic-adapter", executionInstanceId: "node"},
            invocation: {id: "transport-test", sourceIdentity: "transport-test", runPlanDigest: "transport-test"},
            scenarios: [{
                id: "unknown", capabilityIds: [], fixtureRefs: [], action: "vocabulary.resolve",
                input: {
                    operation: "installed_yaml_data_provenance_label",
                    tokens: ["not_a_real_token", "not_a_real_token"]
                }
            }],
        }));
        const process = Bun.spawn(["bun", "__test__/semantic_conformance_runner.ts"], {
            cwd: join(import.meta.dir, ".."),
            env: {...Bun.env, CLASSIC_CONFORMANCE_RUN_PLAN: planPath, CLASSIC_CONFORMANCE_OUTPUT: outputPath},
            stdout: "pipe", stderr: "pipe",
        });
        expect(await process.exited).toBe(0);
        const receipt = JSON.parse(await readFile(outputPath, "utf8"));
        expect(receipt.scenarios[0].executionStatus).toBe("completed");
        expect(receipt.scenarios[0].observation).toEqual({
            operation: "installed_yaml_data_provenance_label",
            entries: [
                {token: "not_a_real_token", label: null, rejected: true},
                {token: "not_a_real_token", label: null, rejected: true},
            ],
        });
    } finally {
        await rm(root, {recursive: true, force: true});
    }
});
