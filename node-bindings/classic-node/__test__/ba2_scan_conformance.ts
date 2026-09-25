import {mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, relative} from "node:path";
import {JsBa2Scanner, scanAllBa2Archives} from "../index.js";

/** Project native archive issue vectors without interpreting the input archive bytes. */
function issues(value: Record<string, any>): Record<string, any> {
    return {dimensions: value.texDims, formats: value.texFrmt, sounds: value.sndFrmt, scripts: value.xseFile};
}

/** Execute default/custom scanner construction, direct reads, discovery and batch convenience. */
export async function observeBa2Scan(fixture: Record<string, any>): Promise<Record<string, any>> {
    if (fixture.operation !== "full") throw new Error("Node uses the full BA2 surface");
    const root = await mkdtemp(join(tmpdir(), "classic-ba2-node-"));
    const path = join(root, "fixture.ba2");
    try {
        await writeFile(path, Buffer.from(fixture.bytes));
        const scanner = new JsBa2Scanner();
        const result = issues(scanner.scanArchive(path));
        const custom = issues(JsBa2Scanner.withXsePatterns([]).scanArchive(path));
        if (JSON.stringify(custom) !== JSON.stringify({
            ...result,
            scripts: []
        })) throw new Error("custom XSE patterns changed unrelated BA2 issue vectors");
        const normalized = (path: string) => relative(root, path).replaceAll("\\", "/");
        return {
            issues: result,
            found: scanner.findBa2Files(root).map(normalized).sort(),
            batch: scanAllBa2Archives(root).map(value => [normalized(value.path), issues(value.issues)]),
            bytes: Array.from(await readFile(path))
        };
    } finally {
        await rm(root, {recursive: true, force: true});
    }
}
