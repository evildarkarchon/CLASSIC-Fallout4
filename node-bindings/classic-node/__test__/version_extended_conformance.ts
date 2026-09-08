import * as classic from "../index.js";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";

/** Execute public version operations and transport the documented CXX PE failure loss. */
export function observeVersionExtended(fixture: Record<string, any>): Record<string, any> {
  const request = fixture.request;
  if (request.operation === "extract") return { filename: classic.extractVersionFromFilename(request.filename), log: classic.extractVersionFromLog(request.content), all: classic.extractAllVersions(request.content) };
  if (request.operation === "known-fallout4") return { "known-fallout4": classic.isKnownFallout4Version(request.version) };
  const root = mkdtempSync(join(tmpdir(), "classic-version-conformance-"));
  /** Prevent authored paths from escaping the disposable workspace. */
  const owned = (path: string): string => {
    if (!path || /[\\:]/.test(path) || path.split("/").some(part => ["", ".", ".."].includes(part))) throw new Error("invalid version fixture path");
    return join(root, path);
  };
  try {
    for (const [path, content] of Object.entries(fixture.files)) {
      const target = owned(path); mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, Buffer.from(content as string, "hex"));
    }
    const target = owned(request.path);
    if (request.operation === "pe-path") return { validPath: classic.isValidPePath(target) };
    try {
      const value = classic.extractPeVersion(target);
      return { peVersion: `${value.major}.${value.minor}.${value.patch}.${value.build}` };
    } catch (error) {
      // CXX discards these public domain errors; this common fact claims no error classification.
      if (!(error instanceof Error) || !/^(Invalid executable path:|Not a valid PE file:|No version information found in PE file:|Failed to read PE file)/.test(error.message)) throw error;
      return { peVersion: "" };
    }
  } finally { rmSync(root, { recursive: true, force: true }); }
}
