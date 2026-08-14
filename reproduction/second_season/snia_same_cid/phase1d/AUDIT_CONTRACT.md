# Frozen contract: H0DN SN Ia same-CID measurement-lineage audit

Contract identifier: `H0DN-SNIA-SAME-CID-MEASUREMENT-LINEAGE-PHASE1D-20260730-01`

Freeze timestamp: 2026-07-30T07:26:17Z

## Primary question

For the 69 H0 Distance Network (H0DN) rows in the 30 exact-name
multi-row groups already traced in Phase 1B, how far can the public
Pantheon+SH0ES release trace each final distance row back toward a specific
survey photometry file and its shared downstream processing dependencies?

The audit separates three questions:

1. Is there exactly one active public photometry file compatible with each
   frozen `(CID, IDSURVEY)` row?
2. Within each same-CID group, do the resolved rows point to distinct public
   file blobs, a reused blob, or an unresolved set?
3. Which common light-curve-fitting, bias-correction, and duplicate-covariance
   dependencies are documented by the frozen public pipeline configuration,
   and are the specifically referenced assets present in the release?

This is a bounded provenance and release-sufficiency audit. It does not
re-fit light curves, modify a covariance, rank surveys, estimate a corrected
Hubble constant, or explain the Hubble tension.

## Chronology and pre-freeze exposure

Phase 1B results were known before this contract:

- 277 H0DN rows map one-to-one to official Pantheon+SH0ES rows;
- 30 exact-name groups contain 69 rows;
- all 30 groups are `MULTI_SURVEY_ONLY`;
- the H0DN covariance equals the mapped official STAT+SYS submatrix.

Phase 1C results were also known:

- the same-CID contrast-space low-dispersion flag persists under the official
  STATONLY covariance;
- the result is therefore not localized solely to the published systematic
  covariance or the tested row-wise peculiar-velocity term.

While designing Phase 1D, the public table schema, public pipeline
configuration, global photometry-header vocabulary, and illustrative raw
files were inspected. One in-scope example (`2005M`, CSP and CfA3K) and the
absence of the specifically referenced `v6_9_duplicate_cid.cov` asset in the
release tree were therefore known before freeze. No complete 69-row
photometry mapping, no 30-group aggregate classification, and no independent
recalculation had been run. The exact exposure is recorded in
`provenance/PREEXECUTION_EXPOSURE.json`.

Accordingly, this package claims partial, not complete, result blindness.
All row- and group-level rules below were frozen before the complete scan.

## Frozen sources

### H0DN

- Repository: `https://github.com/StefCas789/H0DN.git`
- Commit: `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`

### Pantheon+SH0ES DataRelease

- Repository: `https://github.com/PantheonPlusSH0ES/DataRelease.git`
- Commit: `c447f0fea703fcd0fff57de5000947b5ca81286b`
- Photometry tree:
  `Pantheon+_Data/1_DATA/photometry`
- Final catalog and documentation:
  `Pantheon+_Data/4_DISTANCES_AND_COVAR/`
- Public pipeline configuration:
  `Pantheon+_Data/7_PIPPIN/PPLUS.yml`

### Upstream audit map

`provenance/PHASE1B_ROW_MAP.tsv` is a byte-for-byte copy of the compact
277-row map carried by the corrected Phase 1C package. Its SHA-256 is frozen
in `provenance/DECISION_CONFIG.json`. The canonical corrected Phase 1B and
Phase 1C archive names and SHA-256 digests are recorded in
`provenance/UPSTREAM_AUDIT_DEPENDENCIES.json`.

The repository commits, photometry-tree object, key file blobs, byte counts,
and SHA-256 digests are frozen in `provenance/REPOSITORY_LOCK.json` and
`provenance/SOURCE_LOCK.tsv`. Upstream bytes are not redistributed.

## Frozen audit population

The audit selects exact `CID` values occurring more than once in the frozen
277-row Phase 1B map. The population must contain exactly:

- 30 same-CID groups;
- 69 rows;
- group-size distribution: 21 groups of size 2 and 9 groups of size 3;
- survey codes limited to `{5, 51, 56, 57, 62, 63, 64, 65}`.

Any mismatch forces `HOLD_UPSTREAM_MAP_MISMATCH`.

## Frozen survey-to-source vocabulary

The allowed public source directories and normalized `SURVEY:` header values
are fixed in `provenance/DECISION_CONFIG.json`:

| `IDSURVEY` | Published label | Allowed directory | Accepted normalized `SURVEY:` |
| ---: | --- | --- | --- |
| 5 | CSP | `CSPDR3_anthony` or `CSP_data2` | `CSP` |
| 51 | LOSS1 | `KAIT_DS15` | `KAITM` or `KAITW` |
| 56 | SOUSA | `SWIFT` | `SWIFT` |
| 57 | LOSS2 | `LOSS` | `KAIT` |
| 62 | CFA2 | `PS1_LOWZ_COMBINED_TEXT_DS17` | `PS1_LOWZ_COMBINED(CFA2)` |
| 63 | CFA3S | `CfA3_DJ20` | `PS1_LOWZ_COMBINED(CFA3S)` |
| 64 | CFA3K | `CfA3_DJ20` | `PS1_LOWZ_COMBINED(CFA3K)` |
| 65 | CFA4p2 | `PS1_LOWZ_COMBINED_TEXT_DS17` | `PS1_LOWZ_COMBINED(CFA4p2)` |

The aliases are based on the frozen release paper's survey definitions, the
DataRelease directory documentation, and the active PIPPIN `DATAPREP`
configuration. They are not expanded after outcomes are observed.

## Frozen photometry parser and matching rule

For each configured source directory:

1. The audit reads the directory's tracked `.LIST`, `.IGNORE`, and `.README`
   blobs from the frozen Git commit.
2. A candidate file must be named exactly once in `.LIST`, must not be named
   in `.IGNORE`, and must exist as a tracked regular Git blob.
3. The file must contain exactly one parseable `SNID:` header and exactly one
   parseable `SURVEY:` header before its first `OBS:` record.
4. `SNID` must equal the Phase 1B `CID` byte-for-byte after removing only
   leading/trailing ASCII whitespace. No case folding, punctuation rewrite,
   alias list, coordinate match, or manual substitution is allowed.
5. Internal runs of ASCII whitespace in `SURVEY:` are collapsed to one space,
   then leading/trailing whitespace is removed. The result must exactly equal
   an accepted value in the frozen survey-to-source vocabulary.
6. `NOBS`, if present, must parse as a non-negative integer and equal the
   number of lines beginning exactly with `OBS:`. A mismatch makes that file
   unparseable.

For each row:

- one active candidate: `UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE`;
- zero active candidates: `NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE`;
- more than one active candidate:
  `AMBIGUOUS_ACTIVE_PUBLIC_PHOTOMETRY_FILES`;
- any required parse failure: `PHOTOMETRY_PARSE_FAILURE`.

No fit parameter, residual, magnitude difference, covariance element, or
Phase 1C contrast result is used to choose a photometry file.

## Frozen file-distinctness and observation-line diagnostics

For rows with a unique candidate, the audit records:

- Git blob identifier, byte count, and SHA-256;
- source directory, tracked path, normalized `SURVEY`, `SNID`, `NOBS`, and
  counted `OBS:` lines;
- a SHA-256 of the ordered `OBS:` lines after removing only line terminators.

For each same-CID group:

- if every row is unique and every full-file blob SHA-256 is distinct:
  `ALL_ROWS_UNIQUE_DISTINCT_PUBLIC_PHOTOMETRY_FILES`;
- if every row is unique but at least one full-file blob SHA-256 repeats:
  `PUBLIC_PHOTOMETRY_FILE_REUSE_PRESENT`;
- otherwise: `PUBLIC_PHOTOMETRY_LINEAGE_UNRESOLVED`.

The audit also counts byte-identical `OBS:` lines shared between each resolved
file pair. This is descriptive only. Distinct blobs or zero byte-identical
lines do not establish statistical independence, disjoint exposures,
independent calibration, or independent likelihood terms.

## Frozen shared-pipeline evidence rule

The audit searches only the frozen `PPLUS.yml` bytes for the exact anchors in
`DECISION_CONFIG.json`. A line whose first non-whitespace character is `#` is
excluded; every other line is stripped of leading/trailing whitespace and
compared for exact equality with the frozen anchor. Required anchors cover:

- the configured `DATAPREP` source directories;
- the joint `REALDATABS20NOM.DATA` aggregation;
- the shared SALT2 fit-model alias;
- `iflag_duplicate: 0`;
- the `DUP_SIGINT` extra-covariance reference;
- the `NOSYS` covariance option's use of `DUP_SIGINT`.

Each exact anchor must occur the predeclared number of times. Missing or
multiply occurring anchors force `HOLD_PIPELINE_CONFIG_MISMATCH`.

For each explicitly referenced external asset, the audit records whether a
tracked path with the frozen basename exists anywhere in the DataRelease
commit. Absence is a scientific release-sufficiency result, not an
operational failure and not evidence that the original collaboration lacked
the asset.

## Frozen release-sufficiency classification

Provided all operational gates pass:

- `PUBLIC_RELEASE_FULL_MEASUREMENT_LINEAGE` requires all 69 rows to have
  unique active photometry files, all pipeline anchors to verify, and every
  predeclared externally referenced required asset to be tracked in the
  release.
- `PUBLIC_RELEASE_IDENTIFIER_ONLY_LINEAGE` applies only if none of the 69 rows
  has a unique active photometry file and none of the shared-pipeline anchors
  verifies.
- all other completed combinations are
  `PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE`.

The formal completion status is
`AUDIT_COMPLETE_SHARED_DEPENDENCY_AND_LINEAGE_CLASSIFIED`.

## Independent verification

The delivered independent verifier must use a separate implementation path to
reparse:

- the Phase 1B map and 30/69 population;
- active list membership and photometry headers;
- row candidate counts and statuses;
- group file hashes, distinctness classes, and exact observation-line
  intersections;
- PIPPIN anchors and referenced-asset presence;
- the release-sufficiency classification.

It must compare all machine-readable ledgers to its recomputation. A clean
reproduction runs the audit in an isolated package copy and requires every
protected result file to be byte-identical.

## Status precedence

The first applicable operational status is formal:

1. `HOLD_CONTRACT_MISMATCH`
2. `HOLD_SOURCE_MISMATCH`
3. `HOLD_UPSTREAM_MAP_MISMATCH`
4. `HOLD_INPUT_SCHEMA_MISMATCH`
5. `HOLD_PIPELINE_CONFIG_MISMATCH`
6. `HOLD_VERIFICATION_FAILURE`

Only if none applies is the formal status
`AUDIT_COMPLETE_SHARED_DEPENDENCY_AND_LINEAGE_CLASSIFIED`.

An unresolved row is a permitted scientific result and therefore does not
itself force a HOLD.

## Frozen exclusions and non-claims

- No H0DN or Pantheon+ row is removed, merged, averaged, or reweighted.
- No covariance entry is changed, rescaled, symmetrized, or repaired.
- No survey, object, or residual is ranked.
- No survey-specific offset or anomaly test is performed.
- No light curve is re-fit and no bias correction is recomputed.
- No corrected `a_B`, `M_B`, `H0`, or tension significance is computed.
- Distinct public files are not called statistically independent.
- A shared pipeline or covariance dependency is not called the cause of the
  Phase 1A/1C low-dispersion result.
- A missing public asset is not called an error in the original analysis.
- The audit does not claim new physics or resolution of the Hubble tension.
- This independent audit is not collaboration validation or peer review.

## Stop rule

Phase 1D stops after row-level public-photometry lineage, group-level
file-distinctness diagnostics, shared-pipeline evidence, referenced-asset
availability, release-sufficiency classification, independent verification,
and deterministic package closure.

Survey ranking, leave-one-survey-out inference, covariance modification, and
corrected-H0 calculations require a separately frozen later-phase contract.

## Amendment policy

Any post-freeze change to this contract, the decision configuration, source
register, repository lock, exposure record, or upstream map requires a
numbered append-only entry in `provenance/CONTRACT_AMENDMENTS.tsv`. It must
state whether Phase 1D row/group results had been observed and whether
interpretation changes. An undisclosed amendment forces
`HOLD_CONTRACT_MISMATCH`.
