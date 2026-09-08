# Evidence retirement readiness

Issue #216 cannot remove the migration ledger yet. The ledger remains diagnostic;
this audit does not grant runtime coverage or replace executed conformance.

A static audit of all live parity occurrences against validated scenario packs
and `FAMILY_COVERAGE_POLICIES` found:

| Disposition | Occurrences |
| --- | ---: |
| Source-derived structural evidence | 309 |
| Runtime row with at least one potential predicate | 816 |
| Runtime row with no matching predicate | 1,657 |
| Total | 2,782 |

The unmatched runtime rows comprise 315 CXX, 464 Node, and 878 Python occurrences.
The audit uses the same canonical crate/symbol, explicit binding selector, public
operation filter, and retained-operation exclusions as row coverage derivation.
A potential predicate is only a migration candidate: its presence does not prove
that an applicable participant executed it or that any receipt passed.

Concrete unmatched CXX examples include:

- `ExplicitYamlDataSnapshot.explicit_yaml_data_snapshot_game`
  (`parity:cxx:fff0494d03d2c5be`).
- `load_main_yaml_version_with_bundled_dir` exposed as `load_main_yaml_version`
  (`parity:cxx:b0d609f9ed78e468`).
- `LocalIgnoreRecoveryPlan.local_ignore_recovery_plan_diagnostics`
  (`parity:cxx:042ea4bfbf165c0c`).

Existing tests and source parity still own their existing assertions, but cannot
be relabelled as receipt-derived runtime proof. The remaining occurrences need
executable predicates and applicable participant observations, or a justified
permanent structural/negative disposition or reviewed policy exception, before
final retirement. Counts are a point-in-time diagnostic, not an activation list
or a checked coverage baseline.

The permanent analyzer definitions now live in
`tools/binding_compliance/retained_analyzers.py`; executable coverage no longer
imports them from `migration_ledger.py`. This removes that production dependency
without deleting unresolved migration obligations.
