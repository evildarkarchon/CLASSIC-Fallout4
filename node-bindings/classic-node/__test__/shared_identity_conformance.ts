import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Observe stable public tokens or repeated shared-runtime access diagnostics. */
export function observeSharedIdentity(family: string, fixture: JsonObject): JsonObject {
    if (family === "game-identity") {
        const games = classic.getAllGameIds();
        if (fixture.request.operation === "metadata") return {labels: games.map(game => classic.getGameName(game))};
        return {tokens: games};
    }
    if (family === "runtime-access") {
        const available: boolean[] = [];
        const diagnosticsAvailable: boolean[] = [];
        for (let attempt = 0; attempt < 2; attempt += 1) {
            available.push(classic.isRuntimeAvailable());
            const info = classic.getRuntimeInfo();
            diagnosticsAvailable.push(info.available && info.threadCount > 0);
        }
        return {available, diagnosticsAvailable};
    }
    throw new Error("unsupported shared identity family");
}
