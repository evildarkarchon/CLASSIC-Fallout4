import { mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as classic from "../index.js";
type JsonObject = Record<string, any>;

/** Observe public XSE metadata and detection against a fresh fixture-owned directory. */
export async function observeXseOperations(fixture: JsonObject): Promise<JsonObject> {
  const variant = fixture.kind ?? "F4SE";
  const kinds: Record<string, classic.JsXseType> = { F4SE: classic.JsXseType.F4se, F4SEVR: classic.JsXseType.F4sevr,
    SKSE: classic.JsXseType.Skse, SKSE64: classic.JsXseType.Skse64, SKSEVR: classic.JsXseType.Sksevr, SFSE: classic.JsXseType.Sfse };
  if (typeof variant !== "string" || !Object.hasOwn(kinds, variant)
      || Object.keys(fixture).some(key => key !== "files" && key !== "kind") || !Array.isArray(fixture.files)
      || fixture.files.some((name: unknown) => ![`${variant.toLowerCase()}_loader.exe`, `${variant.toLowerCase()}_1_10_163.dll`].includes(name as string))) {
    throw new Error("unsupported XSE fixture");
  }
  const root = await mkdtemp(join(tmpdir(), "classic-xse-conformance-"));
  try {
    for (const name of fixture.files) await writeFile(join(root, name), "");
    const kind = kinds[variant];
    if (classic.parseXseType(variant) !== kind) throw new Error("XSE enum and parser disagree");
    const info = classic.getXseInfo(root, kind);
    return { typeName: classic.xseTypeName(kind), loaderName: classic.xseLoaderName(kind), dllPrefix: classic.xseDllPrefix(kind),
      installed: classic.isXseInstalled(root, kind), version: classic.detectXseVersion(join(root, classic.xseLoaderName(kind)), kind),
      info: { typeName: info.xseType, installed: info.installed, version: info.version ?? null },
      files: await Promise.all((await readdir(root)).sort().map(async name => ({ path: name, hex: (await readFile(join(root, name))).toString("hex") }))) };
  } finally { await rm(root, { recursive: true, force: true }); }
}
