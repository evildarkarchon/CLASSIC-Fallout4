import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Observe public native calls with dedicated-process registry cleanup. */
export function observeSharedRegistry(family: string, fixture: JsonObject): JsonObject {
    const request = fixture.request;
    if (family === "string-operations") {
        const values: string[] = request.values;
        return {
            interned: values.map(value => classic.internString(value)),
            normalized: values.map(value => classic.normalizeString(value)),
            batch: classic.processStringBatch(values)
        };
    }
    if (family !== "registry-operations") throw new Error("unsupported shared/registry family");
    // No native object-presence query is exposed to Node. These non-null authored
    // values make registryGet's null miss an exact absence observation.
    classic.registryClear();
    try {
        const initiallyPresent = classic.registryGet("conformance.stringValue") !== null;
        for (const name of ["stringValue", "boolValue", "intValue"]) classic.registrySet(`conformance.${name}`, request[name]);
        const stored = {
            stringValue: classic.registryGet("conformance.stringValue"),
            boolValue: classic.registryGet("conformance.boolValue"),
            intValue: classic.registryGet("conformance.intValue")
        };
        classic.registrySet("conformance.stringValue", request.replacement);
        const replacement = classic.registryGet("conformance.stringValue");
        classic.registrySet("gamevars_version", request.gameVersion);
        const gameVersion = classic.registryGetGameVersion();
        classic.registryRemove("conformance.stringValue");
        const afterRemovePresent = classic.registryGet("conformance.stringValue") !== null;
        classic.registryClear();
        const afterClearPresent = classic.registryGet("conformance.boolValue") !== null || classic.registryGet("conformance.intValue") !== null;
        return {initiallyPresent, stored, replacement, afterRemovePresent, afterClearPresent, gameVersion};
    } finally {
        classic.registryClear();
    }
}
