# Result index

Start with `audit_summary.json`.

## Provenance and inputs

- `contract_verification.json`
- `source_verification.json`
- `input_inventory.json` (277 rows; 238 exact-name groups; 30 multi-row
  groups containing 69 rows; 39 excess rows / contrast degrees of freedom)
- `run_environment.json`

## Scientific calculation

- `primary_partition.json`
- `reference_partition.json`
- `partition_summary.tsv`
- `statistical_interpretation.json`
- `audit_summary.json`

## Numerical verification

- `baseline_reproduction.json`
- `baseline_reproduction.tsv`
- `numerical_crosschecks.json`
- `numerical_crosschecks.tsv`
- `permutation_invariance_summary.json`
- `permutation_invariance.tsv`
- `monte_carlo_null_check.json`
- `monte_carlo_null_check.tsv`
- `unit_tests.log`
- `clean_reproduction_summary.json`
- `clean_reproduction.log`
- `final_verification_summary.json`

The clean-reproduction summary records parsed-JSON semantic equality,
serialized-byte equality, and both SHA-256 values as separate fields.
`final_verification_summary.json` is the saved closure-time, pre-manifest
record. Run `python scripts/verify_results.py` for a complete read-only live
check that also covers the manifests.

`run_stdout.log` and `run_stderr.log` preserve the primary execution streams.
