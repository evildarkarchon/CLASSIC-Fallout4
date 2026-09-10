import { mkdtemp, writeFile, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as classic from "../index.js";

/** Observe native game and mod stages, retaining nonfatal configuration errors. */
export async function observeOrchestration(fixture: any): Promise<Record<string, unknown>> {
  const root=await mkdtemp(join(tmpdir(),"classic-orchestration-conformance-"));
  try {
    for (const [name,content] of Object.entries(fixture.files)){if(name!=="sentinel.txt")throw new Error("unsupported orchestration fixture path");await writeFile(join(root,name),String(content));}
    const config={gamePath:root,xseAcronym:fixture.xseAcronym,crashgenName:fixture.crashgenName,gameName:fixture.gameName,xseScriptfiles:{},isVr:false,gameVersion:"Original",wryeWarnings:{},logCatchErrors:["error"],logExcludeFiles:[],logExcludeErrors:[],gameTarget:"Fallout4"};
    const result=await classic.runGameChecks(config);const mods=await classic.runModScans(config);
    // JoinSet completion order varies; authenticate the native report before canonicalizing it.
    const reportMatchesChecks=result.report===result.checkResults.map(check=>check.output).join("");
    const game={checkResults:[...result.checkResults].sort((a,b)=>a.name.localeCompare(b.name)),reportMatchesChecks,configIssueCount:result.configIssues.length,errors:[...result.errors].sort()};
    const files=[];for(const name of (await readdir(root)).sort())files.push({path:name,content:await readFile(join(root,name),"utf8")});
    return {game,mods:{report:mods.report,unpackedIssueCount:mods.unpackedIssueCount,archivedIssueCount:mods.archivedIssueCount,errors:[...mods.errors].sort()},files};
  } finally {await rm(root,{recursive:true,force:true});}
}
