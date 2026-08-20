# H0DN SN Ia multi-row provenance audit

Version `0.1.0` is a reproducible, bounded Phase 1B audit of the 277-row
Pantheon+ Hubble-flow input used by the frozen H0 Distance Network (H0DN)
repository.

Formal status:
`AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED`

Boundary marker:
`PROVENANCE_ONLY_NO_ROW_MODIFICATION_NO_COVARIANCE_CORRECTION_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

## Result

- All 277 H0DN rows map uniquely and one-to-one to all 277 official
  Pantheon+SH0ES rows with `USED_IN_SH0ES_HF=1`; no official row is reused.
- Catalog fields alone identify 275 rows. Two rows are catalog-only ambiguous
  and require the corresponding official STAT+SYS diagonal as a numerical
  fingerprint. No row remains ambiguous or unmatched after that second stage.
- The 30 multi-row exact-name groups contain 69 rows: 21 two-row groups and
  9 three-row groups. All 30 are `MULTI_SURVEY_ONLY`; same-survey repeat
  groups number zero.
- The 277-by-277 H0DN covariance is elementwise identical to the mapped
  official STAT+SYS submatrix: 76,729 of 76,729 `float64` values match and
  the maximum absolute difference is zero.

No numerical evidence of element loss, transcription change, additional
rounding, or row-order mismatch was found. This does not establish the
historical construction procedure or test whether the published covariance
is correctly calibrated.

## Matching dependency and error-field correction

Stage one uses only exact H0DN `name` = official `CID`, `m_b`/`m_b_corr`,
`zhel`/`zHEL`, and `zcmb`/`zCMB`, after restricting the official pool to
`USED_IN_SH0ES_HF=1`. Neither `m_b_corr_err_DIAG` nor a covariance value is
used at this stage. Only catalog-only ambiguous rows enter stage two, which
compares H0DN `err_m_b` with the square root of the corresponding printed
official STAT+SYS covariance diagonal.

The frozen README describes `m_b_corr_err_DIAG` as a covariance-diagonal
uncertainty, but the printed catalog values do not numerically equal the
square roots of the printed STAT+SYS covariance diagonal. The cause of this
documentation/data discrepancy is not determined here. For operational row
matching, H0DN `err_m_b` matches the latter at H0DN print precision.

Across the final 277 mapped rows, zero printed catalog values agree with the
printed-matrix square roots within `0.000000500001`; their maximum absolute
difference is `0.14130297508896889`. All 277 H0DN `err_m_b` values agree with
the matrix-derived values within `0.000005000001`; the maximum difference is
`4.959714075936095e-06`. These are numerical diagnostics, not a causal
explanation.

The final 277/277 mapping is a joint catalog-and-covariance lineage result.
Rows uniquely identified by catalog fields alone are reported separately
from rows requiring the official STAT+SYS diagonal as a numerical
fingerprint. The subsequent 76,729-element covariance comparison is
therefore not presented as fully independent of every input used in row
disambiguation.

## Protocol disclosure

The append-only ledger preserves all four amendments:

1. `AMEND-001` corrects one source-lock Git blob transcription; the frozen
   byte count and SHA-256 were already correct.
2. `AMEND-002` records 778 transpose-asymmetric elements in the printed
   official 1701-by-1701 covariance, without changing any value.
3. `AMEND-003` is interpretation-affecting. The initial error-field rule
   yielded zero candidates for all 277 rows; the covariance-diagonal rule
   was fixed before any corrected mapping, group, or lineage result was seen.
4. `AMEND-004` records this explanation and dependency correction with
   `results_observed=YES` and `interpretation_affected=NO`. It changes no
   mapping, survey classification, covariance equality, status, or boundary.

The result is reproducible but is an amended-protocol result, not a wholly
prospective confirmation under the initial matching rule.

## Package map

- `AUDIT_CONTRACT.md`: preserved initial frozen contract.
- `provenance/ACTIVE_MATCHING_CONFIG.json`: single active source for fields,
  tolerances, stage dependency, and the unresolved discrepancy label.
- `results/row_mapping.tsv`: final 277-row mapping.
- `results/row_mapping_dependency.tsv` and
  `results/row_mapping_dependency_summary.json`: catalog-only and
  covariance-assisted stages.
- `results/covariance_diagonal_required_rows.tsv`: the two rows requiring the
  matrix diagonal.
- `results/error_field_discrepancy_rows.tsv` and
  `results/error_field_discrepancy_summary.json`: the three-way error-field
  diagnostic.
- `results/multirow_group_summary.tsv`: 30-group survey ledger.
- `results/covariance_lineage.json`: exact submatrix comparison and its
  evidentiary limit.
- `scripts/verify_results.py`: independent parser and 18 final package gates.
- `REPORT.md` and `REPORT_JA.md`: English and Japanese interpretation.

Upstream data files are not redistributed.

## Quick reproduction

Python 3.12 and NumPy 2.3.5 were used for the delivered run.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt

python scripts/source_tools.py \
  --manifest provenance/SOURCE_LOCK.tsv \
  --acquire-root ../frozen-sources

python scripts/run_audit.py \
  --h0dn ../frozen-sources/H0DN \
  --pantheonplus ../frozen-sources/PantheonPlusSH0ES_DataRelease

python scripts/verify_results.py \
  --h0dn ../frozen-sources/H0DN \
  --pantheonplus ../frozen-sources/PantheonPlusSH0ES_DataRelease
```

See `REPRODUCIBILITY.md` for clean-room and packaging commands.

## Fixed source basis

- H0DN commit
  `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- Pantheon+SH0ES DataRelease commit
  `c447f0fea703fcd0fff57de5000947b5ca81286b`

All nine locked files are checked by commit, Git blob, byte count, and
SHA-256. The fixed repository README, catalog, and covariance are the
evidentiary sources; no mutable web issue is required.

## Scope

This package performs no row deletion, survey selection, covariance
correction, corrected `a_B`, `M_B`, `H0`, or Hubble-tension calculation.
Phase 1C is only a possible future audit and no Phase 1C result is included.

The audit code and original documentation are MIT licensed. Upstream data
retain their own terms. Keiji Yoshimura is the human author and final
responsible researcher; AI assistance is disclosed in
`AI_ASSISTANCE_DISCLOSURE.md`.
