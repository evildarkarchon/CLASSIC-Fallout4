import { detectCrashPattern, detectVrLog } from "../index.js";

/** Observe the actual classifier token; no adapter-local pattern table is allowed. */
export function observeCrashPattern(fixture:Record<string,any>):Record<string,any>{
  if(fixture.operation==="vr")return {vr:detectVrLog(fixture.content)};
  if(fixture.operation!=="classify")throw new Error("Node has no legacy CXX error-text alias");
  return {token:detectCrashPattern(fixture.content) ?? null};
}
