#!/usr/bin/env node

import {basename} from "node:path";
import type {CliOptions} from "./types";
import {getSupportedGameVersions, runCli} from "./run-scan";

function printHelp(): void {
    const gameVersionModes = getSupportedGameVersions("Fallout4", __dirname).join(", ");

    console.log("CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker");
    console.log("");
    console.log("Options:");
    console.log("  --game <name>             Game to scan: Fallout4 (default: the managed game)");
    console.log(`  --game-version <mode>     ${gameVersionModes}`);
    console.log("  --scan-path <path>        Custom crash log directory");
    console.log("  --fcx-mode                Enable FCX enhanced analysis");
    console.log("  --show-fid-values         Show FormID database values");
    console.log("  --simplify-logs           Remove specified strings from logs");
    console.log("  --max-concurrent <n>      Max parallel scans (0=auto, 1-32 explicit)");
    console.log("  --version                 Print version and exit");
    console.log("  --json                    Emit structured output for automation");
    console.log("  --help                    Print help and exit");
}

function parseInteger(value: string, flag: string): number {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isInteger(parsed) || parsed < 0 || parsed > 32) {
        throw new Error(`${flag} must be an integer between 0 and 32`);
    }
    return parsed;
}

/**
 * The `--game` values this CLI accepts, matching the native C++ CLI (`classic-cli/src/cli_args.cpp`).
 *
 * Only Fallout 4 is offered: widening the flag to Fallout 4 VR or other games is out of scope
 * for the CLIs, so other tokens are refused here at parse time rather than launched. Omitting
 * `--game` is still allowed and scans the managed game, which may be Fallout 4 VR.
 */
const ACCEPTED_GAMES: readonly string[] = ["Fallout4"];

/**
 * Validates one `--game` value against {@link ACCEPTED_GAMES}.
 *
 * @throws Error naming the accepted values when `value` is not one of them (case-sensitive,
 *     like the native CLI).
 */
function parseGame(value: string): string {
    if (!ACCEPTED_GAMES.includes(value)) {
        throw new Error(`--game must be one of: ${ACCEPTED_GAMES.join(", ")} (got ${value})`);
    }
    return value;
}

function requireValue(flag: string, value: string | undefined): string {
    if (!value) {
        throw new Error(`${flag} requires a value`);
    }
    return value;
}

function parseArgs(argv: string[]): CliOptions {
    // No default game: an absent `--game` lets the launch scan the managed game.
    const options: CliOptions = {
        version: false,
        json: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const argument = argv[index];

        switch (argument) {
            case "--help":
            case "-h":
                printHelp();
                process.exit(0);
                break;
            case "--game": {
                options.game = parseGame(requireValue(argument, argv[index + 1]));
                index += 1;
                break;
            }
            case "--game-version": {
                const value = requireValue(argument, argv[index + 1]);
                options.gameVersion = value;
                index += 1;
                break;
            }
            case "--scan-path":
                options.scanPath = requireValue(argument, argv[index + 1]);
                index += 1;
                break;
            case "--fcx-mode":
                options.fcxMode = true;
                break;
            case "--show-fid-values":
                options.showFidValues = true;
                break;
            case "--simplify-logs":
                options.simplifyLogs = true;
                break;
            case "--max-concurrent":
                options.maxConcurrent = parseInteger(requireValue(argument, argv[index + 1]), argument);
                index += 1;
                break;
            case "--version":
                options.version = true;
                break;
            case "--json":
                options.json = true;
                break;
            default:
                throw new Error(`Unknown argument: ${argument}`);
        }
    }

    return options;
}

async function main(): Promise<void> {
    try {
        const options = parseArgs(process.argv.slice(2));
        const result = await runCli(options, __dirname);
        process.exit(result.exitCode);
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const executable = basename(process.argv[1] ?? "classic-node");
        console.error(`${executable}: ${message}`);
        process.exit(1);
    }
}

void main();
