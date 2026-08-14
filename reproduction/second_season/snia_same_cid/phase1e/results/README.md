# Result files

## Primary result

- `EXECUTION_STATUS.json`: formal status and bounded scientific classification.
- `audit_summary.json`: aggregate result and non-claims.
- `inferred_crosswalk.tsv`: three code-level target-excluded crosswalks.
- `target_row_application.tsv`: one record for each of the 31 Phase 1E targets.
- `target_candidate_file_evidence.tsv`: the 31 corresponding file records.
- `label_header_diagnostic.tsv`: code-65 label/raw-header token comparison.
- `status_semantics.json`: preferred candidate interpretations and explicit
  non-ancestry boundaries for frozen legacy status identifiers.

The uniqueness and crosswalk classifications hold within the prospectively frozen seven-directory public-photometry audit universe. They do not establish uniqueness across every public photometry directory or any external archive.

The seven directories are `CSPDR3_anthony`, `CSP_data2`, `SWIFT`, `LOSS`,
`KAIT_DS15`, `CfA3_DJ20`, and `PS1_LOWZ_COMBINED_TEXT_DS17`.

`UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK` remains the legacy value in
`target_row_application.tsv`. Its preferred label is
`UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE`: one active public
photometry input candidate matched the exact CID, inferred source directory,
and accepted raw `SURVEY` vocabulary within the frozen seven-directory
universe. It does not prove direct final-`m_b_corr` ancestry, exact fit-output
identity, bias-correction-run identity, executed-run-to-final-catalog lineage,
or statistical independence.

`NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE` is likewise a legacy Phase 1D status. It
means no compatible candidate under the Phase 1D frozen crosswalk; it does not
mean that no public photometry file exists.

## Target-excluded inference evidence

- `holdout_candidate_rows.tsv`: all 74 eligible target-excluded catalog rows.
- `holdout_anchor_evidence.tsv`: the 62 rows with exactly one exact-CID active
  file across the seven-directory universe.

Rows with multiple candidates remain in the candidate ledger but do not enter
the inferred crosswalk.

## Verification

- `contract_verification.json`
- `source_verification.json`
- `independent_verification.json`: second-implementation internal cross-check;
  not an external replication or expert endorsement.
- `unit_tests.log`
- `clean_reproduction_summary.json`
- `clean_reproduction.log`
- `final_verification_summary.json`

The original frozen Phase 1D ledger remains under `provenance/` byte-unchanged.
The accepted corrected Phase 1D ledger and summary are stored under separate
names with a non-retroactive supersession record. Phase 1E does not overwrite
its prospective freeze or a Phase 1D result.
