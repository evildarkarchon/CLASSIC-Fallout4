import {mkdir, mkdtemp, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, join} from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** The only log files a fixture may create; the central validator freezes the same set. */
const CONTROLLED_LOG_FILES = new Set([
    "configured-docs/F4SE/f4se.log",
    "configured-docs/F4SE/f4sevr.log",
    "local-docs/F4SE/f4se.log",
    "explicit-xse/f4se.log",
]);

/** Prefix of the Rust `XseLogError::Inspect` message the binding throws for operational failure. */
const INSPECT_FAILURE = "cannot inspect XSE log ";

/**
 * Observe `resolveXseLogForScan` against fixture-owned registry, Local.yaml and logs.
 *
 * Only the `xse-folder.log` capability is bound in Node. The resolver runs with the owned
 * root as cwd so the relative fixture folders (and the registry's first-use load) resolve
 * inside it; the returned log stays root-relative for cross-adapter comparison.
 */
export async function observeXseLog(fixture: JsonObject): Promise<JsonObject> {
    if (Object.keys(fixture).sort().join() !== "configuredDocs,game,localYaml,logFiles,registryYaml,selectedVersion"
        || !["Fallout4", "Fallout4VR"].includes(fixture.game) || typeof fixture.registryYaml !== "string"
        || !Array.isArray(fixture.logFiles) || fixture.logFiles.some((file: unknown) => !CONTROLLED_LOG_FILES.has(file as string))) {
        throw new Error("unsupported XSE log fixture");
    }
    const root = await mkdtemp(join(tmpdir(), "classic-xse-folder-conformance-"));
    const previous = process.cwd();
    try {
        await writeFile(join(root, "CLASSIC Main.yaml"), fixture.registryYaml, "utf8");
        if (fixture.localYaml !== null) {
            await writeFile(join(root, `CLASSIC ${fixture.game} Local.yaml`), fixture.localYaml, "utf8");
        }
        for (const file of fixture.logFiles) {
            await mkdir(dirname(join(root, file)), {recursive: true});
            await writeFile(join(root, file), "");
        }
        // A family has one dedicated serial runner; identical fixture bytes seed the registry
        // OnceLock on first public access without consulting installed metadata.
        process.chdir(root);
        try {
            const log = classic.resolveXseLogForScan(root, fixture.game, fixture.selectedVersion, fixture.configuredDocs || null);
            return {log: log === null ? null : log.replaceAll("\\", "/"), error: null};
        } catch (failure) {
            // Only the typed operational failure is an observation; adapter defects fail execution.
            if (!(failure instanceof Error) || !failure.message.startsWith(INSPECT_FAILURE)) throw failure;
            return {log: null, error: "inspect"};
        }
    } finally {
        process.chdir(previous);
        await rm(root, {recursive: true, force: true});
    }
}
