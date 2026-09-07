import { mkdir, mkdtemp, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Contain authored filenames before writing scenario inputs. */
function owned(root: string, relative: string): string {
  if (!relative || /[\\:]/.test(relative) || relative.split("/").some(part => !part || part === "." || part === "..")) throw new Error("settings fixture requires a contained relative path");
  return join(root, relative);
}

/** Recognize only attributed public core error prefixes, preserving the failed path. */
function domainError(error: unknown, root: string, paths: string[]): JsonObject {
  const message = error instanceof Error ? error.message : String(error);
  for (const [prefix, kind] of [["Failed to read file ", "io"], ["Failed to parse YAML from ", "yaml-parse"]]) {
    for (const relative of paths) if (message.startsWith(`${prefix}${owned(root, relative)}: `)) return { kind, path: relative };
  }
  throw error;
}

/** Observe all sync/async loaders, cache mutations and exact remaining file bytes. */
export async function observeSettingsLoad(fixture: JsonObject): Promise<JsonObject> {
  const root = await mkdtemp(join(tmpdir(), "classic-settings-conformance-"));
  try {
    for (const [relative, content] of Object.entries(fixture.files)) {
      const path = owned(root, relative); await mkdir(dirname(path), { recursive: true }); await writeFile(path, String(content), "utf8");
    }
    const observed: JsonObject = {};
    for (const operation of ["sync", "async", "batchSync", "batchAsync"]) {
      classic.clearSettingsCache();
      const batch = operation.startsWith("batch");
      const relatives: string[] = batch ? fixture.request.batch : [fixture.request.single];
      const paths = relatives.map(relative => owned(root, relative));
      const keys = batch ? paths : ["conformance.single"];
      let count: number | null = null; let error: JsonObject | null = null;
      try {
        if (operation === "sync") count = classic.loadSettingsSync(keys[0], paths[0]).length;
        else if (operation === "async") count = (await classic.loadSettingsAsync(keys[0], paths[0])).length;
        else if (operation === "batchSync") count = classic.loadBatchSync(paths);
        else count = await classic.loadBatchAsync(paths);
      } catch (failure) { error = domainError(failure, root, relatives); }
      const cached = keys.map(key => classic.isCached(key));
      classic.clearSettingsCache();
      observed[operation] = { count, error, cached, afterClear: keys.map(key => classic.isCached(key)) };
    }
    const files: JsonObject = {};
    for (const relative of await readdir(root, { recursive: true })) {
      const path = join(root, relative);
      const metadata = await stat(path);
      if (metadata.isFile()) files[relative.replace(/\\/g, "/")] = await readFile(path, "utf8");
    }
    return { ...observed, files };
  } finally {
    // A dedicated receipt process owns the cache; cleanup also covers native
    // exceptions so later scenarios cannot inherit stale state or files.
    classic.clearSettingsCache(); await rm(root, { recursive: true, force: true });
  }
}
