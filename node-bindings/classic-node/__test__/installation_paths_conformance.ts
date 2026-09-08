import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DocsPathFinder, DocumentsChecker, GamePathFinder } from "../index.js";

type JsonObject = Record<string, any>;

/** Read a complete sorted durable tree, including unexpected native writes. */
async function inventory(root: string, prefix = ""): Promise<{files: JsonObject[], directories: string[]}> {
  const files: JsonObject[] = [];
  const directories: string[] = [];
  for (const entry of await readdir(join(root, prefix), { withFileTypes: true })) {
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      directories.push(path);
      const nested = await inventory(root, path);
      files.push(...nested.files); directories.push(...nested.directories);
    } else if (entry.isFile()) files.push({path, content: await readFile(join(root, path), "utf8")});
    else throw new Error("unexpected installation artifact");
  }
  files.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  return {files, directories: directories.sort()};
}

/** Execute each native public operation on validated owned caches before any OS fallback. */
export async function observeInstallationPaths(fixture: JsonObject): Promise<JsonObject> {
  const game = fixture.gamePath, docs = fixture.docsPath;
  if (!((game === "game" && docs === "docs") || (game === "Game Folder" && docs === "Docs Folder"))) {
    throw new Error("unsupported installation cache paths");
  }
  const root = await mkdtemp(join(tmpdir(), "classic-installation-conformance-"));
  const previous = process.cwd();
  try {
    await mkdir(join(root, game)); await mkdir(join(root, docs));
    await writeFile(join(root, "CLASSIC Main.yaml"), fixture.registryYaml, "utf8");
    if (Object.keys(fixture.files).join() !== `${game}/Fallout4.exe` || fixture.files[`${game}/Fallout4.exe`] !== "owned executable marker") {
      throw new Error("installation fixture needs a valid cached executable");
    }
    await writeFile(join(root, game, "Fallout4.exe"), "owned executable marker");
    // The dedicated receipt process is serial; relative paths exclude host
    // parent names such as OneDrive from the document-checking contract.
    process.chdir(root);
    const gameFinder = new GamePathFinder("Fallout4.exe", null, "Fallout4", false);
    const docsFinder = new DocsPathFinder("My Games/Fallout4");
    gameFinder.validateGamePath(game); docsFinder.validateDocsPath(docs);
    return {gamePath: gameFinder.findGamePath(game, null), docsPath: docsFinder.findDocsPath(docs),
      checks: new DocumentsChecker("Fallout4").runAllChecks(docs), ...await inventory(root)};
  } finally {
    process.chdir(previous);
    await rm(root, { recursive: true, force: true });
  }
}
