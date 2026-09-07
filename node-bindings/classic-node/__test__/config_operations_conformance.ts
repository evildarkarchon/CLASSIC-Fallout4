import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Re-read every durable file, retaining exact UTF-8 bytes and portable paths. */
async function inventory(root: string, directory = root): Promise<JsonObject[]> {
  const result: JsonObject[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error("unexpected link in config workspace");
    if (entry.isDirectory()) result.push(...await inventory(root, path));
    else result.push({ path: relative(root, path).split(sep).join("/"), content: await readFile(path, "utf8") });
  }
  return result.sort((a, b) => a.path.localeCompare(b.path));
}

/** Invoke the public explicit loader, retaining structured failures and all durable effects. */
export async function observeConfigOperations(fixture: JsonObject): Promise<JsonObject> {
  if (fixture.operation !== "load-explicit" || Object.keys(fixture).sort().join() !== "files,operation") {
    throw new Error("unsupported config operation fixture");
  }
  const root = await mkdtemp(join(tmpdir(), "classic-config-conformance-"));
  try {
    for (const [name, content] of Object.entries(fixture.files)) {
      if (!["main.yaml", "game.yaml", "ignore.yaml"].includes(name) || typeof content !== "string") {
        throw new Error("config fixture requires owned YAML filenames and UTF-8 text");
      }
      await writeFile(join(root, name), content, "utf8");
    }
    let result: JsonObject | null = null;
    let error: JsonObject | null = null;
    let snapshot: classic.ExplicitYamlDataSnapshot | undefined;
    try {
      snapshot = await classic.loadExplicitYamlData(
        { mainPath: join(root, "main.yaml"), gamePath: join(root, "game.yaml"), ignorePath: join(root, "ignore.yaml") },
        classic.JsGameId.Fallout4,
        "auto",
      );
    } catch (failure: any) {
      // Reject infrastructure failures instead of manufacturing a domain observation.
      if (!["read", "parse", "invalid_utf8", "invalid_role_data", "unsupported_game"].includes(failure.code)) throw failure;
      error = { code: failure.code, role: failure.yamlRole ?? null, path: failure.path == null ? null : relative(root, failure.path).split(sep).join("/") };
    }
    if (snapshot !== undefined) {
      const data = snapshot.yamlData;
      result = { classicVersion: data.classicVersion, xseAcronym: data.xseAcronym, crashgenName: data.crashgenName, gameVersion: data.gameVersion, ignoreList: data.ignoreList };
    }
    return { result, error, files: await inventory(root) };
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}
