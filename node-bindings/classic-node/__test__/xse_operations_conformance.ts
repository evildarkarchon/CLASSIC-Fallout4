import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as classic from "../index.js";
type JsonObject = Record<string, any>;

/** Observe public XSE metadata and detection against a fresh fixture-owned directory. */
export async function observeXseOperations(fixture: JsonObject): Promise<JsonObject> {
  if (Object.keys(fixture).join() !== "files" || !Array.isArray(fixture.files)
      || fixture.files.some((name: unknown) => !["f4se_loader.exe", "f4se_1_10_163.dll"].includes(name as string))) {
    throw new Error("unsupported XSE fixture");
  }
  const root = await mkdtemp(join(tmpdir(), "classic-xse-conformance-"));
  try {
    for (const name of fixture.files) await writeFile(join(root, name), "");
    const kind = classic.JsXseType.F4se;
    if (classic.parseXseType("f4se") !== kind) throw new Error("XSE enum and parser disagree");
    const info = classic.getXseInfo(root, kind);
    return { typeName: classic.xseTypeName(kind), loaderName: classic.xseLoaderName(kind), dllPrefix: classic.xseDllPrefix(kind),
      installed: classic.isXseInstalled(root, kind), version: classic.detectXseVersion(join(root, "f4se_loader.exe"), kind),
      info: { typeName: info.xseType, installed: info.installed, version: info.version ?? null },
      files: await Promise.all((await readdir(root)).sort().map(async name => ({ path: name, hex: (await readFile(join(root, name))).toString("hex") }))) };
  } finally { await rm(root, { recursive: true, force: true }); }
}
