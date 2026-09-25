import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRequire} from "node:module";
import {test} from "node:test";

test("getVersion returns the Rust Cargo package version", () => {
    const manifest = readFileSync(new URL("../Cargo.toml", import.meta.url), "utf8");
    const packageSection = manifest.split("[package]", 2)[1].split(/\r?\n\[/, 1)[0];
    const version = /^version\s*=\s*"([^"]+)"\s*$/m.exec(packageSection)?.[1];
    assert.ok(version, "The test requires the explicitly declared Cargo package version");
    const classic = createRequire(import.meta.url)("../index.js");
    assert.equal(classic.getVersion(), version);
});
