import * as classic from "../index.js";
import { mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, isAbsolute } from "node:path";

/** Check the actual override remains beneath the invocation-owned directory. */
function contained(root: string, value: string | null | undefined): string {
  if (value == null) throw new Error("missing application directory override");
  const path = relative(root, value);
  if (isAbsolute(path) || path === ".." || path.startsWith("..\\") || path.startsWith("../")) throw new Error("registry path escaped workspace");
  return path.replaceAll("\\", "/");
}

/** Observe native registry accessors with cleanup on both success and failure. */
export function observeRegistryAccessors(family: string, fixture: Record<string, any>): Record<string, any> {
  classic.registryClear();
  const root = mkdtempSync(join(tmpdir(), "classic-registry-"));
  try {
    if (family === "registry-game") {
      classic.registrySetGame(fixture.request.game);
      const game = classic.registryGetGame();
      classic.registrySetGame(fixture.request.replacement);
      const replacement = classic.registryGetGame();
      classic.registryClear();
      return { key: "gamevars_game", game, replacement, afterClearPresent: classic.registryGetGame() != null };
    }
    if (family !== "registry-paths") throw new Error("unknown registry accessor family");
    const initial = classic.getApplicationDir() ?? null;
    classic.setApplicationDir(join(root, "first"));
    const path = contained(root, classic.getApplicationDir());
    classic.setApplicationDir(join(root, "second"));
    const replacement = contained(root, classic.getApplicationDir());
    classic.registryClear();
    return { initial, path, replacement, afterClear: classic.getApplicationDir() ?? null, files: readdirSync(root).sort() };
  } finally {
    // Each receipt process owns this registry; reset even after a failed observation.
    classic.registryClear();
    rmSync(root, { recursive: true, force: true });
  }
}
