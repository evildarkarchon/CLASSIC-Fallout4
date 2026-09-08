import { mkdtemp, mkdir, writeFile, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname, relative, isAbsolute } from "node:path";
import * as classic from "../index.js";

/** Run individual, grouped and rendered integrity checks through the public checker. */
export async function observeIntegrity(fixture: any): Promise<Record<string, unknown>> {
  const root=await mkdtemp(join(tmpdir(),"classic-integrity-conformance-"));
  try {
    for (const [name,content] of Object.entries(fixture.files)) {
      if (name.includes("\\") || isAbsolute(name) || name.split("/").some(part=>["",".",".."].includes(part))) throw new Error("integrity fixture escaped root");
      await mkdir(dirname(join(root,name)),{recursive:true});await writeFile(join(root,name),String(content));
    }
    const checker=new classic.JsGameIntegrityChecker({gameExePath:join(root,fixture.exe),validExeHashes:fixture.hashes,rootName:fixture.rootName,steamIniPath:fixture.steamIni==null?undefined:join(root,fixture.steamIni),rootWarn:fixture.rootWarn??undefined});
    const checks=checker.runAllChecks();
    if(JSON.stringify(checks)!==JSON.stringify([checker.checkExecutableVersion(),checker.checkInstallationLocation()])) throw new Error("grouped integrity checks differ");
    const files: any[]=[];
    /** Inventory final bytes, including unexpected files, without following links. */
    async function visit(directory:string):Promise<void>{for(const entry of await readdir(directory,{withFileTypes:true})){const path=join(directory,entry.name);if(entry.isSymbolicLink())throw new Error("unexpected integrity symlink");if(entry.isDirectory())await visit(path);else files.push({path:relative(root,path).replaceAll("\\","/"),content:await readFile(path,"utf8")});}}
    await visit(root);files.sort((a,b)=>a.path.localeCompare(b.path));
    return {checks,report:checker.runFullCheck(),files};
  } finally {await rm(root,{recursive:true,force:true});}
}
