/**
 * Display-label audit for the Node CLI.
 *
 * The other four frontends each have one of these; this one did not, and that is
 * the whole of what was wrong here. `cli/run-scan.ts` already renders the display
 * lines `classic-scan-presentation` produces and composes no sentences of its own
 * — it was migrated in the same sweep as the native frontends. What it lacked was
 * anything to keep it that way.
 *
 * That distinction matters, because the Python CLI was in exactly this position
 * once: correct on the day it was written, with no audit, and it is where a raw
 * Vocabulary Token survived after the same bug had been fixed in the TUI. An
 * unenforced frontend is not a compliant one; it is one whose next contributor has
 * nothing telling them the rule exists.
 *
 * What this proves is the narrow thing every frontend must prove: **it did not
 * reword what Rust handed it.** The deny-list is the shared file all five audits
 * read, so a phrase is added once rather than five times.
 *
 * The renderer-conformance half is deliberately not here — `cli.spec.ts` already
 * drives `renderDisplaySegment` through every kind, asserts a count prints Rust's
 * resolved noun, and asserts a path stays whole. Restating it would be a second
 * copy of an assertion that already exists.
 */

import { describe, expect, test } from "bun:test";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const CLI_DIR = join(import.meta.dir, "..", "cli");

/**
 * The shared deny-list of phrases about a Crash Log Scan Run that no frontend may
 * write, read from the file the other four audits read.
 *
 * `__test__/` sits at `node-bindings/classic-node/__test__`, so the repo root is
 * three levels up.
 */
const CORE_OWNED_PHRASES_FILE = join(
	import.meta.dir,
	"..",
	"..",
	"..",
	"business-logic",
	"classic-scan-presentation",
	"core-owned-phrases.txt",
);

/**
 * Every CLI source file this audit inspects.
 *
 * Written by hand rather than globbed, matching the other four: a declared list is
 * reviewable in a diff and lets a failure name the offending file. The coverage
 * test below is what stops it falling behind the directory.
 */
const AUDITED_SOURCES = ["main.ts", "run-scan.ts", "types.ts"] as const;

/** Reads the shared deny-list, dropping blank lines and `#` comments. */
function coreOwnedPhrases(): string[] {
	return readFileSync(CORE_OWNED_PHRASES_FILE, "utf8")
		.split("\n")
		.map((line) => line.trim())
		.filter((line) => line.length > 0 && !line.startsWith("#"));
}

/**
 * Returns the contents of every string and template literal in `source`, one per
 * line, with nothing else.
 *
 * Literals rather than comment-stripped code. Prose is only ever a literal, so
 * reading more than literals only adds ways to be wrong — and it was wrong in the
 * C++ ports this is a sibling of: `succeeded,` is core-owned prose that occurs
 * verbatim in ordinary code as `terminal.succeeded, terminal.failed`. Extracting
 * literals removes that whole class of false positive rather than asking the
 * deny-list to dodge it, and matches the Python audit, which reads literals off
 * the AST for the same reason.
 *
 * Comments never appear, for the reason the CXX parity gate's name scan was fixed:
 * a comment *describing* the drift is not the drift, and `run-scan.ts` carries
 * several that name the phrases this forbids while explaining why they are Rust's
 * to say. Tracking string state is what tells the two apart, and it also stops a
 * `//` inside a URL or path literal from reading as the start of a comment.
 *
 * Literals are newline-separated rather than concatenated so two adjacent ones
 * cannot form a phrase neither contains.
 *
 * Known gap, and harmless here: a regular-expression literal containing `//` or a
 * quote would confuse this, and neither audited file contains one. A false reading
 * there costs a false positive, not a silent pass.
 */
function stringLiterals(source: string): string {
	let out = "";
	let index = 0;

	while (index < source.length) {
		const character = source[index];

		if (character === "/" && source[index + 1] === "/") {
			while (index < source.length && source[index] !== "\n") {
				index += 1;
			}
			continue;
		}
		if (character === "/" && source[index + 1] === "*") {
			const close = source.indexOf("*/", index + 2);
			index = close === -1 ? source.length : close + 2;
			continue;
		}
		// One branch for all three quotes. A template literal is a string as far as
		// this is concerned: its fixed text is exactly where a rewritten sentence
		// would live, since `${…}` interpolation is how drift is spelled in
		// TypeScript.
		if (character === '"' || character === "'" || character === "`") {
			const quote = character;
			index += 1;
			while (index < source.length) {
				if (source[index] === "\\") {
					index += 2;
					continue;
				}
				if (source[index] === quote) {
					index += 1;
					break;
				}
				out += source[index];
				index += 1;
			}
			out += "\n";
			continue;
		}

		// Ordinary code, which is deliberately dropped rather than collected.
		index += 1;
	}

	return out;
}

/**
 * The sentence a frontend would reach for, written as the template it would
 * actually be written as.
 *
 * A template literal rather than a verbatim paste, because that is the shape drift
 * takes in TypeScript: the phrase survives and only the stage is interpolated.
 * Matching a phrase rather than a whole sentence is what lets the plain substring
 * test see through the interpolation.
 */
const REWORDED_SENTENCE = [
	"function summary(error: JsScanRunInfrastructureError): string {",
	"\treturn `Crash Log Scan Run failed during ${error.stage}`;",
	"}",
].join("\n");

describe("Node CLI display-label audit", () => {
	test("no CLI source writes a sentence the presentation crate owns", () => {
		// Deliberately scoped to the deny-list. A general "no template literals"
		// rule would be unworkably noisy — this CLI legitimately composes a great
		// deal of text that is Display Layout, including its own summary block,
		// its banner, and its argument errors.
		const phrases = coreOwnedPhrases();
		const offenders: string[] = [];

		for (const name of AUDITED_SOURCES) {
			const code = stringLiterals(
				readFileSync(join(CLI_DIR, name), "utf8"),
			);
			for (const phrase of phrases) {
				if (code.includes(phrase)) {
					offenders.push(`${name} writes ${JSON.stringify(phrase)}`);
				}
			}
		}

		expect(offenders).toEqual([]);
	});

	test("the shared deny-list is readable and not empty", () => {
		// The detector loops over the deny-list, so a truncated or mislocated list
		// asserts nothing while still reporting green — an audit that reads as
		// coverage while providing none. The other four audits carry the same guard
		// against the same file.
		const phrases = coreOwnedPhrases();

		expect(phrases.length).toBeGreaterThanOrEqual(10);
		expect(phrases).toContain("Crash Log Scan Run failed during");

		// No constraint on an entry's shape is asserted, and that is deliberate. An
		// earlier version of the native ports required each entry to contain a
		// space, because they searched comment-stripped *code* and a bare word
		// could match an identifier. That constraint was load-bearing only because
		// those detectors read more than they needed: `stringLiterals` yields
		// literals alone, where no identifier can appear, so `succeeded,` — which
		// occurs in ordinary code as `terminal.succeeded, terminal.failed` — is
		// safe to list.
	});

	test("the phrase detector catches the drift it exists for", () => {
		// This CLI writes none of these phrases now, so a broken detector and a
		// compliant frontend look identical from here. Feeding the detector the
		// drift it exists to catch is what tells the two apart.
		expect(stringLiterals(REWORDED_SENTENCE)).toContain(
			"Crash Log Scan Run failed during",
		);
	});

	test("the phrase detector reads code rather than comments", () => {
		// Load-bearing for this frontend specifically: `run-scan.ts` explains in
		// prose why `Crash Log Scan Run failed during` is Rust's to say. A detector
		// that could not tell a comment from a literal would fail on the very
		// comment documenting the fix.
		const commented = stringLiterals(
			[
				"// Crash Log Scan Run failed during is core's to say.",
				"/* Crash Log Scan Run failed during, again. */",
				"const x = 1;",
			].join("\n"),
		);
		expect(commented).not.toContain("Crash Log Scan Run failed during");

		const written = stringLiterals(
			'const s = "Crash Log Scan Run failed during";',
		);
		expect(written).toContain("Crash Log Scan Run failed during");
	});

	test("the phrase detector does not mistake a literal slash for a comment", () => {
		// A URL or path literal must not read as the start of a comment, or
		// everything after it on that line silently leaves the audited text —
		// including a phrase written there.
		const code = stringLiterals(
			[
				'const url = "https://example.invalid";',
				'const s = `Crash Log Scan Run failed during ${stage}`;',
			].join("\n"),
		);
		expect(code).toContain("Crash Log Scan Run failed during");
	});

	test("the phrase detector reads literals rather than the code around them", () => {
		// `succeeded,` is core-owned prose and also, character for character, an
		// ordinary argument list. A detector that searched code rather than
		// literals reported the Qt GUI's `emit finished(terminal.succeeded,
		// terminal.failed, ...)` as drift, which is why all four source-scanning
		// ports extract literals.
		expect(
			stringLiterals("emit finished(terminal.succeeded, terminal.failed);"),
		).not.toContain("succeeded,");
		expect(stringLiterals('const s = "3 succeeded, 4 failed";')).toContain(
			"succeeded,",
		);

		// Two adjacent literals must not fuse into a phrase neither contains, or
		// the separator this relies on is doing nothing.
		expect(stringLiterals('const s = "succeeded" + ", failed";')).not.toContain(
			"succeeded,",
		);
	});

	test("the phrase detector leaves compliant rendering alone", () => {
		// The other half of the proof. Concatenating segments Rust produced is the
		// correct shape and must stay quiet, or the audit becomes noise a
		// contributor learns to work around.
		const compliant = stringLiterals(
			"return line.segments.map(renderDisplaySegment).join(' ');",
		);
		for (const phrase of coreOwnedPhrases()) {
			expect(compliant).not.toContain(phrase);
		}
	});

	test("the audit covers every CLI source file", () => {
		// The stale-list guard every one of these audits carries. Without it a new
		// file under `cli/` would be unaudited from the day it lands — and a
		// rewritten sentence is likelier to appear in new code than in old.
		//
		// Set equality rather than a subset check, so a listed-but-deleted file
		// fails too, matching the Python audit's stricter form.
		const present = readdirSync(CLI_DIR, { recursive: true })
			.map((entry) => String(entry).replaceAll("\\", "/"))
			.filter((entry) => entry.endsWith(".ts"))
			.sort();

		expect(present).toEqual([...AUDITED_SOURCES].sort());
	});
});
