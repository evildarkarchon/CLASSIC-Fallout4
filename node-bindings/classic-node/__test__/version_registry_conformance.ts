import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Observe public metadata and matching against fixture-owned YAML in a dedicated process. */
export async function observeVersionRegistry(fixture: JsonObject): Promise<JsonObject> {
  if (Object.keys(fixture).sort().join() !== "operation,registryYaml,request"
      || !["lookup", "match", "enumerate", "crashgen", "xse", "details"].includes(fixture.operation) || typeof fixture.registryYaml !== "string") {
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
    if (fixture.operation === "details") {
      let byVersion;
      try {
        byVersion = classic.getVersionByVersionString(request.version);
      } catch (failure) {
        if (!(failure instanceof Error) || !failure.message.startsWith("Invalid version string:")) throw failure;
        return { result: null, error: { code: "invalid_version" } };
      }
      const handling = classic.getUnknownVersionHandling();
      return { result: {
        byVersion: byVersion?.id ?? null,
        byShortName: classic.getVersionByShortName(request.shortName)?.id ?? null,
        correctIds: classic.getCorrectVersions(request.isVr).map(info => info.id).sort(),
        wrongIds: classic.getWrongVersions(request.isVr).map(info => info.id).sort(),
        addressLibrary: classic.getAddressLibraryFilename(request.version, request.isVr) ?? null,
        crashgenVersions: classic.getCrashgenVersionStrings(request.id),
        exeHashes: classic.getAllExeHashes(request.game, request.isVr).sort(),
        scriptHashes: classic.getAllScriptHashes(request.game, request.isVr),
        versionScriptHashes: classic.getScriptHashesForVersion(request.id),
        strategy: handling.strategy, logLevel: handling.logLevel,
        defaultId: classic.getUnknownVersionDefault(request.game) ?? null,
        compatible: classic.isVersionCompatible(request.id, request.version),
        snapshotIds: classic.getVersionRegistry(request.game, request.isVr).versions.map(info => info.id),
      }, error: null };
    }
    if (fixture.operation === "enumerate") {
      const ids = classic.getAllVersions().map(info => info.id).sort();
      const filteredIds = classic.getAllVersionsForGame(request.game, request.isVr).map(info => info.id).sort();
      return { result: { ids, count: ids.length, filteredIds }, error: null };
    }
    if (fixture.operation === "crashgen") {
      const configs = classic.getCrashgenVersions(request.id).map(crashgen);
      const selected = classic.getCrashgenForVersion(request.id, request.version);
      return { result: { configs, selected: selected == null ? null : crashgen(selected) }, error: null };
    }
    if (fixture.operation === "xse") {
      const xse = classic.getVersionById(request.id)?.xse;
      return { result: xse == null ? null : { acronym: xse.acronym, fullName: xse.fullName,
        compatibleVersion: xse.compatibleVersion, loader: xse.loader, fileCount: xse.fileCount }, error: null };
    }
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

/** Project the common native configuration fields without recomputing registry decisions. */
function crashgen(config: JsonObject): JsonObject {
  return { version: config.version, name: config.name, acronym: config.acronym,
    dllFile: config.dllFile, description: config.description, downloadUrl: config.downloadUrl };
}
