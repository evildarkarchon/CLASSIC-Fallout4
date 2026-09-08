import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { JsFileIO, calculateFileSimilarity, calculateTextSimilarity } from "../index.js";

type JsonObject = Record<string, any>;

/** Reject nonportable fixture paths before performing any native operation. */
function ownedPath(root: string, path: string): string {
  if (!path || path.includes(":") || path.includes("\\") || path.split("/").some(part => ["", ".", ".."].includes(part))) {
    throw new Error("file operation needs a contained relative path");
  }
  return join(root, path);
}

/** Re-read the complete sorted durable inventory, including unexpected native writes. */
async function files(root: string, prefix = ""): Promise<JsonObject[]> {
  const result: JsonObject[] = [];
  for (const entry of await readdir(join(root, prefix), { withFileTypes: true })) {
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) result.push(...await files(root, path));
    else if (entry.isFile()) result.push({ path, content: await readFile(join(root, path), "utf8") });
    else throw new Error("unexpected non-file durable artifact");
  }
  return result.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
}

/** Execute public native text I/O and keep its errors separate from harness failures. */
export async function observeFileOperations(fixture: JsonObject): Promise<JsonObject> {
  const operation = fixture.operation;
  if (!["read-text", "write-text"].includes(operation)) throw new Error("unsupported file operation");
  const root = await mkdtemp(join(tmpdir(), "classic-file-conformance-"));
  try {
    const target = ownedPath(root, fixture.path);
    for (const [path, content] of Object.entries(fixture.files)) {
      const destination = ownedPath(root, path);
      await mkdir(dirname(destination), { recursive: true });
      await writeFile(destination, content as string, "utf8");
    }
    const result: JsonObject = { operation, path: fixture.path, content: null, error: null, beforeFiles: await files(root), files: [] };
    const io = new JsFileIO();
    try {
      if (operation === "read-text") result.content = await io.readFile(target);
      else await io.writeFile(target, fixture.content);
    } catch (error) {
      // N-API preserves the Rust error category in its prefix, followed by platform prose.
      if (!(error instanceof Error) || !error.message.startsWith("I/O error: ")) throw error;
      result.error = "io_error";
    }
    result.files = await files(root);
    if (operation === "read-text") result.similarity = await similarityObservation();
    return result;
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

/** Compare native file and text APIs without allowing either to mutate source bytes. */
async function similarityObservation(): Promise<string[]> {
  const root = await mkdtemp(join(tmpdir(), "classic-similarity-"));
  try {
    const left = join(root, "left.txt"), right = join(root, "right.txt");
    const first = "alpha\nbeta\n";
    await writeFile(left, first);
    const results = [];
    for (const second of [first, "gamma\ndelta\n", "alpha\ngamma\n"]) {
      await writeFile(right, second);
      const result = calculateFileSimilarity(left, right);
      if (calculateTextSimilarity(first, second) !== result) throw new Error("text similarity disagrees with native file similarity");
      if (await readFile(left, "utf8") !== first || await readFile(right, "utf8") !== second) throw new Error("similarity changed source bytes");
      results.push(result.toFixed(6));
    }
    return results;
  } finally { await rm(root, {recursive: true, force: true}); }
}
