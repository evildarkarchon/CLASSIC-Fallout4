import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Project only native strict-version failures, allowing unrelated errors to fail execution. */
function observe(call: () => boolean): JsonObject {
    try {
        return {hasUpdate: call(), error: null};
    } catch (failure) {
        if (!(failure instanceof Error) || !failure.message.startsWith("Version error:")) throw failure;
        return {hasUpdate: null, error: {code: "invalid_version"}};
    }
}

/** Compare explicit versions through class and free-function bindings without fetching. */
export function observeUpdateDecisions(fixture: JsonObject): JsonObject {
    if (Object.keys(fixture).sort().join() !== "current,latest"
        || typeof fixture.current !== "string" || typeof fixture.latest !== "string") {
        throw new Error("unsupported update decision fixture");
    }
    const client = new classic.GithubClient("conformance", "unused");
    const result = observe(() => client.hasUpdate(fixture.current, fixture.latest));
    const standalone = observe(() => classic.hasUpdate(fixture.current, fixture.latest));
    if (JSON.stringify(result) !== JSON.stringify(standalone)) throw new Error("update binding entrypoints disagree");
    return result;
}
