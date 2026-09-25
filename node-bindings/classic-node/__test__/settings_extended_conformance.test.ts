import {expect, test} from "bun:test";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import {observeSettingsExtended} from "./settings_extended_conformance";

const root = resolve(import.meta.dir, "../../..");
const pack = JSON.parse(readFileSync(resolve(root, "tests/conformance/packs/settings_cached_docs/v1.json"), "utf8"));
for (const scenario of pack.scenarios) {
    test(`cached-docs: ${scenario.id}`, () => {
        const fixture = JSON.parse(readFileSync(resolve(root, pack.fixtureRoot, pack.fixtures[scenario.id]), "utf8"));
        expect(observeSettingsExtended(pack.familyId, fixture)).toEqual(scenario.expected);
    });
}
