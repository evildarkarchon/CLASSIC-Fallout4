import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

test("explicit logging initialization is idempotent and emits native records", () => {
  const child = spawnSync(process.execPath, ["-e", "const m=require('./index.js');m.initLogging();m.initLogging();new m.JsLogger('probe').info('classic-init-record')"], {
    cwd: new URL("../", import.meta.url), encoding: "utf8",
    env: { ...process.env, RUST_LOG: "trace", RUST_LOG_STYLE: "never" },
  });
  assert.equal(child.status, 0, child.stderr);
  assert.equal(child.stderr.split("classic-init-record").length - 1, 1);
  assert.match(child.stderr, /INFO/);
});
