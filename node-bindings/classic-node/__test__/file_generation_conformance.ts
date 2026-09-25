import {mkdir, mkdtemp, readdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, join} from "node:path";
import {generateIgnoreFile, generateLocalYaml, JsFileGenerator} from "../index.js";

/** Re-read every durable generated file instead of trusting returned creation flags. */
export async function inventory(root: string, prefix = ""): Promise<Record<string, string>[]> {
    const result: Record<string, string>[] = [];
    for (const entry of await readdir(join(root, prefix), {withFileTypes: true})) {
        const path = prefix ? `${prefix}/${entry.name}` : entry.name;
        if (entry.isDirectory()) result.push(...await inventory(root, path));
        else if (entry.isFile()) result.push({path, content: await readFile(join(root, path), "utf8")});
        else throw new Error("unexpected generated filesystem artifact");
    }
    return result.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
}

/** Await native relative-path writes before restoring this serial receipt process's cwd. */
export async function observeFileGeneration(fixture: Record<string, any>): Promise<Record<string, any>> {
    if (!["Fallout4", "Fallout4VR"].includes(fixture.game)) throw new Error("invalid generator fixture game");
    const root = await mkdtemp(join(tmpdir(), "classic-generation-node-"));
    const previous = process.cwd();
    try {
        for (const [path, content] of Object.entries(fixture.files)) {
            if (path.includes(":") || path.includes("\\") || path.split("/").some(part => ["", ".", ".."].includes(part))) throw new Error("invalid generation path");
            const target = join(root, path);
            await mkdir(dirname(target), {recursive: true});
            await writeFile(target, content as string, "utf8");
        }
        // This executable owns its process cwd and awaits every spawned native write.
        process.chdir(root);
        const generator = new JsFileGenerator(fixture.ignore, fixture.local, fixture.game);
        const result: Record<string, any> = {
            paths: [generator.ignoreFilePath().replaceAll("\\", "/"), generator.localYamlPath().replaceAll("\\", "/")],
            before: await inventory(root)
        };
        result.generated = await Promise.all([generateIgnoreFile(fixture.ignore), generateLocalYaml(fixture.local, fixture.game)]);
        result.existing = [await generateIgnoreFile(fixture.ignore), await generateLocalYaml(fixture.local, fixture.game)];
        result.standalone = [await generateIgnoreFile("must not replace"), await generateLocalYaml("must not replace", fixture.game)];
        result.files = await inventory(root);
        return result;
    } finally {
        process.chdir(previous);
        await rm(root, {recursive: true, force: true});
    }
}
