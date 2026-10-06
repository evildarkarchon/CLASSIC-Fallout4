import {afterEach, describe, expect, test} from "bun:test";
import {mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";

import {JsGameId, ScanRunLaunch, ScanRunRequest} from "../index.js";

const roots: string[] = [];

/** Creates an Installation Root whose User Settings document holds `yaml`. */
function rootWithSettings(yaml: string): string {
    const root = mkdtempSync(join(tmpdir(), "classic-scan-launch-spec-"));
    roots.push(root);
    writeFileSync(join(root, "CLASSIC Settings.yaml"), yaml);
    return root;
}

const MANAGED_FALLOUT4 = `schema_version: "1.0"
CLASSIC_Settings:
  Managed Game: Fallout 4
  Game Version: NextGen
  Max Concurrent Scans: 3
  FormID Databases:
    Fallout4:
      - databases/Fallout4 FormIDs.db
`;

afterEach(() => {
    for (const root of roots.splice(0)) rmSync(root, {recursive: true, force: true});
});

describe("ScanRunLaunch", () => {
    test("standard launch carries the Rust-built request and never writes User Settings", () => {
        const root = rootWithSettings(MANAGED_FALLOUT4);
        const before = readFileSync(join(root, "CLASSIC Settings.yaml"));

        const launch = ScanRunLaunch.standard(root, {maxConcurrent: 0, showFormidValues: true});

        expect(launch.intent).toBe("standard");
        expect(launch.configuration.game).toBe(JsGameId.Fallout4);
        expect(launch.configuration.gameVersion).toBe("NextGen");
        expect(launch.configuration.maxConcurrent ?? null).toBeNull();
        expect(launch.configuration.showFormidValues).toBe(true);
        expect(launch.configuration.formidDatabasePaths).toEqual(["databases/Fallout4 FormIDs.db"]);
        expect(launch.standardSource?.baseDirectory).toBe(root);
        expect(launch.targetedSource).toBeNull();
        expect(launch.fcxEnabled).toBe(false);
        expect(launch.diagnostics).toEqual([]);
        expect(launch.request()).toBeInstanceOf(ScanRunRequest);
        expect(readFileSync(join(root, "CLASSIC Settings.yaml")).equals(before)).toBe(true);
    });

    test("degraded User Settings still launch and report their diagnostics", () => {
        const root = rootWithSettings("CLASSIC_Settings:\n  Managed Game: Fallout 4\n");

        const launch = ScanRunLaunch.standard(root);

        expect(launch.diagnostics.map(diagnostic => [diagnostic.kind, diagnostic.code])).toEqual([
            ["userSettings", "migration_required_unversioned_document"],
        ]);
    });

    test("a Targeted launch without inputs throws the typed launch error", () => {
        const root = rootWithSettings(MANAGED_FALLOUT4);

        let caught: unknown;
        try {
            ScanRunLaunch.targeted(root, []);
        } catch (error) {
            caught = error;
        }

        expect((caught as { code?: string }).code).toBe("targeted_without_inputs");
        expect((caught as { kind?: string }).kind).toBe("targeted_without_inputs");
    });

    test("the FCX Mode override gives a Targeted launch its setup context and XSE log", () => {
        const scratch = rootWithSettings("");
        const game = join(scratch, "Fallout 4");
        const documents = join(scratch, "Documents");
        mkdirSync(join(documents, "F4SE"), {recursive: true});
        const xseLog = join(documents, "F4SE", "f4se.log");
        writeFileSync(xseLog, "");
        const root = rootWithSettings(
            `${MANAGED_FALLOUT4}  Game Folder Path: '${game}'\n  Documents Folder Path: '${documents}'\n`,
        );

        const launch = ScanRunLaunch.targeted(root, [join(root, "crash-one.log")], {fcxMode: true});

        expect(launch.fcxEnabled).toBe(true);
        const context = launch.setupContext;
        expect(context?.gameRoot).toBe(game);
        expect(context?.docsRoot).toBe(documents);
        // Nothing is saved for the executable, so NextGen's own executable under the game folder.
        expect(context?.gameExePath).toBe(join(game, "Fallout4.exe"));
        expect(context?.xseLogPath).toBe(xseLog);
    });

    test("an uninspectable XSE log location throws the typed launch error", () => {
        // The YAML `\0` escape saves a documents folder no platform can inspect.
        const root = rootWithSettings(`${MANAGED_FALLOUT4}  FCX Mode: true\n  Documents Folder Path: "/bad\\0docs"\n`);

        let caught: unknown;
        try {
            ScanRunLaunch.standard(root);
        } catch (error) {
            caught = error;
        }

        expect((caught as { code?: string }).code).toBe("xse_log_inspect");
        expect((caught as { kind?: string }).kind).toBe("xse_log_inspect");
    });

    test("an unknown game-version override is rejected", () => {
        const root = rootWithSettings(MANAGED_FALLOUT4);

        expect(() => ScanRunLaunch.standard(root, {gameVersion: "Nonsense"})).toThrow();
    });
});
