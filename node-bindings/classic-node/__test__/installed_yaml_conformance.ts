import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import * as classic from "../index.js";

type JsonObject = Record<string, any>;
const cacheEnvironment = ["LOCALAPPDATA", "APPDATA", "XDG_CACHE_HOME", "HOME"];
const ignorePath = "installation/CLASSIC Data/CLASSIC Ignore.yaml";

/** Normalize binding enum spelling while retaining the underlying machine token. */
function token(value: string | null | undefined): string | null {
  return value == null ? null : value.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
}

/** Reject fixture paths that escape the disposable scenario workspace. */
function ownedPath(root: string, path: string): string {
  const target = resolve(root, path);
  const local = relative(root, target);
  if (isAbsolute(path) || !local || local === ".." || local.startsWith(`..${sep}`) || isAbsolute(local)) {
    throw new Error(`fixture path is outside its workspace: ${path}`);
  }
  return target;
}

/** Reduce native absolute paths to portable scenario-relative attribution. */
function pathCarrier(root: string, path: string | null | undefined): string | null {
  if (path == null) return null;
  const local = relative(root, path).split(sep).join("/");
  ownedPath(root, local);
  return local;
}

/** Install only explicit input bytes; never read expected results or host YAML data. */
async function materialize(root: string, files: Record<string, string>): Promise<void> {
  for (const [path, content] of Object.entries(files)) {
    if (typeof content !== "string") throw new Error("fixture file content must be UTF-8 text");
    const target = ownedPath(root, path);
    await mkdir(dirname(target), { recursive: true });
    await writeFile(target, content, "utf8");
  }
}

/** Project identities from public DTOs, preserving their exact native hashes and lengths. */
function identity(value: { sha256: string; byteLen?: number; byteLength?: number }, path: string): JsonObject {
  return { path, sha256: value.sha256, byteLength: value.byteLength ?? value.byteLen };
}

/** Attribute selected-file identities using the public role and source provenance. */
function selectedFile(value: classic.JsInspectedYamlDataFile): JsonObject {
  const role = token(value.role);
  const provenance = token(value.provenance);
  const name = role === "main" ? "CLASSIC Main.yaml" : "CLASSIC Fallout4.yaml";
  const path = provenance === "bundled" ? `installation/CLASSIC Data/databases/${name}`
    : `cache/CLASSIC/yaml-cache/${name}${provenance === "previous" ? ".prev" : ""}`;
  return { role, provenance, schemaVersion: `${value.schemaMajor}.${value.schemaMinor}`, identity: identity(value, path) };
}

/** Retain ordered structured diagnostics independently of platform-dependent prose. */
function diagnostics(root: string, values: classic.JsInstalledYamlDataDiagnostic[]): JsonObject[] {
  return values.map((item) => ({
    role: token(item.role), candidate: token(item.candidate), path: pathCarrier(root, item.path), kind: token(item.kind),
  }));
}

/** Re-read all durable regular files after the operation and any explicit mutation. */
async function fileTree(root: string, directory = root): Promise<JsonObject[]> {
  const result: JsonObject[] = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) result.push(...await fileTree(root, path));
    else if (entry.isFile()) {
      const bytes = await readFile(path);
      result.push({ path: pathCarrier(root, path), sha256: createHash("sha256").update(bytes).digest("hex"), byteLength: bytes.length });
    } else throw new Error("unexpected non-regular filesystem entry in scenario workspace");
  }
  return result.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
}

/** Observe installed-data APIs in an isolated root, restoring process environment on failure. */
export async function observeInstalledYaml(fixture: JsonObject): Promise<JsonObject> {
  const root = await mkdtemp(join(tmpdir(), "classic-node-installed-conformance-"));
  const previous = new Map(cacheEnvironment.map((name) => [name, process.env[name]]));
  try {
    await mkdir(join(root, "installation"), { recursive: true });
    await materialize(root, fixture.files);
    // These APIs resolve the process environment, so cases run sequentially and own every fallback.
    for (const name of cacheEnvironment) process.env[name] = join(root, "cache");
    const games: Record<string, classic.JsGameId> = {
      Fallout4: classic.JsGameId.Fallout4, Fallout4VR: classic.JsGameId.Fallout4Vr,
      Skyrim: classic.JsGameId.Skyrim, Starfield: classic.JsGameId.Starfield,
    };
    if (!(fixture.game in games)) throw new Error("unsupported fixture game");
    const request = { installationRoot: join(root, "installation"), game: games[fixture.game], selectedGameVersion: fixture.selectedGameVersion };
    const observation: JsonObject = { outcome: "error", game: null, gameDataRole: null, main: null, gameFile: null,
      localIgnore: null, recovery: null, snapshot: null, diagnostics: [], error: null, files: [] };
    let selected: classic.JsInstalledYamlDataInspection | classic.InstalledYamlDataSnapshot | classic.LocalIgnoreRecoveryPlan | undefined;
    let snapshot: classic.InstalledYamlDataSnapshot | undefined;
    let recovery: classic.LocalIgnoreRecoveryPlan | undefined;
    try {
      if (fixture.operation === "inspect") {
        selected = await classic.inspectInstalledYamlData(request);
        observation.outcome = "inspected";
      } else if (fixture.operation === "load") {
        const outcome = await classic.loadInstalledYamlData(request);
        if (outcome.status === classic.JsInstalledYamlDataLoadStatus.Ready && outcome.snapshot) {
          selected = snapshot = outcome.snapshot;
          observation.outcome = "ready";
        } else if (outcome.status === classic.JsInstalledYamlDataLoadStatus.LocalIgnoreRecoveryRequired && outcome.recoveryPlan) {
          selected = recovery = outcome.recoveryPlan;
          observation.outcome = "recovery_required";
        } else throw new Error("native load outcome has no status-selected payload");
      } else throw new Error("unsupported installed-data operation");
    } catch (error) {
      const native = error as Error & { code?: string; yamlRole?: string; diagnostics?: classic.JsInstalledYamlDataDiagnostic[] };
      const codes = ["unsupported_game", "no_usable_source", "local_ignore_read", "local_ignore_default_invalid", "local_ignore_create", "invalid_selected_data"];
      if (!(error instanceof Error) || !native.code || !codes.includes(native.code)) throw error;
      // The shared role domain contains update-eligible Main/game only; Local Ignore is identified by code.
      observation.error = { code: native.code, role: ["main", "game"].includes(native.yamlRole ?? "") ? native.yamlRole : null };
      // NAPI omits the diagnostics property when the native diagnostic vector is empty.
      observation.diagnostics = diagnostics(root, native.diagnostics ?? []);
    }
    // Projection happens after mutation to demonstrate that native handles retain the selected bytes.
    await materialize(root, fixture.mutations ?? {});
    if (selected) {
      Object.assign(observation, { game: selected.game, gameDataRole: selected.gameDataRole,
        main: selectedFile(selected.main), gameFile: selectedFile(selected.gameFile), diagnostics: diagnostics(root, selected.diagnostics) });
    }
    if (snapshot) {
      observation.localIgnore = { state: token(snapshot.localIgnoreState), identity: identity(snapshot.localIgnoreIdentity, ignorePath) };
      observation.snapshot = { classicVersion: snapshot.yamlData.classicVersion, gameRootName: snapshot.yamlData.gameRootName,
        ignoreList: snapshot.yamlData.ignoreList, simplifyRemoveList: snapshot.simplifyRemoveList };
    }
    if (recovery) observation.recovery = {
      localIgnorePath: pathCarrier(root, recovery.localIgnorePath),
      malformedIdentity: identity(recovery.malformedLocalIgnoreIdentity, ignorePath),
      defaultIdentity: recovery.defaultLocalIgnoreIdentity == null ? null : identity(recovery.defaultLocalIgnoreIdentity, ignorePath),
      selectedGameVersion: recovery.selectedGameVersion,
    };
    if (recovery && fixture.recoveryAction === "proceed") {
      const proceeded = recovery.proceedWithoutIgnore();
      observation.outcome = "proceeded";
      observation.localIgnore = {state: token(proceeded.localIgnoreState), identity: identity(proceeded.localIgnoreIdentity, ignorePath)};
      observation.snapshot = {classicVersion: proceeded.yamlData.classicVersion, gameRootName: proceeded.yamlData.gameRootName, ignoreList: proceeded.yamlData.ignoreList, simplifyRemoveList: proceeded.simplifyRemoveList};
    }
    let backupAlias: string | undefined;
    if (recovery && fixture.recoveryAction === "reset") {
      const outcome = await recovery.resetToDefault();
      if (outcome.status === classic.JsLocalIgnoreResetStatus.Conflict && outcome.conflict) {
        const conflict = outcome.conflict;
        observation.outcome = "reset_conflict";
        observation.recovery.decision = {status: "conflict", expectedIdentity: identity(conflict.expectedIdentity, ignorePath), actualIdentity: conflict.actualIdentity == null ? null : identity(conflict.actualIdentity, ignorePath), backupPath: conflict.backupPath == null ? null : pathCarrier(root, conflict.backupPath)};
      } else if (outcome.status === classic.JsLocalIgnoreResetStatus.Reset && outcome.reset) {
        const reset = outcome.reset;
        // The timestamp/process suffix is normalized only after namespace and retained-hash verification.
        const retainedBackupPath = pathCarrier(root, reset.backupPath);
        if (retainedBackupPath === null) throw new Error("successful reset did not retain its backup path");
        backupAlias = retainedBackupPath;
        const stem = "installation/CLASSIC Backup/YAML Data/Local Ignore/CLASSIC Ignore.yaml." + reset.malformedLocalIgnoreIdentity.sha256 + ".";
        if (!backupAlias.startsWith(stem) || !backupAlias.endsWith(".bak")) throw new Error("reset backup escaped its content-addressed namespace");
        const backupName = "installation/CLASSIC Backup/YAML Data/Local Ignore/<backup>";
        observation.outcome = "reset";
        observation.recovery.decision = {status: "reset", localIgnorePath: pathCarrier(root, reset.localIgnorePath), malformedIdentity: identity(reset.malformedLocalIgnoreIdentity, ignorePath), backupIdentity: identity(reset.backupIdentity, backupName), replacementIdentity: identity(reset.replacementIdentity, ignorePath)};
        observation.diagnostics = diagnostics(root, reset.diagnostics);
        const resolved = reset.snapshot;
        observation.localIgnore = {state: token(resolved.localIgnoreState), identity: identity(resolved.localIgnoreIdentity, ignorePath)};
        observation.snapshot = {classicVersion: resolved.yamlData.classicVersion, gameRootName: resolved.yamlData.gameRootName, ignoreList: resolved.yamlData.ignoreList, simplifyRemoveList: resolved.simplifyRemoveList};
      } else throw new Error("reset status does not select exactly one payload");
    }
    observation.files = await fileTree(root);
    if (backupAlias !== undefined) {
      for (const file of observation.files) if (file.path === backupAlias) file.path = "installation/CLASSIC Backup/YAML Data/Local Ignore/<backup>";
      observation.files.sort((a: any, b: any) => a.path.localeCompare(b.path));
    }
    return observation;
  } finally {
    for (const [name, value] of previous) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    await rm(root, { recursive: true, force: true });
  }
}
