import * as classic from "../index";

/** Exercise original default helpers using a synthetic header that reqwest rejects before transport. */
export async function observeUpdateRejection(fixture: Record<string, any>): Promise<Record<string, any>> {
    if (fixture.operation !== "latest" || fixture.token !== "synthetic\ninvalid") throw new Error("Unsupported rejection fixture");
    const previous = process.env.GITHUB_TOKEN;
    process.env.GITHUB_TOKEN = fixture.token;
    try {
        for (const invoke of [
            () => classic.getLatestRelease(fixture.owner, fixture.repo),
            () => classic.checkForUpdates(fixture.owner, fixture.repo, fixture.currentVersion),
        ]) {
            let rejected = false;
            try {
                await invoke();
            } catch (error) {
                if (!(error instanceof Error) || error.message !== "HTTP error: builder error") throw error;
                rejected = true;
            }
            if (!rejected) throw new Error("Malformed authorization header was accepted");
        }
        return {boundary: "request-builder", error: "builder-error", requestBuilt: false};
    } finally {
        // Keep synthetic credentials scoped until both asynchronous client calls finish.
        if (previous === undefined) delete process.env.GITHUB_TOKEN;
        else process.env.GITHUB_TOKEN = previous;
    }
}
