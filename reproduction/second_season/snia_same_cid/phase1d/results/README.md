# Result files

## Formal status and summaries

- `EXECUTION_STATUS.json`: formal status, release-sufficiency class, and
  corrected evidence boundaries.
- `audit_summary.json`: aggregate main findings, explicit interpretation
  aliases, and non-claims.
- `final_verification_summary.json`: recorded strict closure result from the
  otherwise read-only verifier.
- `input_inventory.json`: frozen Phase 1B audit population.
- `photometry_scan_summary.json`: directory-level active-file scan.
- `run_environment.json`: runtime identity.

## Main evidence ledgers

- `row_lineage.tsv`: one record for each of 69 final distance rows.
- `candidate_file_evidence.tsv`: 38 frozen-crosswalk-compatible input-candidate
  records.
- `group_lineage.tsv`: one record for each of 30 same-CID groups.
- `pair_observation_overlap.tsv`: all 48 within-group row pairs.
- `pipeline_anchor_evidence.tsv`: 12 exact public-configuration anchors.
- `referenced_asset_availability.tsv`: three predeclared referenced assets.
- `shared_dependency_ledger.tsv`: bounded dependency-layer interpretation.

Legacy tokens are retained to preserve the original machine-result interface.
`UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE` is interpreted as
`UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE`, and
`NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE` as
`NO_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE`. Neither token proves direct
ancestry to a final measurement. Every affected ledger states
`direct_final_measurement_ancestry = NOT_ESTABLISHED`.

The 12 configuration anchors are bounded by
`CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY` and
`NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF`.

## Verification records

- `contract_verification.json`
- `source_verification.json`
- `independent_verification.json`: within-project main
  second-implementation cross-check.
- `unit_tests.log`
- `clean_reproduction.log`
- `clean_reproduction_summary.json`

The second-implementation record is not an independent external replication,
peer review, or expert endorsement.

## Post-hoc clarification

- `posthoc_cid_only_crosswalk_diagnostic.tsv`: 31 unresolved main rows searched
  by exact CID alone.
- `posthoc_cid_only_candidate_files.tsv`: 73 corresponding candidates.
- `posthoc_cid_only_crosswalk_summary.json`: aggregate diagnostic and hashes of
  protected main files.
- `posthoc_cid_only_crosswalk_independent_verification.json`: within-project
  second-implementation recomputation of the diagnostic.

These four files are explicitly post-hoc and non-promoting. They do not
replace or modify any main ledger, and their candidates do not establish
direct final-measurement ancestry.
