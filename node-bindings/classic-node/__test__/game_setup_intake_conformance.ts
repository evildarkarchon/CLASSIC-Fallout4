import {mkdir, mkdtemp, readdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, isAbsolute, join, relative} from "node:path";
import * as classic from "../index.js";

/** Execute primitive decisions or compare explicit and settings-backed read-only setup intake. */
export async function observeSetup(fixture: any): Promise<Record<string, unknown>> {
    if (fixture.operation === "normalize") return {
        versions: fixture.versions.map((value: any) => classic.normalizeGameSetupVersionSelection(value)),
        needs: fixture.paths.map(([game, docs]: any[]) => {
            const result = classic.gameSetupNeedsPathDetection(game, docs);
            return [result.needsGamePath, result.needsDocsPath];
        })
    };
    const root = await mkdtemp(join(tmpdir(), "classic-setup-conformance-"));
    try {
        for (const [name, content] of Object.entries(fixture.files)) {
            if (name.includes("\\") || isAbsolute(name) || name.split("/").some(part => ["", ".", ".."].includes(part))) throw new Error("setup fixture escaped root");
            await mkdir(dirname(join(root, name)), {recursive: true});
            await writeFile(join(root, name), String(content).replaceAll("<ROOT>", root.replaceAll("\\", "/")));
        }

        /** Inventory all files/directories to catch unexpected write effects. */
        async function tree(): Promise<Record<string, string | null>> {
            const result: Record<string, string | null> = {};

            /** Capture nested owned entries without following links. */
            async function visit(dir: string): Promise<void> {
                for (const entry of await readdir(dir, {withFileTypes: true})) {
                    const path = join(dir, entry.name), key = relative(root, path).replaceAll("\\", "/");
                    if (entry.isSymbolicLink()) throw new Error("unexpected setup link");
                    if (entry.isDirectory()) {
                        result[key] = null;
                        await visit(path);
                    } else result[key] = (await readFile(path)).toString("hex");
                }
            }

            await visit(root);
            return Object.fromEntries(Object.entries(result).sort(([a], [b]) => a.localeCompare(b)));
        }

        const before = await tree();

        /** Preserve result summaries while authenticating rendered typed diagnostic fields. */
        function project(result: any): any {
            const report = result.renderedReport;
            if (result.totalChecks !== result.checks.length || result.failedChecks !== result.checks.filter((check: any) => check.state === "failed").length) throw new Error("setup summary lost typed checks");
            for (const check of result.checks) {
                if (!report.includes(`[${check.state}] ${check.kind}: ${check.message}`) || check.details.some((detail: string) => !report.includes(detail))) throw new Error("setup report lost diagnostic content");
            }
            return {
                status: result.status,
                hasErrors: result.hasErrors,
                totalChecks: result.totalChecks,
                failedChecks: result.failedChecks,
                actionCount: result.actionCount,
                pathUpdateCount: result.pathUpdateCount,
                pathUpdates: result.pathUpdates.map((update: any) => ({
                    kind: update.kind,
                    path: relative(root, update.path).replaceAll("\\", "/")
                })),
                gameRoot: relative(root, result.gameRoot).replaceAll("\\", "/"),
                docsRoot: relative(root, result.docsRoot).replaceAll("\\", "/"),
                gameExecutable: relative(root, result.gameExecutable).replaceAll("\\", "/"),
                reportFlags: {
                    gameNamed: report.includes("Game Setup Intake: Starfield"),
                    metadataUnsupported: report.includes("[unsupported] registry_metadata:"),
                    versionWarning: report.includes("[warning] executable_version:"),
                    documentsPassed: report.includes("[passed] documents_folder:"),
                    loaderFailed: report.includes("[failed] xse_loader:")
                }
            };
        }

        const direct = project(classic.runGameSetupIntake({
            gameId: "Starfield",
            gameVersion: "Original",
            gameRoot: join(root, "Game"),
            docsRoot: join(root, "Docs"),
            gameExePath: join(root, "Game/Starfield.exe")
        }));
        const result = project(classic.runGameSetupIntakeFromUserSettings(root));
        if (JSON.stringify(direct) !== JSON.stringify(result)) throw new Error("equivalent setup facts differ");
        const after = await tree();
        return {
            ...result,
            files: Object.entries(after).filter(([, value]) => value !== null).map(([path]) => path),
            unchanged: JSON.stringify(before) === JSON.stringify(after)
        };
    } finally {
        await rm(root, {recursive: true, force: true});
    }
}
