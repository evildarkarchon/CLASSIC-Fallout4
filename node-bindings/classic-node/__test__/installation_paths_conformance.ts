import { chmod, mkdir, mkdtemp, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DocsPathFinder, DocumentsChecker, GamePathFinder } from "../index.js";
import * as classic from "../index.js";

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
    docsFinder.setSteamAppId(12345);
    gameFinder.validateGamePath(game); docsFinder.validateDocsPath(docs);
    const checker = new DocumentsChecker("Fallout4");
    const checks = checker.runAllChecks(docs);
    if (checker.checkOnedriveInPath(docs) !== null) throw new Error("owned path unexpectedly reports OneDrive");
    ["Fallout4.ini", "Fallout4Custom.ini", "Fallout4Prefs.ini"].forEach((name, index) => {
      const check = checker.validateIniFile(docs, name);
      if (check.exists || check.isValid || !check.hasIssue || check.iniName !== name || check.message !== checks[index]) throw new Error("INI diagnosis disagrees with aggregate check");
    });
    docsFinder.validateIniFiles(docs, []);
    let missingRejected = false;
    try { docsFinder.validateIniFiles(docs, ["Fallout4.ini"]); } catch (error) { if (!(error instanceof Error) || !error.message.includes("Fallout4.ini")) throw error; missingRejected = true; }
    if (!missingRejected) throw new Error("missing required INI was accepted");
    await mkdir("validation/owned/scan", {recursive: true});
    classic.validateCustomScanPath("validation/owned/scan");
    classic.validateSettingsPath(game, "Game Path", ["Fallout4.exe"]);
    classic.validateSettingsPaths(game, docs, "validation/owned/scan", "Fallout4.exe");
    classic.checkDriveExists(root); classic.checkReadPermissions(game); classic.checkWritePermissions(game);
    classic.validatePathWithPermissions(game, true, true);
    if (!classic.isValidPath(game) || classic.isValidPath("missing-path")) throw new Error("path existence alias disagrees with owned tree");
    classic.validateRequiredFiles(game, ["Fallout4.exe"]);
    let requiredRejected = false;
    try { classic.validateRequiredFiles(game, ["missing.ini"]); } catch (error) {
      if (!(error instanceof Error) || !error.message.includes("missing.ini")) throw error;
      requiredRejected = true;
    }
    if (!requiredRejected) throw new Error("required-files alias accepted an absent file");
    const readonlyFile = "validation/owned/scan/readonly.txt";
    await writeFile(readonlyFile, "retained bytes");
    await chmod(readonlyFile, 0o444);
    if (((await stat(readonlyFile)).mode & 0o200) !== 0) throw new Error("readonly precondition was not established");
    classic.removeReadonly(readonlyFile);
    if (((await stat(readonlyFile)).mode & 0o200) === 0 || await readFile(readonlyFile, "utf8") !== "retained bytes") throw new Error("readonly removal changed bytes or failed to restore write access");
    if (classic.isRestrictedPath("validation/owned/scan") || !classic.isRestrictedPath("Windows/System32/test")) throw new Error("restricted-path classification changed");
    if (!classic.isValidExecutablePath(`${game}/Fallout4.exe`) || classic.isValidExecutablePath("CLASSIC Main.yaml")) throw new Error("executable path classification changed");
    await rm("validation", {recursive: true});
    await writeFile("path-detection.log", `plugin directory = "${game}/Data/F4SE/Plugins"\n`);
    if (classic.parseXseLog("path-detection.log") !== game) throw new Error("XSE log path extraction changed game root");
    await rm("path-detection.log");
    return {gamePath: gameFinder.findGamePath(game, null), docsPath: docsFinder.findDocsPath(docs),
      checks, ...await inventory(root)};
  } finally {
    process.chdir(previous);
    await rm(root, { recursive: true, force: true });
  }
}
