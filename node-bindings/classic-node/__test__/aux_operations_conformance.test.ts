import {expect, test} from "bun:test";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import {observeAuxOperations} from "./aux_operations_conformance";

const root = resolve(import.meta.dir, "../../..");
for (const family of ["web-operations", "resource-operations", "version-operations"]) {
    const pack = JSON.parse(readFileSync(resolve(root, "tests/conformance/packs", family.replaceAll("-", "_"), "v1.json"), "utf8"));
    for (const scenario of pack.scenarios) {
        test(`${family}: ${scenario.id} observes the public binding`, () => {
            const fixture = JSON.parse(readFileSync(resolve(root, pack.fixtureRoot, pack.fixtures[scenario.input.fixtureRef]), "utf8"));
            expect(observeAuxOperations(family, fixture)).toEqual(scenario.expected);
        });
    }
}
