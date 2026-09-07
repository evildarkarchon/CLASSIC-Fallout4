import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Observe public metadata and matching against fixture-owned YAML in a dedicated process. */
export async function observeVersionRegistry(fixture: JsonObject): Promise<JsonObject> {
  if (Object.keys(fixture).sort().join() !== "operation,registryYaml,request"
      || !["lookup", "match"].includes(fixture.operation) || typeof fixture.registryYaml !== "string") {
    throw new Error("unsupported version registry fixture");
  }
  const root = await mkdtemp(join(tmpdir(), "classic-version-registry-conformance-"));
  const previous = process.cwd();
  try {
    await writeFile(join(root, "CLASSIC Main.yaml"), fixture.registryYaml, "utf8");
    // A family has one dedicated serial runner; identical fixture bytes seed OnceLock
    // on first public access without consulting the user's installed metadata.
    process.chdir(root);
    const observation = observe(fixture);
    const files: JsonObject[] = [];
    for (const entry of await readdir(root, { withFileTypes: true })) {
      if (!entry.isFile()) throw new Error("unexpected non-file in version registry workspace");
      files.push({ path: entry.name, content: await readFile(join(root, entry.name), "utf8") });
    }
    return { ...observation, files: files.sort((a, b) => a.path.localeCompare(b.path)) };
  } finally {
    process.chdir(previous);
    await rm(root, { recursive: true, force: true });
  }
}

/** Convert native success/error carriers without inferring domain results from inputs. */
function observe(fixture: JsonObject): JsonObject {
    const request = fixture.request;
    if (fixture.operation === "lookup") {
      const info = classic.getVersionById(request.id);
      const result = info == null ? null : {
        id: info.id, version: info.version, shortName: info.shortName,
        game: info.game, docsName: info.docsName, steamId: info.steamId, isVr: info.isVr,
      };
      return { result, error: null };
    }
    try {
      const matched = classic.matchVersion(request.version, request.game, request.isVr);
      return { result: { matchedId: matched.versionInfo?.id ?? null, confidence: matched.confidence, message: matched.message }, error: null };
    } catch (failure: any) {
      // Only the native version parser's documented error earns domain-error credit.
      if (!(failure instanceof Error) || !failure.message.startsWith("Invalid version string:")) throw failure;
      return { result: null, error: { code: "invalid_version" } };
    }
}
