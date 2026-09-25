import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import * as classic from "../index.js";

/** Compare read-only native lookups to .NET registry values, retaining only agreement booleans. */
export function observeWindowsPlatformPaths(fixture: Record<string, any>): Record<string, boolean> {
    if (process.platform !== "win32") throw new Error("Windows platform conformance requires Windows");
    const oraclePath = fileURLToPath(new URL("../../../tools/binding_compliance/platform_path_oracle.ps1", import.meta.url));
    const child = spawnSync("pwsh", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", oraclePath], {encoding: "utf8"});
    if (child.status !== 0) throw new Error("Read-only Windows reference lookup failed");
    let oracle: { documents: string | null; missingKeyAbsent: boolean };
    try {
        oracle = JSON.parse(child.stdout);
    } catch {
        // Never echo a malformed oracle response: it may contain the personal documents path.
        throw new Error("Read-only Windows reference returned invalid JSON");
    }
    return {
        documentsAgree: (classic.getSystemDocumentsPath() ?? null) === oracle.documents,
        registryMissing: oracle.missingKeyAbsent && classic.queryGameRegistry(fixture.registryGame, "", false) == null,
        steamUnavailable: classic.parseSteamLibrary(fixture.steamId) == null,
    };
}
