import * as classic from "../index.js";

/** Read each native YAML identifier and description without constructing expected values. */
export function observeYamlFileValues(fixture: Record<string, any>): Record<string, any> {
  if (JSON.stringify(fixture) !== '{"request":{}}') throw new Error("unsupported YAML file value request");
  return { kinds: classic.getAllYamlFiles().map(value => ({ token: value, description: classic.getYamlFileDescription(value) })) };
}
