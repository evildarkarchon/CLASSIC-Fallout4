import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { JsCrashgenChecker, checkCrashgenConfig, checkCrashgenConfigWithRules, checkCrashgenFull, checkCrashgenFullWithRules } from "../index.js";
import { inventory } from "./file_generation_conformance.js";

/** Execute each exported checker alias and preserve complete native issue/report values. */
export async function observeCrashgenCheck(fixture: Record<string, any>): Promise<Record<string, any>> {
  const root=await mkdtemp(join(tmpdir(),"classic-crashgen-node-"));
  const issues=(values:any[])=>values.map(value=>({path:relative(root,value.filePath).replaceAll("\\","/"),section:value.section,setting:value.setting,current:value.currentValue,recommended:value.recommendedValue,description:value.description,severity:value.severity}));
  try {
    for(const [path,content] of Object.entries(fixture.files)) {
      if(path.includes(":")||path.includes("\\")||path.split("/").some(part=>["", ".", ".."].includes(part)))throw new Error("invalid Crashgen fixture path");
      const target=join(root,path);await mkdir(dirname(target),{recursive:true});await writeFile(target,content as string,"utf8");
    }
    const before=await inventory(root);const result=new JsCrashgenChecker(root,"Buffout4").check();
    const report=checkCrashgenFull(root,"Buffout4");
    for(const alias of [checkCrashgenConfig(root,"Buffout4"),checkCrashgenConfigWithRules(root,"Buffout4",undefined)]) {
      if(alias.report!==result.report || JSON.stringify(issues(alias.issues))!==JSON.stringify(issues(result.issues)))throw new Error("Crashgen checker aliases disagree");
    }
    const full=checkCrashgenFullWithRules(root,"Buffout4",undefined);
    if(report.message!==result.report || JSON.stringify(issues(report.issues))!==JSON.stringify(issues(result.issues)) || JSON.stringify(full)!==JSON.stringify(report))throw new Error("Crashgen orchestrator aliases disagree");
    return {message:report.message,issues:issues(report.issues),name:report.crashgenName,config:report.configPath?relative(root,report.configPath).replaceAll("\\","/"):null,plugins:report.installedPlugins.sort(),beforeFiles:before,files:await inventory(root)};
  } finally {await rm(root,{recursive:true,force:true});}
}
