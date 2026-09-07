# Focused semantic conformance equivalence

Issue #205 promotes six independent v1 families to blocking receipt enforcement:
Crash Suspect, Crashgen Settings, Mod Guidance, FormID lookup, Named Record, and
Plugin Evidence. Each family keeps its domain observations and invokes its
existing public Rust, CXX, Node, and Python operations. No production API or
binding declaration is introduced by this migration.

## Fixture and expectation ownership

The shared inputs under `tests/fixtures/semantic_conformance/<family>/` extract
the deterministic fixture values embedded in the retained Python and Node
public-seam tests. Those tests include `test_crash_suspect_analyzer.py`,
`test_crashgen_settings_analyzer.py`, `test_mod_guidance_analyzer.py`,
`test_formid_value_lookup.py`, `test_named_record_finding_analyzer.py`, and
`test_plugin_evidence_analyzer.py` under `python-bindings/tests/`, with their
counterparts under `node-bindings/classic-node/__test__/`.

The tracked packs under `tests/conformance/packs/<family_with_underscores>/`
own expected observations independently of all adapter outputs. Prepared plans
carry only scenario inputs, fixture paths, and normalization policy. An adapter
cannot obtain expected observations from that plan. Central comparison checks
the complete typed projection, including explicit nulls, ordered findings, and
structured errors; coverage comes from trusted predicates over authenticated
observations.

| Family | Retained facts reused by the pack | Replacement observations |
| --- | --- | --- |
| `crash-suspect` | Main-error and stack rules, DLL involvement, empty result after prior use, malformed rule input | Ordered finding kinds and rule identity/severity; successful empty findings; analyzer kind and structured configuration failure |
| `crashgen-settings` | Authored crashgen rules, failing and passing setting checks, clean settings after prior use, unsupported version | Exact authored notice/issue/success guidance, populated section/setting and expected/actual values, separate disabled-setting notices, successful empty result, distinct unsupported-version failure |
| `mod-guidance` | Matched authored guidance, absent-mod remediation, empty selection, invalid configuration | Ordered guidance/remediation findings, authored messages, distinct empty success and typed failure |
| `formid-lookup` | In-memory found/missing/disabled outcomes, repeated lookup, blank values, injected operational errors, batch and backend operations | Exact found value, explicit missing/disabled status, ordered batch results, typed error code/message and queried FormID/plugin |
| `named-record` | Counted named records, clean input after prior use, invalid configuration | Ordered names/counts, successful empty findings, typed configuration failure |
| `plugin-evidence` | Counted plugin evidence, clean input after prior use, invalid configuration | Ordered plugin/count observations, successful empty evidence, typed configuration failure |

The Mod Guidance authored-guidance fixture also exercises non-null plugin
exclusions: a nonmatching exclusion preserves installed-mod guidance, while a
matching exclusion suppresses the excluded mod. Its expected findings stay
explicit in the pack, so dropping exclusions or decoding their shared array
carrier incorrectly fails the same public-operation receipt comparison.

The families make no frontend consumer claim: their applicable denominator is
the four semantic adapters, with CXX represented by both `windows-msvc` and
`windows-clang-cl`. Existing Crash Log Scan Run and User Settings consumer
obligations remain separate.

## Same-revision execution

`tools/binding_compliance/run_semantic_conformance.py --family <family>
--participant <rust|node|python>` uses the existing shared lifecycle to prepare a
fresh invocation, run the adapter with a bounded timeout, preserve command
diagnostics, and compare its receipt. Native CXX uses
`tools/binding_compliance/conformance/adapters/run_cxx_conformance.ps1 -Family
<family> -Compiler <msvc|clang-cl>` and invokes only
`classic-cli/build_cli.ps1 -Test -CTestName classic-cxx-conformance`. CXX receipt
validation also authenticates the native attempt and JUnit evidence.

CI runs each family as a separate blocking step after the retained runtime
suite in the same checkout. A preceding failure does not skip later receipt
attempts unless the job is cancelled; each family uploads diagnostics even on
failure. The Node runtime matrix and both native compilers retain fail-fast
disabled. The static workflow policy rejects missing families, missing native
instances, weakened conditions, nonblocking steps, and checkout revision
overrides. Its CLI job budget includes the retained suite and ten bounded
receipt launches.

These commands describe required execution, not a claim that a particular
local or CI run has passed. Passing artifacts for the exact source revision are
the execution evidence; neither this map nor the diagnostic migration ledger
can grant receipt coverage.

## Evidence deliberately retained

All old runtime registry entries, positive coverage evidence, focused Rust and
binding tests, signature inventories, declaration/stub freshness checks,
compile-only type negatives, forbidden-export checks, and structural parity
gates remain in place. SQLite integration, cache behavior, detailed rule
diagnostics, and other lower-level facts retain their existing tests.

Migrated semantic rows require valid executable receipts even while their old
registry entries remain. No old evidence is retired by #205. Removing a later
registry row or focused test requires a separate fact-by-fact equivalence
decision backed by the actual replacement execution.
