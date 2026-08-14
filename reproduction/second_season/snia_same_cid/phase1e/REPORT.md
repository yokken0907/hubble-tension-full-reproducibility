# Phase 1E report: public crosswalk for IDSURVEY 51, 57, and 65

## Result

A crosswalk inferred without using any CID from the 30 same-CID groups found
one compatible active public photometry input candidate for each of the 31
target rows under the frozen Phase 1E rules.

Formal status:
`AUDIT_COMPLETE_TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_CLASSIFIED`.

Scientific classification:
`PUBLIC_INTERNAL_CROSSWALK_SUPPORTED_3_OF_3_TARGET_ROWS_UNIQUE_31_OF_31`.

This is not an official `SURVEY.DEF` reconstruction. It is a reproducible
internal association among layers of the frozen public DataRelease.

The uniqueness and crosswalk classifications hold within the prospectively frozen seven-directory public-photometry audit universe. They do not establish uniqueness across every public photometry directory or any external archive.

The seven prospectively frozen directories are `CSPDR3_anthony`, `CSP_data2`,
`SWIFT`, `LOSS`, `KAIT_DS15`, `CfA3_DJ20`, and
`PS1_LOWZ_COMBINED_TEXT_DS17`.

## Anti-circular inference

The Phase 1D post-hoc candidate patterns were known before Phase 1E. They are
fully disclosed. The audit therefore excluded every CID in the 30 Phase 1B
multi-row groups from crosswalk inference. An anchor had to be a target-code
row with a CID occurring once in the full 1701-row catalog and exactly one
active exact-CID photometry file across the seven-directory universe.

The support threshold was prospectively hash-frozen at five anchors or more,
including at least three Hubble-flow anchors, with one and only one source
directory across all anchors.

## Crosswalk evidence

| IDSURVEY | Public label | Eligible | Anchors | HF anchors | Directory | Raw header |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 51 | LOSS1 | 22 | 19 | 6 | `LOSS` | `KAIT` |
| 57 | LOSS2 | 39 | 31 | 8 | `KAIT_DS15` | `KAITM` |
| 65 | CFA4p2 | 13 | 12 | 8 | `PS1_LOWZ_COMBINED_TEXT_DS17` | `PS1_LOWZ_COMBINED(CFA4p1)` |

Sixty-two of 74 eligible rows were unambiguous anchors. The remaining 12 had
multiple exact-CID files and were not selected or manually adjudicated.

The inferred mappings classified exactly one compatible candidate for 7/7,
16/16, and 8/8 target rows for codes 51, 57, and 65. The frozen legacy status
`UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK` remains in the primary ledger,
but its preferred meaning is
`UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE`.

This classification does not prove direct ancestry to the final `m_b_corr`
row, identity of the exact light-curve fit or FITRES row, identity of the
bias-correction run, executed-run-to-final-catalog lineage, or statistical
independence.

## Accepted corrected Phase 1D dependency

Phase 1E prospectively froze the original Phase 1D archive hash before the
Phase 1E result was known. That original freeze is retained byte-for-byte. The
later accepted corrected Phase 1D archive is recorded separately as a
post-result upstream supersession with SHA-256
`6792886b8f1a8ac6397e6305931bfc750fdf1f1211c5e92b1f07ea1e7f0609bd`.

The corrected Phase 1D row ledger adds interpretation fields but preserves all
original columns. A canonical comparison of the 31 target-driving rows over
`h0dn_row_1based`, `official_row_1based`, `CID`, `IDSURVEY`, and legacy
`lineage_status` is identical. The Phase 1E target population and scientific
counts therefore do not change.

## Metadata tension

The official label for code 65 contains `CFA4p2`, while every target-excluded
anchor for that code carries the raw header token `CFA4p1`. This is classified
as `PUBLIC_LABEL_RAW_HEADER_CFA_TOKEN_MISMATCH`. The audit does not decide
which naming layer is historically authoritative and does not infer an error
in the measured quantities.

## Verification and boundary

The second internal implementation cross-check passed 24/24 checks, 36/36 unit
and regression tests passed, and an isolated reproduction regenerated 15/15
protected result files byte for byte. This is not an external independent
replication, peer review, or expert endorsement.

No row, label, fit, covariance, or Hubble-constant estimate is changed. The
audit makes no survey ranking, residual-anomaly, causal, new-physics, or
Hubble-tension-resolution claim.
