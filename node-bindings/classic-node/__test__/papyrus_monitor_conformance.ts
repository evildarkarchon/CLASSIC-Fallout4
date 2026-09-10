import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { analyzePapyrusLog } from "../index.js";

/** Observe the public Node full-file API; monitoring methods are not exported by Node. */
export async function observePapyrusMonitor(fixture: Record<string, any>): Promise<Record<string, any>> {
  if (fixture.operation !== "full") throw new Error("Node Papyrus supports only full analysis");
  const root = await mkdtemp(join(tmpdir(), "classic-papyrus-node-"));
  const path = join(root, "Papyrus.0.log");
  try {
    if (fixture.content !== null) await writeFile(path, fixture.content, "utf8");
    try {
      const value = analyzePapyrusLog(path);
      return { stats: { dumps: value.dumps, stacks: value.stacks, warnings: value.warnings,
                       errors: value.errors, lines: value.linesProcessed }, error: null,
               content: await readFile(path, "utf8") };
    } catch (error) {
      if (!(error instanceof Error) || !error.message.startsWith("Papyrus log file not found at: ")) throw error;
      return { stats: null, error: "missing", content: null };
    }
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}
