import {mkdtemp, readdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import * as classic from "../index.js";

/** Validate actual plugin filenames and native metadata using embedded registry fallback. */
export async function observeXsePlugins(fixture: Record<string, any>): Promise<Record<string, any>> {
    const root = await mkdtemp(join(tmpdir(), "classic-xse-plugins-")), previous = process.cwd();
    try {
        for (const [name, content] of Object.entries(fixture.files)) await writeFile(join(root, name), content as string);
        process.chdir(root);
        const info = classic.getAddressLibInfo(fixture.version),
            checker = new classic.JsXseChecker(root, fixture.version);
        const files = async () => Object.fromEntries(await Promise.all((await readdir(root)).map(async name => [name, await readFile(join(root, name), "utf8")])));
        const beforeFiles = await files(), result = checker.check(), message = checker.validate();
        if (classic.checkXsePlugins(root, fixture.version) !== message) throw new Error("XSE convenience validation disagrees with checker");
        return {info, result, message, beforeFiles, files: await files()};
    } finally {
        process.chdir(previous);
        await rm(root, {recursive: true, force: true});
    }
}
