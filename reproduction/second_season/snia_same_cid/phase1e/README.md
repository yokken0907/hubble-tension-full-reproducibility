# H0DN SN Ia survey-code crosswalk audit (Phase 1E)

This repository audits the three Pantheon+SH0ES `IDSURVEY` codes that remained
unresolved in Phase 1D: `51`, `57`, and `65`.

The central safeguard is target exclusion. No CID from the 30 same-CID groups
is permitted to define the crosswalk. Instead, exact-CID matches from unique
official-catalog rows outside those groups are used as anchors. A crosswalk is
accepted only when it meets the prospectively hash-frozen minimum-support and
single-directory rules.

## Result

Formal status:
`AUDIT_COMPLETE_TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_CLASSIFIED`

Scientific classification:
`PUBLIC_INTERNAL_CROSSWALK_SUPPORTED_3_OF_3_TARGET_ROWS_UNIQUE_31_OF_31`

| IDSURVEY | Official label | Target-excluded anchors | HF anchors | Inferred public directory | Exact raw `SURVEY` header | Phase 1E targets |
| ---: | --- | ---: | ---: | --- | --- | ---: |
| 51 | LOSS1 | 19/22 | 6 | `LOSS` | `KAIT` | 7/7 compatible candidates |
| 57 | LOSS2 | 31/39 | 8 | `KAIT_DS15` | `KAITM` | 16/16 compatible candidates |
| 65 | CFA4p2 | 12/13 | 8 | `PS1_LOWZ_COMBINED_TEXT_DS17` | `PS1_LOWZ_COMBINED(CFA4p1)` | 8/8 compatible candidates |

The uniqueness and crosswalk classifications hold within the prospectively frozen seven-directory public-photometry audit universe. They do not establish uniqueness across every public photometry directory or any external archive.

For each of the 31 target rows, exactly one active public photometry input
candidate matched the exact CID, inferred source directory, and accepted raw
`SURVEY` vocabulary within that frozen universe. The preferred interpretation
is `UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_PUBLIC_INPUT_CANDIDATE`. It does not
establish direct ancestry to the final `m_b_corr` row, the exact light-curve
fit or FITRES row, the bias-correction run, executed-run-to-final-catalog
lineage, or statistical independence. The legacy
`UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK` value remains unchanged in the
primary target ledger for reproducibility.

The code-65 official-label token (`CFA4p2`) and raw-header token (`CFA4p1`)
do not match. This is reported as descriptive public metadata tension only.
The audit does not decide which naming layer is historically or physically
authoritative and changes neither source.

The result is a public-release-internal crosswalk, not an official
`SURVEY.DEF` reconstruction. The accepted corrected Phase 1D package is
recorded as a post-result upstream supersession, not substituted into the
prospective Phase 1E freeze. The original freeze remains byte-unchanged. The
corrected Phase 1D ledger preserves all original columns and the 31-row target
population while adding interpretation fields; therefore the Phase 1E counts
and classifications are unchanged.

## Reproduce

Requirements: Python 3.11 or newer, Git, and a checkout of the frozen
Pantheon+SH0ES DataRelease commit.

```bash
python3 scripts/run_audit.py --pantheonplus /path/to/DataRelease
python3 scripts/independent_verify.py --pantheonplus /path/to/DataRelease
python3 -m unittest discover -s tests -v
python3 scripts/clean_reproduce.py --pantheonplus /path/to/DataRelease
python3 scripts/verify_results.py \
  --pantheonplus /path/to/DataRelease \
  --phase1d-corrected-zip /path/to/h0dn-snia-same-cid-measurement-lineage-audit_v0.1.0.zip \
  --phase1d-corrected-sidecar /path/to/h0dn-snia-same-cid-measurement-lineage-audit_v0.1.0.zip.sha256
```

The required DataRelease commit is
`c447f0fea703fcd0fff57de5000947b5ca81286b`. Upstream photometry and catalog
bytes are not redistributed.

The script named `independent_verify.py` is a second internal implementation
cross-check. It is not an external independent replication, peer review, or
expert endorsement.

## Scope

No row, label, covariance, or light curve is modified. No survey ranking,
residual analysis, corrected Hubble constant, causal explanation, new physics,
or Hubble-tension resolution is claimed.
