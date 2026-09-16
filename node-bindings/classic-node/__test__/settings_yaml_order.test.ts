import {expect, test} from "bun:test";
import {yamlGetIndexmapValue} from "../index.js";

test("ordered YAML mapping preserves non-index string key insertion order", () => {
    expect(Object.entries(yamlGetIndexmapValue("mapping:\n  zebra: last\n  alpha: first\n", "mapping")))
        .toEqual([["zebra", "last"], ["alpha", "first"]]);
});
