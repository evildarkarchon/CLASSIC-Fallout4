import { FormIdFindingAnalyzer, JsFormIdValueLookup } from "../index.js";

/** Run a real opaque analyzer over deterministic native disabled/in-memory lookup handles. */
export async function observeFormidFinding(fixture:Record<string,any>):Promise<Record<string,any>>{
  const mode=fixture.mode;
  const lookup=mode==="disabled"?JsFormIdValueLookup.disabled():mode==="in-memory"?JsFormIdValueLookup.inMemory(fixture.entries.map((entry:Record<string,any>)=>({formid:entry.formid,plugin:entry.plugin,value:entry.value ?? undefined,operationalFailure:entry.failure ?? undefined}))):null;
  if(lookup===null)throw new Error("unsupported Node FormID factory mode");
  const analyzer=new FormIdFindingAnalyzer(lookup);
  if(analyzer.kind!=="formid_finding")throw new Error("incorrect native analyzer identity");
  try{
    const result=await analyzer.analyze({crashLines:fixture.lines,plugins:fixture.plugins});
    return {mode,findings:result.findings.map(finding=>({identifier:finding.identifier,occurrences:finding.occurrences,plugin:finding.plugin ?? null,status:finding.valueLookupStatus,value:finding.value ?? null})),error:null};
  }catch(error){
    if(!(error instanceof Error) || !("code" in error) || !("analyzerKind" in error) || error.analyzerKind!=="formid_finding")throw error;
    return {mode,findings:null,error:{code:error.code,message:error.message}};
  }
}
