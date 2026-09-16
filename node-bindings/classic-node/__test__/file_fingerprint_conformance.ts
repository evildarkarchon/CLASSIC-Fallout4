import * as api from "../index.js";
import {mkdtemp, readdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {basename, join} from "node:path";

/** Inspect actual native hash results and deterministic cache effects. */
export async function observeFileFingerprint(fixture: Record<string, any>): Promise<Record<string, any>> {
    const root = await mkdtemp(join(tmpdir(), "classic-fingerprint-"));
    const target = join(root, "payload.bin");
    /** Select counters; timing and platform cache capacity are not observations. */
    const stats = () => {
        const value = api.getHashCacheStats();
        return {hits: value.hits, misses: value.misses, size: value.size};
    };
    api.clearHashCache();
    api.resetHashCacheStats();
    try {
        if (fixture.bytes !== null) await writeFile(target, Buffer.from(fixture.bytes));
        let hash: string | null = null;
        let error: string | null = null;
        for (let i = 0; i < 2; i++) {
            try {
                hash = api.hashFile(target);
            } catch (failure) {
                if (!(failure instanceof Error) || !failure.message.startsWith("File not found: ")) throw failure;
                error = "not_found";
            }
        }
        const cache = stats();
        const paths = [target, join(root, "absent.bin")];
        const batch = Object.fromEntries(Object.entries(api.hashFilesParallel(paths)).filter(([, value]) => value !== "").map(([path, value]) => [basename(path), value]));
        const map = Object.fromEntries(Object.entries(api.hashFilesParallel(paths)).filter(([, value]) => value !== "").map(([path, value]) => [basename(path), value]));
        api.resetHashCacheStats();
        const reset = stats();
        api.clearHashCache();
        const files = [];
        for (const name of (await readdir(root)).sort()) files.push({
            path: name,
            bytes: [...await readFile(join(root, name))]
        });
        return {
            hash,
            error,
            encoding: fixture.bytes === null ? null : api.detectEncoding(target),
            batch,
            map,
            cache,
            reset,
            cleared: stats(),
            files
        };
    } finally {
        // Cache ownership ends before the temporary path can be reused.
        api.clearHashCache();
        api.resetHashCacheStats();
        await rm(root, {recursive: true, force: true});
    }
}
