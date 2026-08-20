# Phase 1B report: exact-name multi-row provenance

## Executive finding

The final mapping is a joint catalog-and-covariance lineage result. Of 277
H0DN Hubble-flow rows, 275 are uniquely identified using catalog fields
alone. The two rows named `2009cz` are catalog-only ambiguous and require the
official STAT+SYS diagonal as a numerical fingerprint. After that declared
second stage, all 277 rows map one-to-one to the complete official
`USED_IN_SH0ES_HF=1` subset, with no unmatched row, ambiguity, or reused
official row.

All 30 exact-name multi-row groups are cross-survey groups and none is a
same-survey repeat. The mapped 277-by-277 official STAT+SYS submatrix equals
the H0DN covariance in all 76,729 `float64` elements, with maximum absolute
difference zero.

Formal status:
`AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED`

Boundary marker:
`PROVENANCE_ONLY_NO_ROW_MODIFICATION_NO_COVARIANCE_CORRECTION_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

## Question and fixed sources

Phase 1A localized unusually low residual chi-square to 39 duplicate-name
contrast degrees of freedom. Exact string equality alone did not determine
why those rows repeat or whether their covariance values and order correspond
to the official release. Phase 1B therefore asks which official row and
survey code correspond to each H0DN row, and whether the resulting covariance
submatrix is numerically identical.

| Source | Fixed commit | Principal files |
| --- | --- | --- |
| H0DN | `cc0a4b9f36e65470d514f254a3c5cffa463fbd94` | `data/sn1a_hf_pp.dat`, `data/sn1a_covar_pp.dat` |
| Pantheon+SH0ES DataRelease | `c447f0fea703fcd0fff57de5000947b5ca81286b` | `Pantheon+SH0ES.dat`, `Pantheon+SH0ES_STAT+SYS.cov` |

The source register locks nine files, including the relevant READMEs, by
commit, Git blob, byte count, and SHA-256. Upstream bytes are not
redistributed.

## Corrected two-stage mapping

Candidates are always restricted to official rows with
`USED_IN_SH0ES_HF=1`. The active configuration is
`provenance/ACTIVE_MATCHING_CONFIG.json`.

Stage one uses only:

- exact H0DN `name` = official `CID`;
- absolute `m_b` versus `m_b_corr` difference at most
  `0.000500000001`;
- absolute `zhel` versus `zHEL` and `zcmb` versus `zCMB` differences at most
  `0.000005000001`.

It does not use `m_b_corr_err_DIAG` or any covariance value. Each H0DN row is
then classified as `CATALOG_ONLY_UNIQUE`, `CATALOG_ONLY_AMBIGUOUS`, or
`CATALOG_ONLY_UNMATCHED`.

Only a catalog-only ambiguous row enters stage two. Its H0DN `err_m_b` must
agree with the square root of the candidate official STAT+SYS covariance
diagonal within `0.000005000001`. The resulting dependency class is
`COVARIANCE_DIAGONAL_REQUIRED`, `AMBIGUOUS_AFTER_ALL_RULES`, or
`UNMATCHED_AFTER_ALL_RULES`.

Candidates are sorted by fixed official row index, `CID`, then `IDSURVEY`.
There are no aliases, case conversion, fuzzy matching, manual assignments, or
order-based tie-breaks.

| Mapping dependency | Rows |
| --- | ---: |
| `CATALOG_ONLY_UNIQUE` | 275 |
| `CATALOG_ONLY_AMBIGUOUS` | 2 |
| `CATALOG_ONLY_UNMATCHED` | 0 |
| `COVARIANCE_DIAGONAL_REQUIRED` | 2 |
| `AMBIGUOUS_AFTER_ALL_RULES` | 0 |
| `UNMATCHED_AFTER_ALL_RULES` | 0 |
| Final one-to-one matches | 277 |
| Reused official rows | 0 |

The two covariance-required rows and every candidate-level delta are recorded
in `results/covariance_diagonal_required_rows.tsv` and
`results/row_mapping_dependency.tsv`.

## `m_b_corr_err_DIAG` diagnostic

The frozen README describes `m_b_corr_err_DIAG` as a covariance-diagonal
uncertainty, but the printed catalog values do not numerically equal the
square roots of the printed STAT+SYS covariance diagonal. The cause of this
documentation/data discrepancy is not determined here. H0DN `err_m_b`
matches the matrix-derived values at the H0DN print tolerance.

| Diagnostic across the mapped 277 rows | Result |
| --- | ---: |
| Catalog versus matrix within `0.000000500001` | 0 |
| Catalog versus matrix maximum absolute difference | `0.14130297508896889` |
| H0DN versus matrix within `0.000005000001` | 277 |
| H0DN versus matrix maximum absolute difference | `4.959714075936095e-06` |
| Cause classification | `UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY` |

This records an observed numerical relation; it does not select among
rounding, version, generation, documentation, or other possible causes.

## Multi-row groups

| Quantity | Result |
| --- | ---: |
| Exact-name multi-row groups | 30 |
| Rows in those groups | 69 |
| Two-row groups | 21 |
| Three-row groups | 9 |
| `MULTI_SURVEY_ONLY` | 30 |
| `SAME_SURVEY_REPEATED` | 0 |
| `MIXED_SURVEY_MULTIPLICITY` | 0 |

The survey-row counts in the 69-row focus set are CSP 16, LOSS1 7, SOUSA 3,
LOSS2 16, CFA2 1, CFA3S 3, CFA3K 15, and CFA4p2 8. Complete evidence is in
`results/multirow_group_summary.tsv` and
`results/multirow_row_evidence.tsv`.

## Covariance comparison and evidentiary limit

The final official index sequence extracts a 277-by-277 submatrix from the
unmodified printed 1701-by-1701 STAT+SYS covariance.

| Diagnostic | Result |
| --- | ---: |
| Elements compared | 76,729 |
| Exactly equal elements | 76,729 |
| Mismatches | 0 |
| Maximum absolute difference | 0 |

This is elementwise `float64` equality, not an `allclose` comparison. No
numerical evidence of element loss, transcription change, additional
rounding, or row-order mismatch was found. Equality does not by itself prove
the historical construction procedure.

The printed full official matrix has 778 entries unequal to their transpose
partners, with maximum absolute difference
`3.0000000000038676e-08`. `AMEND-002` records this diagnostic. No value is
symmetrized, averaged, rounded, or replaced before the primary comparison.

Because the official diagonal disambiguates two rows, the subsequent
76,729-element comparison is not represented as fully independent of every
input used in mapping. This dependency is explicit in the row ledgers and
machine-readable summary.

## Scientific interpretation

Within the two fixed repositories, Phase 1B finds no support for explaining
the Phase 1A localization through a missing Hubble-flow row, an assignment
reuse, a same-survey repeated row, a mapped row-order mismatch, or a numerical
submatrix transcription difference. It does not establish that the published
covariance is calibrated, identify the cause of low chi-square, or make a
causal claim.

A covariance-calibration audit could be a later Phase 1C, but no such test or
result is part of this package.

## Protocol integrity

The original contract and `AMEND-001` through `AMEND-003` remain preserved.
`AMEND-003` records that the initial `m_b_corr_err_DIAG` comparison produced
zero candidates for all 277 rows and that the corrected matrix-diagonal rule
was fixed before corrected mapping results were viewed.

`AMEND-004` has `results_observed=YES` and
`interpretation_affected=NO`. It removes an unsupported description,
separates catalog-only identification from covariance-assisted
disambiguation, records the unresolved documentation/data discrepancy, and
limits the covariance claim to observed numerical equality. The 277/277
mapping, group classifications, covariance values, formal status, and
scientific boundary are unchanged.

## Non-claims

This audit performs no row modification, covariance correction, survey
selection, corrected `a_B`, `M_B`, `H0`, or Hubble-tension significance. It
does not establish statistical independence of rows, endorse either upstream
project, or constitute peer review.
