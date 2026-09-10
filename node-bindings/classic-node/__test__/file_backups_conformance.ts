import { mkdtemp, mkdir, writeFile, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import * as classic from "../index.js";

/** Observe copies and restored bytes before removing only fixture-selected files. */
export async function observeFileBackups(fixture: Record<string, any>): Promise<Record<string, any>> {
  const root = await mkdtemp(join(tmpdir(), "classic-managed-backup-"));
  try {
    const game = fixture.kind === "game-files" ? join(root, "game") : root;
    await mkdir(game, { recursive: true });
    const source = join(game, "f4se_fixture.dll");
    await writeFile(source, fixture.content); await writeFile(join(game, "sentinel.txt"), "keep\n");
    const files = async () => {
      const result: Record<string,string> = {};
      /** Retain unrelated sentinels as well as backup-owned file bytes. */
      async function walk(directory: string): Promise<void> {
        for (const entry of await readdir(directory, { withFileTypes: true })) {
          const path = join(directory, entry.name);
          if (entry.isDirectory()) await walk(path); else result[relative(root,path).split(sep).join("/")] = await readFile(path,"utf8");
        }
      }
      await walk(root); return result;
    };
    if (fixture.kind === "managed") {
      const manager = new classic.JsBackupManager(game);
      const initial = await manager.backupExists("xse");
      const result = await manager.createBackup("xse");
      if (result.backupType !== "XSE (F4SE/SKSE)" || !result.exists || result.backupDir !== join(game,"CLASSIC_Backups","XSE_Backup")) throw new Error("backup metadata differs from owned destination");
      const exists = await manager.backupExists("xse");
      const copy = await readFile(join(result.backupDir,"f4se_fixture.dll"),"utf8");
      await writeFile(source,"changed\n");
      const restored = await manager.restoreBackup("xse");
      return { initial, exists, created: `Backed up ${result.fileCount} files`, restored, copy, source: await readFile(source,"utf8"), files: await files() };
    }
    const manager = new classic.JsGameFilesManager(game,join(root,"backups"));
    const summarize = (result: any, operation: string) => {
      if (result.operation !== operation || result.label !== "fixture") throw new Error("operation metadata changed");
      return `${result.filesAffected} files affected, ${result.errors.length} errors`;
    };
    const backup = summarize(await manager.backup("fixture",["f4se_"]),"BACKUP");
    await writeFile(source,"changed\n");
    const restore = summarize(await manager.restore("fixture",["f4se_"]),"RESTORE");
    const restored = await readFile(source,"utf8");
    const remove = summarize(await manager.remove("fixture",["f4se_"]),"REMOVE");
    return { backup, restore, remove, restored, files: await files() };
  } finally { await rm(root, { recursive: true, force: true }); }
}
