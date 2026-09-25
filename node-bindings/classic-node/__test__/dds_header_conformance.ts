import {mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {basename, join} from "node:path";
import {JsDdsAnalyzer} from "../index.js";

/** Observe the native DDS analyzer, batch filtering and dimension fallback results. */
export async function observeDdsHeader(fixture: Record<string, any>): Promise<Record<string, any>> {
    if (fixture.operation !== "validate") throw new Error("Node has no DDSHeader parsing class");
    const root = await mkdtemp(join(tmpdir(), "classic-dds-node-"));
    const path = join(root, "texture.dds");
    try {
        await writeFile(path, Buffer.from(fixture.bytes));
        const analyzer = new JsDdsAnalyzer("Fallout4");
        return {
            issues: analyzer.validateFile(path).map(issue => issue.message),
            batch: analyzer.validateBatch([path, join(root, "missing.dds")]).map(entry => [basename(entry.path), entry.issues.map(issue => issue.message)]),
            dimensionIssues: JsDdsAnalyzer.validateDimensions(fixture.dimensions[0], fixture.dimensions[1]).map(issue => issue.message),
            bytes: Array.from(await readFile(path))
        };
    } finally {
        await rm(root, {recursive: true, force: true});
    }
}
