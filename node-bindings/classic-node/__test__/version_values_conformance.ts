import * as classic from "../index.js";
import {mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";

/** Read public version values from authored inputs, with no installed-game dependency. */
export function observeVersionValues(family: string, fixture: Record<string, any>): Record<string, any> {
    const request = fixture.request;
    if (family === "game-version-parse") {
        try {
            return {parsed: classic.parseGameVersion(request.version)};
        } catch (error) {
            if (!(error instanceof Error) || !error.message.startsWith("Invalid version string:")) throw error;
            return {parsed: null};
        }
    }
    if (family === "game-version-distance") return {distance: classic.gameVersionDistance(request.a, request.b)};
    const root = mkdtempSync(join(tmpdir(), "classic-version-values-"));
    const previous = process.cwd();
    try {
        writeFileSync(join(root, "CLASSIC Main.yaml"), fixture.registryYaml, "utf8");
        // Dedicated receipt processes keep first-use singleton configuration input-owned.
        process.chdir(root);
        const variants = classic.getAllFallout4Versions().map(v => {
            const info = classic.getFallout4VersionInfo(v);
            return {isVr: info.isVr, exeName: info.exeName, steamAppId: info.steamId};
        });
        return {
            variants,
            files: readdirSync(root).sort().map(path => ({path, content: readFileSync(join(root, path), "utf8")}))
        };
    } finally {
        process.chdir(previous);
        rmSync(root, {recursive: true, force: true});
    }
}
