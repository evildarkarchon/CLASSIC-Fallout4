import { detectGpuInfo, parseLogSegments, extractFormIds, extractPluginList, parseCrashgenVersion, checkCrashgenVersionStatus } from "../index.js";

/** Normalize only absent optional fields on a real native GPU result. */
function gpu(lines: string[]): Record<string, any> {
  const info=detectGpuInfo(lines);
  return {primary:info.primary,secondary:info.secondary ?? null,manufacturer:info.manufacturer,rival:info.rival ?? null};
}

/** Run the Node exports applicable to this scoped log-parsing plan. */
export function observeLogParsing(fixture:Record<string,any>):Record<string,any>{
  if(fixture.operation==="crashgen-version"){
    const version=parseCrashgenVersion(fixture.version);const status=checkCrashgenVersionStatus(fixture.version,fixture.supported);
    const statuses:Record<string,string>={Valid:"valid",Outdated:"outdated",NewerThanKnown:"newer_than_known",NoSupportedVersion:"no_supported_version"};
    if(!(status in statuses))throw new Error("unknown native crashgen status");
    return {operation:"crashgen-version",version:version==null?null:[version.major,version.minor,version.patch],status:statuses[status]};
  }
  if(fixture.operation==="node-parser")return {operation:"node-parser",segments:parseLogSegments(fixture.content),formids:extractFormIds(fixture.content),plugins:extractPluginList(fixture.content)};
  if(fixture.operation!=="gpu")throw new Error("unsupported Node log-parsing operation");
  return {operation:"gpu",info:gpu(fixture.lines),empty:gpu([]),batch:[gpu(fixture.lines),gpu([])]};
}
