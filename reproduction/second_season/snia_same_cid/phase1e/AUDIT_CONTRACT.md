# Frozen contract: H0DN SN Ia survey-code crosswalk audit

Contract identifier:
`H0DN-SNIA-SURVEY-CODE-CROSSWALK-PHASE1E-20260802-01`

## Primary question

Can IDSURVEY codes `51`, `57`, and `65` be connected to public Pantheon+SH0ES
photometry directory/header vocabularies using rows that are independent of the
30 same-CID groups, and does that independently inferred crosswalk uniquely
resolve the 31 Phase 1D rows left unresolved by its frozen vocabulary?

This is a public-release metadata and provenance audit. It is not a light-curve
analysis, covariance analysis, survey comparison, or Hubble-constant analysis.

## Chronology and known post-hoc hypotheses

The audit is not blind. Before this contract was frozen, Phase 1D had already
shown that its original mapping left 31 rows unresolved and its post-hoc
CID-only diagnostic had exposed repeated candidate patterns for codes 51, 57,
and 65. Those patterns are recorded in
`provenance/PREEXECUTION_EXPOSURE.json`.

To prevent those target outcomes from defining their own crosswalk, no CID in
any of the 30 Phase 1B multi-row groups may enter the inference set. The
mapping is inferred only from target-excluded public rows and is then applied
once to the 31 fixed targets.

This is a project-internal prospective hash freeze before the complete Phase
1E scan. It is not described as a public preregistration.

## Frozen sources

- Pantheon+SH0ES DataRelease commit
  `c447f0fea703fcd0fff57de5000947b5ca81286b`.
- Corrected Phase 1B 277-row map, copied byte-for-byte and hash locked.
- Phase 1D row-lineage ledger and summary, copied byte-for-byte and hash
  locked.
- Phase 1D archive SHA-256
  `3c201733aee688ee3535928029317f6b9e0bc012a4cca79cfb8c9145e54c7342`.

Upstream data bytes are not redistributed beyond the compact derived ledgers
already contained in Phase 1D.

## Frozen target population

Select from the Phase 1D main row ledger only rows with:

- `IDSURVEY` in `{51, 57, 65}`; and
- `lineage_status = NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE`.

The population must be exactly 31 rows: 7, 16, and 8 for codes 51, 57, and 65.
Any mismatch is `HOLD_UPSTREAM_TARGET_MISMATCH`.

## Target-excluded anchor construction

The full 1701-row official catalog is used only through `CID`, `IDSURVEY`, and
`USED_IN_SH0ES_HF`.

An eligible row must:

1. have one of the three target IDSURVEY codes;
2. have a CID occurring exactly once in the full catalog; and
3. have a CID absent from every Phase 1B multi-row group.

All active files in the seven Phase 1D public source directories are scanned
without assigning any directory to an IDSURVEY in advance. Active-file and
header parsing rules are inherited verbatim in substance from Phase 1D:
tracked `.LIST` membership exactly once, no `.IGNORE` membership, one `SNID`,
one `SURVEY`, and a consistent optional `NOBS` count.

An eligible catalog row becomes an anchor only when exact CID matching finds
exactly one parseable active file across all seven directories. No magnitude,
fit parameter, residual, covariance value, redshift, coordinate, filename
heuristic, case folding, punctuation rewrite, or manual alias is permitted.

## Frozen inference rule

For each IDSURVEY code, support requires all of the following:

- at least 5 target-excluded anchors;
- at least 3 anchors with `USED_IN_SH0ES_HF = 1`;
- exactly one distinct source directory across all anchors; and
- an accepted raw `SURVEY` vocabulary equal to the exact set observed among
  those anchors.

Failure by low support is
`HOLD_INSUFFICIENT_TARGET_EXCLUDED_EVIDENCE`. More than one supported source
directory is `HOLD_CONFLICTING_TARGET_EXCLUDED_EVIDENCE`.

Meeting the rule establishes only
`TARGET_EXCLUDED_PUBLIC_INTERNAL_CROSSWALK_SUPPORTED`. It is not called an
official `SURVEY.DEF` mapping, because the frozen DataRelease does not track
that registry.

## Frozen target application

For each of the 31 targets, a candidate must have:

- exact target CID;
- the inferred source directory for its IDSURVEY; and
- a raw `SURVEY` header in the inferred exact header set.

Exactly one candidate gives
`UNIQUE_ACTIVE_FILE_UNDER_INFERRED_CROSSWALK`; any other count remains
`TARGET_NOT_UNIQUELY_RESOLVED_UNDER_INFERRED_CROSSWALK`.

The Phase 1D main ledgers, counts, status, and release classification remain
unchanged. A Phase 1E success is a new supplementary result, not a retroactive
rewrite of Phase 1D.

## Official-label versus raw-header diagnostic

The distance README's labels are recorded independently of the inferred raw
directory/header mapping. For code 65 only, the exact `CFA4pN` token in the
published label is compared with any such token in the inferred raw header.
A mismatch is descriptive metadata tension. It does not, by itself, identify
which label is historically or physically correct and does not modify either
source.

## Independent verification

A separate implementation must independently reparse the catalog, compact
Phase 1B/1D ledgers, lists, ignores, and photometry headers; reconstruct the
anchor set; infer all crosswalks; apply them to all targets; and compare every
machine-readable scientific ledger. Protected outputs must reproduce byte for
byte in an isolated package copy.

## Frozen exclusions and non-claims

- No row is removed, merged, averaged, reweighted, or relabelled in an
  upstream file.
- No light curve is re-fit and no bias correction is recomputed.
- No covariance entry is changed or assessed.
- No residual, survey, or object is ranked.
- No survey-specific offset, anomaly, or influence statistic is computed.
- No corrected `a_B`, `M_B`, `H0`, or tension significance is computed.
- Directory/header association is not statistical independence.
- A public metadata mismatch is not called an error in the scientific
  measurement.
- No causal explanation of the Phase 1A/1C low-dispersion result is made.
- No new physics or Hubble-tension resolution is claimed.

## Stop rule

The phase stops after crosswalk classification, 31-row application, label/header
diagnostic, independent verification, clean reproduction, and deterministic
packaging. It does not proceed to survey-stratified residual analysis.
