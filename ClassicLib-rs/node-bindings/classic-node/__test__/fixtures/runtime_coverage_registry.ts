import { readFileSync } from "node:fs";

type RuntimeCoverageEntry = {
  coverageId: string;
  classification: string;
  ownerModule: string;
  tier: string;
  testSuite?: string;
  testCaseId?: string;
  fixtureRefs?: string[];
  bindingIdentifiers?: string[];
  contractSelector?: Record<string, string>;
};

type RuntimeCoverageRegistry = {
  schemaVersion: string;
  binding: string;
  entries: RuntimeCoverageEntry[];
};

const registry = JSON.parse(
  readFileSync(new URL("./runtime_coverage_registry.json", import.meta.url), "utf-8"),
) as RuntimeCoverageRegistry;

export function getRuntimeCoverageEntries(testSuite?: string): RuntimeCoverageEntry[] {
  if (!testSuite) {
    return registry.entries;
  }
  return registry.entries.filter((entry) => entry.testSuite === testSuite);
}

export function getTier1OwnerModules(): string[] {
  return getRuntimeCoverageEntries()
    .filter((entry) => entry.tier === "tier1")
    .map((entry) => entry.ownerModule);
}
