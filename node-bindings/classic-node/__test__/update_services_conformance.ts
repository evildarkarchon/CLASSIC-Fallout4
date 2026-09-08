import * as classic from "../index.js";
import { mkdtempSync, mkdirSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
type JsonObject = Record<string, any>;

/** Execute notification checks with the real native binding and one isolated cache. */
export async function observeUpdateServices(fixture: JsonObject, scenarioId: string): Promise<JsonObject> {
  const service = process.env.CLASSIC_CONFORMANCE_SERVICE;
  if (!service) throw new Error("CLASSIC_CONFORMANCE_SERVICE is required");
  const base = `${service.replace(/\/$/, "")}/${scenarioId}`;
  const config = JSON.stringify({ github_api_base_url: `${base}/api`, notification_pages_url: `${base}/pages`, timeout_ms: fixture.timeoutMs });
  const root = mkdtempSync(join(tmpdir(), "classic-update-"));
  const cache = join(root, "cache");
  mkdirSync(cache);
  try {
    const results: JsonObject[] = [];
    for (let check = 0; check < fixture.checks; check++) {
      try {
        const status = await classic.checkAppNotificationConfigured("conformance", "updates", fixture.installedVersion, config, cache);
        results.push({ status: {
          classification: status.classification.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`),
          latestVersion: status.latestVersion, publishedAt: status.publishedAt,
          minSupportedVersion: status.minSupportedVersion ?? null,
          display: status.display ? { title: status.display.title, body: status.display.body, ctaUrl: status.display.ctaUrl ?? null } : null,
          parseError: status.parseError ?? null,
        }, error: null });
      } catch (error) {
        if (!(error instanceof Error)) throw error;
        let code: string;
        if (error.message.startsWith("FETCH_FAILED:")) code = "fetch_failed";
        else if (error.message.startsWith("DECODE:")) code = "decode";
        else if (error.message.startsWith("INSTALLED_VERSION_PARSE:")) code = "installed_version";
        else if (error.message.startsWith("UPDATE_ERROR: manifest_version ") && error.message.includes(" not supported ")) code = "unsupported_version";
        else throw error;
        results.push({ status: null, error: { code } });
      }
    }
    const files = readdirSync(cache).sort().map(name => ({ path: `cache/${name}`, hex: readFileSync(join(cache, name)).toString("hex") }));
    return { results, files };
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}
