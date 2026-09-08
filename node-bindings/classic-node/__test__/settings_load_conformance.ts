import { mkdir, mkdtemp, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { dirname, join, relative } from "node:path";
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
  if (fixture.kind === "yaml-batch") return observeSettingsYamlBatch(fixture);
  if (fixture.kind === "yaml-batch") return observeSettingsYamlBatch(fixture);
  if (fixture.kind === "yaml") return observeSettingsYaml(fixture);
  const root = await mkdtemp(join(tmpdir(), "classic-settings-conformance-"));
  try {
    for (const [relative, content] of Object.entries(fixture.files)) {
      const path = owned(root, relative); await mkdir(dirname(path), { recursive: true }); await writeFile(path, String(content), "utf8");
    }
    classic.resetSettingsCacheStats();
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
      const cacheState = {
        keys: classic.settingsCacheKeys().map(key => batch ? relative(root, key).replace(/\\/g, "/") : key).sort(),
        size: classic.settingsCacheSize(), stats: cacheStatistics(),
        invalidated: keys.map(key => classic.invalidateSettings(key)),
        invalidatedAgain: keys.map(key => classic.invalidateSettings(key)),
        afterInvalidate: classic.settingsCacheSize(), resetStats: {} as JsonObject,
      };
      classic.resetSettingsCacheStats(); cacheState.resetStats = cacheStatistics();
      // Refill entries so clear is checked independently of invalidation.
      keys.forEach((key, index) => { if (cached[index]) classic.loadSettingsSync(key, paths[index]); });
      classic.clearSettingsCache();
      observed[operation] = { count, error, cached, cacheState, afterClear: keys.map(key => classic.isCached(key)) };
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

/** Retain counters and bounded storage without platform-specific capacity. */
function cacheStatistics(): JsonObject {
  const stats = classic.getSettingsCacheStats();
  return { hits: stats.hits, misses: stats.misses, hitRateZero: stats.hit_rate === 0, size: stats.size, bounded: stats.capacity > 0 };
}

/** Execute YAML parsing, typed access, mutation, persistence and cache reuse. */
async function observeSettingsYaml(fixture: JsonObject): Promise<JsonObject> {
  const root = await mkdtemp(join(tmpdir(), "classic-yaml-conformance-"));
  classic.yamlClearCache();
  try {
    const parsed = classic.yamlParse(fixture.content);
    const before = { name: classic.yamlGetStringValue(fixture.content, "name", "fallback"), missing: classic.yamlGetStringValue(fixture.content, "absent", "fallback"), items: classic.yamlGetVecValue(fixture.content, "items"), mapping: classic.yamlGetHashmapValue(fixture.content, "mapping") };
    let content = classic.yamlStringify(parsed);
    for (const key of fixture.updateOrder) content = classic.yamlSetSetting(content, key, fixture.updates[key]);
    const after = Object.fromEntries(Object.keys(fixture.updates).map(key => [key, classic.yamlGetValue(content, key)]));
    const path = join(root, "saved.yaml");
    classic.yamlSaveFile(path, classic.yamlParse(content));
    const initial = classic.yamlGetCacheStats();
    const loaded = classic.yamlLoadFile(path); classic.yamlLoadFile(path);
    const stats = classic.yamlGetCacheStats();
    const persisted = Object.fromEntries(Object.keys(fixture.updates).map(key => [key, classic.yamlGetValue(classic.yamlStringify(loaded), key)]));
    const files: JsonObject = {};
    for (const entry of await readdir(root)) {
      const file = join(root, entry);
      if ((await stat(file)).isFile()) files[entry] = await readFile(file, "utf8");
    }
    classic.yamlClearCache();
    return { before, after, persisted, files, cache: { hits: stats.hits - initial.hits, misses: stats.misses - initial.misses, size: stats.size, afterClear: classic.yamlGetCacheStats().size } };
  } finally {
    // File and cache ownership belongs to this scenario even when a native call fails.
    classic.yamlClearCache(); await rm(root, { recursive: true, force: true });
  }
}

/** Preserve ordered map entries and typed batch results across actual native calls. */
function observeSettingsYamlBatch(fixture: JsonObject): JsonObject {
  const before = classic.yamlGetSettingsBatch(fixture.content, fixture.keys);
  const ordered = Object.entries(classic.yamlGetIndexmapValue(fixture.content, "mapping"));
  const vectors = classic.yamlGetHashmapVecValue(fixture.content, "vectors");
  const updated = classic.yamlSetSettingsBatch(fixture.content, fixture.updates);
  return { before, ordered, vectors, after: classic.yamlGetSettingsBatch(updated, fixture.keys) };
}

/** Preserve ordered map entries and typed batch results across actual native calls. */
function observeSettingsYamlBatch(fixture: JsonObject): JsonObject {
  const before = classic.yamlGetSettingsBatch(fixture.content, fixture.keys);
  const ordered = Object.entries(classic.yamlGetIndexmapValue(fixture.content, "mapping"));
  const vectors = classic.yamlGetHashmapVecValue(fixture.content, "vectors");
  const updated = classic.yamlSetSettingsBatch(fixture.content, fixture.updates);
  return { before, ordered, vectors, after: classic.yamlGetSettingsBatch(updated, fixture.keys) };
}
