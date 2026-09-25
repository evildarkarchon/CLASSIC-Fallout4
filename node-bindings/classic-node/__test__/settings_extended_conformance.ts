import * as classic from "../index.js";
import {mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {join, relative} from "node:path";

/** Observe actual cached document payloads before loading and after disk changes/invalidation. */
export function observeSettingsExtended(_family: string, fixture: Record<string, any>): Record<string, any> {
    const root = mkdtempSync(join(tmpdir(), "classic-cached-docs-"));
    const path = join(root, "input.yaml");
    const key = "conformance.cached-docs";
    classic.clearSettingsCache();
    try {
        const before = classic.getCached(key) ?? null;
        writeFileSync(path, fixture.content, "utf8");
        classic.loadSettingsSync(key, path);
        const cached = classic.getCached(key) ?? null;
        writeFileSync(path, fixture.replacement, "utf8");
        const afterFileChange = classic.getCached(key) ?? null;
        classic.invalidateSettings(key);
        const afterInvalidate = classic.getCached(key) ?? null;
        // Inventory after the last public read to expose forbidden stale writeback.
        const files: Record<string, string> = {};
        inventory(root, root, files);
        return {before, cached, afterFileChange, afterInvalidate, files};
    } finally {
        classic.clearSettingsCache();
        rmSync(root, {recursive: true, force: true});
    }
}

/** Capture every remaining file recursively without normalizing its contents. */
function inventory(root: string, directory: string, files: Record<string, string>): void {
    for (const name of readdirSync(directory)) {
        const path = join(directory, name);
        if (statSync(path).isDirectory()) inventory(root, path, files);
        else files[relative(root, path).replace(/\\/g, "/")] = readFileSync(path, "utf8");
    }
}
