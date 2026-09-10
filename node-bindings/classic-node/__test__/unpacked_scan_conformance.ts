import { mkdir,mkdtemp,readdir,rm,writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname,join,relative } from "node:path";
import { JsUnpackedScanner,scanUnpackedFiles } from "../index.js";
import { inventory } from "./file_generation_conformance.js";

/** Inventory empty directories too so a read-only scan cannot hide filesystem mutations. */
async function directories(root:string,prefix=""):Promise<string[]>{
  const result:string[]=[];for(const entry of await readdir(join(root,prefix),{withFileTypes:true})){const path=prefix?`${prefix}/${entry.name}`:entry.name;if(entry.isDirectory()){result.push(path,...await directories(root,path));}}return result.sort();
}

/** Project actual sets deterministically; DDS paths are inventory, not issue counts. */
function issues(value:Record<string,any>,root:string):Record<string,any>{
  const fields={animation:value.animdata,formats:value.texFrmt,sounds:value.sndFrmt,scripts:value.xseFile,previs:value.previs};
  return {...Object.fromEntries(Object.entries(fields).map(([name,values])=>[name,(values as string[]).map(value=>value.replaceAll("\\","/")).sort()])),dds:value.ddsFiles.map((path:string)=>relative(root,path).replaceAll("\\","/")).sort()};
}

/** Exercise the native class and free-function scanner while retaining all input bytes. */
export async function observeUnpackedScan(fixture:Record<string,any>):Promise<Record<string,any>>{
  const root=await mkdtemp(join(tmpdir(),"classic-unpacked-node-"));
  const target=(path:string)=>{if(path.includes(":")||path.includes("\\")||path.split("/").some(part=>["", ".", ".."].includes(part)))throw new Error("invalid unpacked path");return join(root,path);};
  try{
    for(const path of fixture.directories)await mkdir(target(path),{recursive:true});
    for(const [path,content] of Object.entries(fixture.files)){const destination=target(path);await mkdir(dirname(destination),{recursive:true});await writeFile(destination,content as string,"utf8");}
    const result:Record<string,any>={beforeFiles:await inventory(root),beforeDirectories:await directories(root)};const scanner=new JsUnpackedScanner();result.issues=issues(scanner.scanDirectory(root,fixture.scripts),root);
    if(JSON.stringify(issues(scanUnpackedFiles(root,fixture.scripts),root))!==JSON.stringify(result.issues))throw new Error("unpacked convenience scan changed results");
    result.files=await inventory(root);result.directories=await directories(root);return result;
  }finally{await rm(root,{recursive:true,force:true});}
}
