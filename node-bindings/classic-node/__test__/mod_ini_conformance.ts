import {mkdir, mkdtemp, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, join, relative} from "node:path";
import {detectConfigDuplicates, JsConfigDuplicateDetector, scanModInis} from "../index.js";
import {inventory} from "./file_generation_conformance.js";

/** Project the actual Node ModIniScanner result and all durable input bytes. */
export async function observeModIni(fixture: Record<string, any>): Promise<Record<string, any>> {
    if (!["scan", "duplicates"].includes(fixture.operation)) throw new Error("Node exposes no typed INI cache");
    const root = await mkdtemp(join(tmpdir(), "classic-mod-ini-node-"));
    try {
        for (const [path, content] of Object.entries(fixture.files)) {
            if (path.includes(":") || path.includes("\\") || path.split("/").some(part => ["", ".", ".."].includes(part))) throw new Error("invalid INI fixture path");
            const target = join(root, path);
            await mkdir(dirname(target), {recursive: true});
            await writeFile(target, content as string, "utf8");
        }
        const before = await inventory(root);
        const normalized = (path: string) => relative(root, path).replaceAll("\\", "/");
        if (fixture.operation === "duplicates") {
            const groups = (values: Record<string, any>[]) => values.map(group => ({
                original: normalized(group.original),
                duplicates: group.duplicates.map(normalized).sort()
            })).sort((left, right) => left.original < right.original ? -1 : left.original > right.original ? 1 : 0);
            const mapping = (value: Record<string, string[]>) => Object.fromEntries(Object.entries(value).map(([name, paths]) => [name, paths.map(normalized)]));
            const detector = new JsConfigDuplicateDetector();
            const initialGroups = groups(detector.detectDuplicates(root));
            const initialMap = mapping(detector.getDuplicateMap(root));
            if (JSON.stringify(groups(detectConfigDuplicates(root))) !== JSON.stringify(initialGroups)) throw new Error("duplicate convenience helper changed results");
            if (JsConfigDuplicateDetector.withWhitelist(["no-fixture-matches"]).detectDuplicates(root).length !== 0) throw new Error("custom whitelist was ignored");
            const path = fixture.replacement.path;
            if (path.includes(":") || path.includes("\\") || path.split("/").some((part: string) => ["", ".", ".."].includes(part))) throw new Error("invalid replacement path");
            await writeFile(join(root, path), fixture.replacement.content, "utf8");
            return {
                operation: "duplicates",
                before,
                result: {
                    initialGroups,
                    initialMap,
                    afterGroups: groups(detector.detectDuplicates(root)),
                    afterMap: mapping(detector.getDuplicateMap(root))
                },
                files: await inventory(root)
            };
        }
        const value = scanModInis(root, fixture.game);
        return {
            operation: "scan", before, result: {
                message: value.message.replaceAll(root, "<ROOT>").replaceAll("\\", "/"),
                issues: value.issues.map(issue => ({...issue, filePath: normalized(issue.filePath)})),
                vsync: value.vsyncFiles.map(entry => ({path: normalized(entry.filePath), setting: entry.setting})),
                duplicates: value.duplicates.map(entry => ({
                    name: entry.fileName,
                    paths: entry.paths.map(normalized).sort()
                }))
            }, files: await inventory(root)
        };
    } finally {
        await rm(root, {recursive: true, force: true});
    }
}
