import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { JsEnbChecker, JsIniValidator, checkEnb } from "../index.js";

type JsonObject = Record<string, any>;

/** Reject fixture paths escaping the fresh game root. */
function ownedPath(root: string, path: string): string {
  if (!path || path.includes(":") || path.includes("\\") || path.split("/").some(part => ["", ".", ".."].includes(part))) throw new Error("scan game needs a contained relative path");
  return join(root, path);
}

/** Read every durable file and directory, including unexpected native artifacts. */
async function inventory(root: string, prefix = ""): Promise<{ files: JsonObject[]; directories: string[] }> {
  const files: JsonObject[] = [];
  const directories: string[] = [];
  for (const entry of await readdir(join(root, prefix), { withFileTypes: true })) {
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      directories.push(path);
      const children = await inventory(root, path);
      files.push(...children.files); directories.push(...children.directories);
    } else if (entry.isFile()) files.push({ path, content: await readFile(join(root, path), "utf8") });
    else throw new Error("unexpected scan game durable artifact");
  }
  files.sort((left, right) => left.path < right.path ? -1 : left.path > right.path ? 1 : 0);
  directories.sort();
  return { files, directories };
}

/** Observe public Scan Game adapters on controlled fixtures without ambient discovery. */
export async function observeScanGame(fixture: JsonObject): Promise<JsonObject> {
  const operation = fixture.operation;
  if (!["validate-ini", "validate-enb"].includes(operation)) throw new Error("unsupported scan game operation");
  const root = await mkdtemp(join(tmpdir(), "classic-scan-game-conformance-"));
  try {
    for (const path of fixture.directories) await mkdir(ownedPath(root, path), { recursive: true });
    for (const [path, content] of Object.entries(fixture.files)) {
      const target = ownedPath(root, path);
      await mkdir(dirname(target), { recursive: true });
      await writeFile(target, content as string, "utf8");
    }
    const before = await inventory(root);
    let result: JsonObject;
    if (operation === "validate-ini") {
      const validator = new JsIniValidator(fixture.game);
      const report = validator.validateInis(root);
      const issues = validator.detectAllIssues(validator.scanConfigFiles(root)).map(issue => ({ ...issue, filePath: relative(root, issue.filePath).replaceAll("\\", "/") }));
      // Only invocation-specific root spelling is normalized in report text.
      result = { report: report.replaceAll(root, "<ROOT>").replaceAll("\\", "/"), issues };
    } else {
      const checker = new JsEnbChecker(root);
      const value = checker.validate();
      const alias = checkEnb(root);
      if (checker.checkBinaries() !== value.binaries || checker.checkConfig() !== value.config || alias.binaries !== value.binaries || alias.config !== value.config) throw new Error("ENB public entry points disagree");
      result = { binaries: value.binaries, config: value.config };
    }
    const after = await inventory(root);
    return { operation, game: fixture.game, result, beforeFiles: before.files, files: after.files, beforeDirectories: before.directories, directories: after.directories };
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}
