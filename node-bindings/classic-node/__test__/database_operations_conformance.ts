import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Read all durable SQLite and sidecar bytes after native handles close. */
async function databaseFiles(root: string, directory = root): Promise<JsonObject[]> {
  const files: JsonObject[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error("unexpected link in database workspace");
    if (entry.isDirectory()) files.push(...await databaseFiles(root, path));
    else files.push({ path: relative(root, path).split(sep).join("/"), hex: (await readFile(path)).toString("hex") });
  }
  return files.sort((a, b) => a.path.localeCompare(b.path));
}

/** Traverse the public pool, retaining empty hits, ordered misses, and native open failures. */
export async function observeDatabaseOperations(fixture: JsonObject): Promise<JsonObject> {
  if (Object.keys(fixture).sort().join() !== "databaseHex,operation,queries" || fixture.operation !== "pool") throw new Error("unsupported database operation fixture");
  if (!Array.isArray(fixture.queries) || fixture.queries.some((pair: any) => !Array.isArray(pair) || pair.length !== 2 || pair.some((value: any) => typeof value !== "string"))) throw new Error("database queries require string pairs");
  const root = await mkdtemp(join(tmpdir(), "classic-database-conformance-"));
  try {
    if (fixture.databaseHex !== null) {
      if (typeof fixture.databaseHex !== "string" || !/^(?:[0-9a-f]{2})*$/.test(fixture.databaseHex)) throw new Error("database bytes require lowercase hex");
      await writeFile(join(root, "formids.db"), Buffer.from(fixture.databaseHex, "hex"));
    }
    const pool = new classic.JsDatabasePool("Fallout4", 1, 300);
    const result: JsonObject = { table: pool.getGameTable(), initialAvailable: pool.isAvailable(), error: null, single: [], batch: [] };
    try {
      try { await pool.initialize([join(root, "formids.db")]); }
      catch (failure: any) {
        // The binding exposes a string carrier; validate its domain and attributed path.
        if (!(failure instanceof Error) || !failure.message.startsWith("Failed to open database:") || !failure.message.includes(JSON.stringify(join(root, "formids.db")).slice(1, -1))) throw failure;
        result.error = { code: "open", path: "formids.db" };
      }
      result.available = pool.isAvailable();
      if (result.error === null) {
        for (const [formid, plugin] of fixture.queries) result.single.push((await pool.getEntry(formid, plugin)) ?? null);
        const batch = await pool.getEntriesBatch(fixture.queries);
        result.batch = fixture.queries.map(([formid, plugin]: string[]) => batch[`${formid}:${plugin}`] ?? null);
      }
      result.cleared = pool.clearCache(false);
      result.afterClear = pool.clearCache(false);
    } finally {
      // Native handles must be released before Windows workspace cleanup.
      await pool.close();
    }
    result.closedAvailable = pool.isAvailable();
    result.closedCache = pool.clearCache(false);
    return { ...result, files: await databaseFiles(root) };
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}
