import {mkdtemp, readdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, relative, sep} from "node:path";
import * as classic from "../index.js";
import {yamlValues} from "./config_yaml_values_conformance.js";

type JsonObject = Record<string, any>;

/** Re-read every durable file, retaining exact UTF-8 bytes and portable paths. */
async function inventory(root: string, directory = root): Promise<JsonObject[]> {
    const result: JsonObject[] = [];
    for (const entry of await readdir(directory, {withFileTypes: true})) {
        const path = join(directory, entry.name);
        if (entry.isSymbolicLink()) throw new Error("unexpected link in config workspace");
        if (entry.isDirectory()) result.push(...await inventory(root, path));
        else result.push({path: relative(root, path).split(sep).join("/"), content: await readFile(path, "utf8")});
    }
    return result.sort((a, b) => a.path.localeCompare(b.path));
}

/** Invoke the public explicit loader, retaining structured failures and all durable effects. */
export async function observeConfigOperations(fixture: JsonObject): Promise<JsonObject> {
    if (!["load-explicit", "main-version", "persist-local"].includes(fixture.operation) || Object.keys(fixture).sort().join() !== (fixture.operation === "persist-local" ? "docsRoot,files,gameRoot,operation" : "files,operation")) {
        throw new Error("unsupported config operation fixture");
    }
    const root = await mkdtemp(join(tmpdir(), "classic-config-conformance-"));
    try {
        for (const [name, content] of Object.entries(fixture.files)) {
            if (!["main.yaml", "game.yaml", "ignore.yaml", "CLASSIC Main.yaml", "local.yaml", "CLASSIC Settings.yaml"].includes(name) || typeof content !== "string") {
                throw new Error("config fixture requires owned YAML filenames and UTF-8 text");
            }
            await writeFile(join(root, name), content, "utf8");
        }
        if (fixture.operation === "persist-local") {
            await classic.persistGameLocalPaths(join(root, "local.yaml"), fixture.gameRoot, fixture.docsRoot);
            return {result: null, error: null, files: await inventory(root)};
        }
        if (fixture.operation === "main-version") {
            // Own resolver inputs while this sequential adapter awaits native loading.
            const previous = new Map(["LOCALAPPDATA", "XDG_CACHE_HOME"].map(name => [name, process.env[name]]));
            try {
                for (const name of previous.keys()) process.env[name] = join(root, "isolated-cache");
                const version = await classic.loadMainYamlVersion(root);
                return {result: {version}, error: null, files: await inventory(root)};
            } finally {
                for (const [name, value] of previous) {
                    if (value === undefined) delete process.env[name]; else process.env[name] = value;
                }
            }
        }
        let result: JsonObject | null = null;
        let error: JsonObject | null = null;
        let snapshot: classic.ExplicitYamlDataSnapshot | undefined;
        try {
            snapshot = await classic.loadExplicitYamlData(
                {
                    mainPath: join(root, "main.yaml"),
                    gamePath: join(root, "game.yaml"),
                    ignorePath: join(root, "ignore.yaml")
                },
                classic.JsGameId.Fallout4,
                "auto",
            );
        } catch (failure: any) {
            // Reject infrastructure failures instead of manufacturing a domain observation.
            if (!["read", "parse", "invalid_utf8", "invalid_role_data", "unsupported_game"].includes(failure.code)) throw failure;
            error = {
                code: failure.code,
                role: failure.yamlRole ?? null,
                path: failure.path == null ? null : relative(root, failure.path).split(sep).join("/")
            };
        }
        if (snapshot !== undefined) {
            if (snapshot.game !== classic.JsGameId.Fallout4) throw new Error("explicit snapshot returned an unexpected game");
            const data = snapshot.yamlData;
            if (snapshot.gameDataRole !== classic.JsExplicitYamlDataGameRole.Fallout4) throw new Error("explicit snapshot returned an unexpected game role");
            result = {
                game: "Fallout4",
                classicVersion: data.classicVersion,
                xseAcronym: data.xseAcronym,
                crashgenName: data.crashgenName,
                gameVersion: data.gameVersion,
                ignoreList: data.ignoreList
            };
            result.gameRole = "Fallout4";
            result.yamlValues = yamlValues(data);
            const fromContent = classic.createYamlDataFromContent(fixture.files["main.yaml"], fixture.files["game.yaml"], fixture.files["ignore.yaml"], "Fallout4", "auto");
            if (JSON.stringify(yamlValues(fromContent)) !== JSON.stringify(result.yamlValues)) throw new Error("content constructor differs from retained explicit data");
            result.identities = Object.fromEntries([["main.yaml", snapshot.mainIdentity], ["game.yaml", snapshot.gameIdentity], ["ignore.yaml", snapshot.ignoreIdentity]].map(([name, identity]: any) => [name, {
                sha256: identity.sha256,
                byteLen: Number(identity.byteLen)
            }]));
        }
        return {result, error, files: await inventory(root)};
    } finally {
        await rm(root, {recursive: true, force: true});
    }
}
