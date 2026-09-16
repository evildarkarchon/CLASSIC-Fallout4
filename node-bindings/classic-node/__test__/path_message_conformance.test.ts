import {expect, test} from "bun:test";
import {readFileSync} from "node:fs";
import {mkdtemp, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {resolve} from "node:path";
import {observePathMessage, portable} from "./path_message_conformance";

test("portable removes Windows scenario roots across separator and extended-prefix variants", () => {
    for (const root of ["C:\\temp\\scenario", "C:/temp/scenario", "\\\\?\\C:\\temp\\scenario"]) {
        for (const path of ["C:\\temp\\scenario\\game\\Fallout4.exe", "C:/temp/scenario/game/Fallout4.exe",
            "\\\\?\\C:\\temp\\scenario\\game\\Fallout4.exe", "//?/C:/temp/scenario/game/Fallout4.exe"]) {
            expect(portable(path, root)).toBe("game/Fallout4.exe");
        }
    }
});

const repositoryRoot = resolve(import.meta.dir, "../../..");

test.skipIf(process.platform !== "win32")("path observations strip roots reached through a Windows directory alias", async () => {
    const directory = await mkdtemp(resolve(tmpdir(), "Classic-Mixed-Case-"));
    const originalTemp = process.env.TEMP;
    const originalTmp = process.env.TMP;
    try {
        // Existing paths canonicalize the alias, while missing paths retain its spelling.
        process.env.TEMP = directory.toUpperCase();
        process.env.TMP = directory.toUpperCase();
        const pack = JSON.parse(readFileSync(resolve(repositoryRoot, "tests/conformance/packs/path_normalization/v1.json"), "utf8"));
        for (const scenario of pack.scenarios) {
            const fixture = JSON.parse(readFileSync(resolve(repositoryRoot, pack.fixtureRoot, pack.fixtures[scenario.id]), "utf8"));
            expect(await observePathMessage(pack.familyId, fixture)).toEqual(scenario.expected);
        }
    } finally {
        if (originalTemp === undefined) delete process.env.TEMP;
        else process.env.TEMP = originalTemp;
        if (originalTmp === undefined) delete process.env.TMP;
        else process.env.TMP = originalTmp;
        await rm(directory, {recursive: true, force: true});
    }
});

for (const family of ["path_normalization", "path_operations"]) {
    const pack = JSON.parse(readFileSync(resolve(repositoryRoot, `tests/conformance/packs/${family}/v1.json`), "utf8"));
    for (const scenario of pack.scenarios) {
        test(`${family}: ${scenario.id}`, async () => {
            const fixture = JSON.parse(readFileSync(resolve(repositoryRoot, pack.fixtureRoot, pack.fixtures[scenario.id]), "utf8"));
            expect(await observePathMessage(pack.familyId, fixture)).toEqual(scenario.expected);
        });
    }
}

test("portable removes scenario roots within error messages without altering unrelated roots", () => {
    expect(portable("Missing \\\\?\\C:\\temp\\scenario\\game", "\\\\?\\C:\\temp\\scenario"))
        .toBe("Missing game");
    expect(portable("Missing C:/temp/scenario/game/a and C:\\temp\\scenario\\game\\b", "C:\\temp\\scenario"))
        .toBe("Missing game/a and game/b");
    expect(portable("C:\\temp\\scenario-other\\game\\a", "C:\\temp\\scenario"))
        .toBe("C:/temp/scenario-other/game/a");
    expect(portable("/tmp/scenario/game/a", "/tmp/scenario")).toBe("game/a");
});
