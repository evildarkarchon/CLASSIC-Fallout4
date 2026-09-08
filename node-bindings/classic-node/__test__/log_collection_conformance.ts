import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { JsLogCollector, CRASH_AUTOSCAN_PATTERN, CRASH_LOG_PATTERN } from "../index.js";
import { inventory } from "./file_generation_conformance.js";

/** Exercise actual collection twice, retaining exact move/copy effects and custom paths. */
export async function observeLogCollection(fixture: Record<string, any>): Promise<Record<string, any>> {
  if (CRASH_AUTOSCAN_PATTERN !== "crash-*-AUTOSCAN.md") throw new Error("public autoscan glob changed");
  if (CRASH_LOG_PATTERN !== "crash-*.log") throw new Error("public crash-log glob changed");
  const root=await mkdtemp(join(tmpdir(),"classic-collection-node-"));
  const materialize=async (values: Record<string,string>)=>{
    for(const [path,content] of Object.entries(values)){
      if(path.includes(":") || path.includes("\\") || path.split("/").some(part=>["", ".", ".."].includes(part)))throw new Error("invalid collection fixture path");
      const target=join(root,path);await mkdir(dirname(target),{recursive:true});await writeFile(target,content,"utf8");
    }
  };
  try {
    for(const folder of ["base","xse","custom"])await mkdir(join(root,folder));
    await materialize(fixture.files);
    const collector=new JsLogCollector(join(root,"base"),join(root,"xse"),join(root,"custom"));
    const normalized=(paths:string[])=>paths.map(path=>relative(root,path).replaceAll("\\","/")).sort();
    const result:Record<string,any>={before:await inventory(root),first:normalized(await collector.collectAll())};
    if(collector.crashLogsDir()!==join(root,"base","Crash Logs") || collector.pastebinDir()!==join(root,"base","Crash Logs","Pastebin"))throw new Error("collector path accessor changed");
    result.afterFirst=await inventory(root);
    await materialize(fixture.later);
    result.second=normalized(await collector.collectAll());
    result.files=await inventory(root);
    return result;
  } finally {await rm(root,{recursive:true,force:true});}
}
