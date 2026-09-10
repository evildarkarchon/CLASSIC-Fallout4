import { mkdir, mkdtemp, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Reject escaping fixture paths before creating files in the temporary workspace. */
function owned(root: string, path: string): string {
  if (!path || /[\\:]/.test(path) || path.split("/").some(part => !part || part === "." || part === "..")) {
    throw new Error("fixture path must be a contained relative path");
  }
  return join(root, path);
}

/** Normalize only the scenario root, Windows extended prefixes and separators. */
export function portable(value: string, root: string): string {
  // Native paths may already use forward slashes while the temporary root uses backslashes.
  const normalizedValue = value.replace(/\\/g, "/").replace(/^\/\/\?\//, "");
  const normalizedRoot = root.replace(/\\/g, "/").replace(/^\/\/\?\//, "");
  return normalizedValue.split(`//?/${normalizedRoot}/`).join("").split(`${normalizedRoot}/`).join("");
}

/** Exercise public native bindings and return input-independent observed domain facts. */
export async function observePathMessage(family: string, fixture: JsonObject): Promise<JsonObject> {
  const request = fixture.request;
  if (family === "message-operations") {
    const message = classic.createMessage(request.type, request.content, request.target);
    // Details are a documented plain-object input to the public formatter.
    message.details = request.details ?? undefined;
    return { type: message.messageType, target: message.target, content: message.content,
      title: message.title ?? null, details: message.details ?? null, formatted: classic.formatMessage(message) };
  }
  const temporary = await mkdtemp(join(tmpdir(), "classic-path-conformance-"));
  try {
    // Windows temp paths can use 8.3 aliases; match the spelling native normalization returns.
    const root = await realpath(temporary);
    for (const path of fixture.directories) await mkdir(owned(root, path), { recursive: true });
    for (const [path, content] of Object.entries(fixture.files)) {
      const target = owned(root, path);
      await mkdir(dirname(target), { recursive: true });
      await writeFile(target, content as string, "utf8");
    }
    if (family === "path-operations") {
      const path = owned(root, request.path);
      const exists = classic.isValidPath(path);
      let error: string | null = null;
      try { classic.validateRequiredFiles(path, request.requiredFiles); }
      catch (failure) {
        if (!(failure instanceof Error)) throw failure;
        error = portable(failure.message, root);
      }
      return { path: request.path, exists, requiredFiles: { accepted: error === null, error } };
    }
    if (family === "path-normalization") {
      const joinedPath = classic.joinPaths([owned(root, request.base), ...request.components]);
      const normalizedPath = classic.normalizePath(joinedPath);
      const paths = request.validatePaths.map((path: string) => owned(root, path));
      const validation = classic.validatePathsBatch(paths);
      return { joinedPath: portable(joinedPath, root), normalizedPath: portable(normalizedPath, root),
        validation: paths.map((path: string) => ({ path: portable(path, root), exists: validation[path] })) };
    }
    throw new Error("unsupported path/message family");
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}
