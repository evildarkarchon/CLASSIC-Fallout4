import { mkdtemp, writeFile, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import * as classic from "../index.js";

/** Observe actual extraction, copy and replacement inside a disposable root. */
export async function observePathBackups(fixture: Record<string, any>): Promise<Record<string, any>> {
  const root = await mkdtemp(join(tmpdir(), "classic-backup-"));
  const local = (path: string) => relative(root, path).split(sep).join("/");
  try {
    const source = join(root, "settings.ini"), log = join(root, "xse.log");
    await writeFile(log, fixture.log); await writeFile(source, Buffer.from(fixture.firstHex, "hex"));
    const manager = new classic.BackupManager(join(root, "backups"));
    const initial = manager.listVersions();
    const version = manager.extractVersionFromXseLog(log), explicit = new classic.XseVersion(fixture.version);
    if (version.fullVersion() !== explicit.fullVersion() || version.sanitized() !== explicit.sanitized() || explicit.toString() !== `XseVersion('${fixture.version}')`) throw new Error("version APIs disagree");
    const created = manager.createBackup(source, version), first = (await readFile(created)).toString("hex");
    await writeFile(source, Buffer.from(fixture.replacementHex, "hex"));
    if (manager.createBackup(source, explicit) !== created) throw new Error("replacement path changed");
    const files: Record<string,string> = {};
    /** Retain every actual file so unexpected backup writes cannot disappear. */
    async function inventory(directory: string): Promise<void> {
      for (const entry of await readdir(directory, { withFileTypes: true })) {
        const path = join(directory, entry.name);
        if (entry.isDirectory()) await inventory(path); else files[local(path)] = (await readFile(path)).toString("hex");
      }
    }
    await inventory(root);
    return { version: version.fullVersion(), sanitized: version.sanitized(), initial, versions: manager.listVersions(), root: local(manager.backupRoot), directory: local(manager.getVersionPath(explicit)), created: local(created), firstHex: first, replacementHex: (await readFile(created)).toString("hex"), files };
  } finally { await rm(root, { recursive: true, force: true }); }
}
