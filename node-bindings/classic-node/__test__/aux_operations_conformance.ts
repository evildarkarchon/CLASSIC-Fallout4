import {observeVersionExtended} from "./version_extended_conformance";
import * as classic from "../index.js";
import {mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {dirname, join, relative} from "node:path";

type JsonObject = Record<string, any>;

/** Preserve documented native errors; programming and dispatch failures still fail execution. */
function result(operation: () => string): JsonObject {
    try {
        return {value: operation(), error: null};
    } catch (error) {
        if (!(error instanceof Error) || !/^(Invalid URL|URL parse error:|Version string is empty|Invalid version)/.test(error.message)) throw error;
        return {value: null, error: error.message};
    }
}

/** Exercise pure public binding operations using only the materialized input request. */
export function observeAuxOperations(family: string, fixture: JsonObject): JsonObject {
    const request = fixture.request;
    if (family.startsWith("version-") && request.operation) return observeVersionExtended(fixture);
    if (family === "web-operations") {
        if (request.operation === "game-routes") {
            if (request.game !== "Fallout4") throw new Error("Unsupported routing game");
            return {
                urls: ["NexusMods", "BethesdaNet", "ModDB"].map(site =>
                    classic.getModSiteGameUrl(site as classic.JsModSite, request.game as classic.JsGameId))
            };
        }
        const url = request.url;
        if (classic.getUserAgentPrefix() !== classic.getUserAgent().split("/")[0]) {
            throw new Error("User agent prefix disagrees with the public user agent");
        }
        if (classic.getClassicVersion() !== classic.getUserAgent().split("/")[1]) {
            throw new Error("CLASSIC version disagrees with the public user agent");
        }
        return {
            userAgent: classic.getUserAgent(),
            userAgentWithSuffix: classic.getUserAgentWithSuffix(request.suffix),
            sites: ["NexusMods", "BethesdaNet", "ModDB"].map(site => ({
                name: classic.getModSiteName(site as classic.JsModSite),
                baseUrl: classic.getModSiteUrl(site as classic.JsModSite),
            })),
            valid: classic.isValidUrl(url),
            validated: result(() => classic.validateUrl(url)),
            domain: result(() => classic.extractDomain(url)),
            joined: result(() => classic.joinUrl(url, request.path)),
            query: result(() => classic.buildUrlWithQuery(url, request.params.map(([key, value]: string[]) => ({
                key,
                value
            })))),
        };
    }
    if (family === "resource-operations") {
        const info = classic.createResourceInfo(request.path);
        const observation: JsonObject = {
            detected: classic.detectResourceType(request.path),
            supported: classic.isSupportedResource(request.path),
            parsed: classic.parseResourceType(request.type),
            typeCatalog: request.types.map((name: string) => classic.parseResourceType(name)),
            extensions: classic.getResourceExtensions(request.type),
            info: {path: info.path, type: info.resourceType, size: info.size},
        };
        const root = mkdtempSync(join(tmpdir(), "classic-resource-conformance-"));
        try {
            for (const [path, content] of Object.entries(fixture.files)) {
                const target = owned(root, path);
                mkdirSync(dirname(target), {recursive: true});
                writeFileSync(target, content as string, "utf8");
            }
            observation.resources = classic.enumerateResources(root).map(item => ({
                path: relative(root, item.path).replaceAll("\\", "/"),
                type: item.resourceType,
                size: item.size
            })).sort((a, b) => a.path.localeCompare(b.path));
            observation.counts = classic.countResourcesByType(root).map(item => ({
                type: item.resourceType,
                count: item.count
            })).sort((a, b) => a.type.localeCompare(b.type));
            const first = observation.resources[0];
            const sized = classic.createResourceInfoWithSize(first.path, first.size);
            observation.sizedInfo = {path: sized.path, type: sized.resourceType, size: sized.size};
            observation.validation = request.validate.map((path: string) => {
                let error = null;
                try {
                    classic.validateResource(owned(root, path));
                } catch (failure) {
                    if (!(failure instanceof Error)) throw failure;
                    if (failure.message.startsWith("Resource not found: ")) error = "not_found";
                    else if (failure.message.startsWith("Invalid resource type: Path is not a file: ")) error = "invalid_type";
                    else throw failure;
                }
                return {path, error};
            });
            observation.files = resourceFiles(root, root).sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
            return observation;
        } finally {
            rmSync(root, {recursive: true, force: true});
        }
    }
    if (family === "version-operations") {
        const parsed = result(() => classic.parseVersion(request.version));
        return {
            parsed,
            optional: classic.tryParseVersion(request.version),
            comparison: parsed.error === null ? classic.compareVersions(request.version, request.other) : null,
            formatted: parsed.error === null ? classic.formatVersion(request.version) : null,
        };
    }
    throw new Error("unsupported auxiliary owner domain");
}

/** Keep every authored fixture destination inside the disposable workspace. */
function owned(root: string, path: string): string {
    if (!path || /[\\:]/.test(path) || path.split("/").some(part => ["", ".", ".."].includes(part))) throw new Error("resource fixture path must be contained");
    return join(root, path);
}

/** Read every actual file after execution, rejecting symlinks and unowned file kinds. */
function resourceFiles(root: string, directory: string): { path: string; hex: string }[] {
    const files: { path: string; hex: string }[] = [];
    for (const entry of readdirSync(directory, {withFileTypes: true})) {
        const path = join(directory, entry.name);
        if (entry.isDirectory()) files.push(...resourceFiles(root, path));
        else if (entry.isFile()) files.push({
            path: relative(root, path).replaceAll("\\", "/"),
            hex: readFileSync(path).toString("hex")
        });
        else throw new Error("unexpected symlink or special file in resource workspace");
    }
    return files;
}
