import { test, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { observeVersionExtended } from "./version_extended_conformance";

const root = resolve(import.meta.dir, "../../..");
for (const family of ["version_extraction", "version_pe", "version_pe_path"]) {
  const pack = JSON.parse(readFileSync(resolve(root, `tests/conformance/packs/${family}/v1.json`), "utf8"));
  for (const scenario of pack.scenarios) {
    test(`${family}: ${scenario.id}`, () => {
      const fixture = JSON.parse(readFileSync(resolve(root, pack.fixtureRoot, pack.fixtures[scenario.id]), "utf8"));
      expect(observeVersionExtended(fixture)).toEqual(scenario.expected);
    });
  }
}
