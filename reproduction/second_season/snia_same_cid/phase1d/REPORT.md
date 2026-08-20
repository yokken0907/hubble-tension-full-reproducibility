# Phase 1D report: same-CID measurement lineage and shared dependencies

## Executive conclusion

The frozen public release provides **partial**, not complete, measurement
lineage for the 69 H0DN rows in 30 repeated-CID groups. Under the predeclared
CID-plus-survey crosswalk, 38 rows each have exactly one compatible active
public photometry input candidate and 31 do not. Only 3 of 30 groups have a
distinct unique compatible candidate for every row. This does not establish
the direct executed-run ancestry of any final `m_b_corr` row. At the same
time, all 12 predeclared shared-pipeline anchors are present in the public
configuration, while none of three specifically referenced external assets
is tracked in the frozen release.

The formal completion status is
`AUDIT_COMPLETE_SHARED_DEPENDENCY_AND_LINEAGE_CLASSIFIED`, with release
classification `PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE`.

The audit does not alter the Phase 1A/1C covariance findings. It narrows what
can and cannot be reconstructed from public material before any scientifically
stronger survey-level attribution is attempted.

## Question and scope

Phase 1B established a one-to-one row map between the 277 H0DN distances and
the official Pantheon+SH0ES release, including 30 exact-CID groups containing
69 rows. Phase 1C found that the same-CID contrast-space low-dispersion flag
persisted under the official STATONLY covariance. Phase 1D therefore asks:

1. Can each of those 69 final rows be linked to exactly one active public
   survey-photometry input candidate under the frozen crosswalk?
2. When both rows have compatible candidates, do different rows point to
   distinct file blobs,
   and do their literal observation records overlap?
3. Which common fitting, aggregation, and duplicate-CID covariance
   dependencies are directly documented by the frozen public configuration?
4. Are the specifically referenced inputs needed for fuller reconstruction
   tracked in the public release?

It does not refit light curves, recompute bias corrections, rank surveys,
change any covariance, or estimate a corrected H0.

## Frozen design

The main contract, decision vocabulary, source locks, Phase 1B row map, and
pre-execution exposure record were prospectively frozen within the project
before the complete 69-row scan.
Partial result blindness is explicitly disclosed: selected illustrative
files and one absent referenced asset had been inspected before freeze.

The two upstream repositories are locked by URL and commit, and key inputs
are additionally locked by Git object identifier, byte count, and SHA-256.
The Pantheon+ photometry subtree is locked to tree object
`3facbb99276c7589349d8eceaac218ccd2ad0726`.

For each configured source directory, only files occurring exactly once in
the tracked `.LIST`, absent from `.IGNORE`, and present as Git blobs were
eligible. A file then had to pass strict `SNID`, `SURVEY`, and optional
`NOBS` parsing. Row selection used exact CID and the predeclared normalized
survey header; no fit value, residual, covariance element, or Phase 1C
outcome could choose a candidate.

## Main results

The scan covered 847 active files in seven unique public source directories,
with zero parser failures.

### Row and group lineage

- 38 of 69 rows had one active input candidate compatible with the frozen
  crosswalk.
- 31 of 69 rows had no compatible candidate under that crosswalk.
- 38 row–file evidence records were emitted.
- 3 groups (`2009cz`, `2005iq`, `2005hc`) had a distinct unique compatible
  candidate for every row.
- 27 groups lacked such complete candidate coverage.
- 10 of 48 possible within-group row pairs had compatible candidates for both
  rows.
- None of those 10 pairs shared a byte-identical `OBS:` line.

Per frozen IDSURVEY label, the unique/unresolved counts were:

| Code | Label | Unique | Unresolved |
| ---: | --- | ---: | ---: |
| 5 | CSP | 16 | 0 |
| 51 | LOSS1 | 0 | 7 |
| 56 | SOUSA | 3 | 0 |
| 57 | LOSS2 | 0 | 16 |
| 62 | CFA2 | 1 | 0 |
| 63 | CFA3S | 3 | 0 |
| 64 | CFA3K | 15 | 0 |
| 65 | CFA4p2 | 0 | 8 |

These are crosswalk outcomes, not survey-quality scores.

The legacy status `UNIQUE_ACTIVE_PUBLIC_PHOTOMETRY_FILE` is retained for code
compatibility and is explicitly aliased to
`UNIQUE_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE`. The legacy zero-candidate
status is similarly aliased to
`NO_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE`. Every row carries
`evidence_level = FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE` and
`direct_final_measurement_ancestry = NOT_ESTABLISHED`.

### Shared dependencies and release sufficiency

All 12 exact-text anchors in the frozen `PPLUS.yml` configuration passed.
They are configuration-level evidence for common source aggregation, a shared
SALT2 model alias, duplicate handling, and the `DUP_SIGINT` covariance
reference, including its use by the NOSYS option. They are not a job log, run
manifest, or input/output hash chain proving which configuration produced the
published 277 rows.

The machine-readable boundary markers are
`CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY` and
`NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF`.

Three assets were predeclared as necessary for fuller public reconstruction:

- `v6_9_duplicate_cid.cov`
- `SALT2muH0_data_foranthony.input`
- `LOWZ.nml`

No tracked path with any of these basenames occurs in the frozen DataRelease
tree. This is a public-release sufficiency limit. It is not evidence that the
original collaboration lacked the files or that its internal analysis was
incorrect.

### Survey-crosswalk evidence register

`provenance/SURVEY_CROSSWALK_EVIDENCE.tsv` records the evidence path, Git
object/version, excerpt hash, and evidence classification for all eight
IDSURVEY codes. Codes 5, 56, 62, 63, and 64 are `COMPOSITE_INFERENCE`; codes
51, 57, and 65 are `UNRESOLVED_BRIDGE`. No entry is promoted from the post-hoc
CID-only diagnostic, and the main 38/69 and 31/69 classifications are not
changed.

## Post-hoc CID-only localization

The main result's 31 unresolved rows required a clarification to prevent an
invalid “no public data” interpretation. A second contract was therefore
frozen **after** the main results and was explicitly made non-promoting. It
searched all 847 active parsed files by exact CID alone.

Every unresolved row had multiple same-CID files:

| IDSURVEY | Rows | Row–candidate records |
| ---: | ---: | ---: |
| 51 | 7 | 16 |
| 57 | 16 | 39 |
| 65 | 8 | 18 |
| **Total** | **31** | **73** |

The candidate ledger shows a systematic recurring pattern: each code-51 row
has an `LOSS` candidate, each code-57 row has a `KAIT_DS15` candidate, and
each code-65 row has a CFA4p1-header candidate. Other same-CID survey files
also occur, so CID alone cannot assign a final row. `SURVEY.DEF`, which might
have supplied an explicit numeric crosswalk, is not tracked in the frozen
release.

This is a concrete hypothesis for a separately and prospectively internally
frozen crosswalk audit, not a corrected mapping in Phase 1D. The five protected
main result files
were hash-checked before and after this diagnostic and remained byte
identical.

## Interpretation

Phase 1D establishes two useful boundaries.

First, the public release is rich enough to limit 38 rows to one compatible
public photometry input candidate and to identify important configuration-level
shared-processing anchors. It does not provide the executed run, FITRES,
quality-cut, bias-correction, and input/output hash chain required to prove
direct final-measurement ancestry.

Second, the unresolved portion is localized. It is not a general parser
failure and not an absence of same-CID photometry. It is concentrated in
three numeric survey codes and in the missing explicit bridge from final
IDSURVEY values to raw-series header vocabulary.

This does not explain the Phase 1C low-dispersion result. Shared processing
and duplicate covariance are dependencies, not demonstrated causes.
Likewise, distinct blobs and zero literal line overlap do not imply
independent calibration, disjoint exposures, or independent likelihood
terms.

## Verification

- 15/15 checks passed in a separate-implementation main cross-check.
- 9/9 checks passed in a separate-implementation post-hoc cross-check.
- All unit and locked-result regression tests in `results/unit_tests.log`
  passed.
- An isolated package copy regenerated 19/19 protected result files
  byte-for-byte.
- The final closure gate requires all scientific, scope, documentation,
  syntax, path-leak, and packaging checks to pass.

These second-implementation checks use the same project, public inputs, and
AI-assisted environment. They are not an independent external replication,
peer review, or expert endorsement.

## Recommended next branch

The strongest next step is a new crosswalk-resolution phase, prospectively
frozen within the project before result inspection. It should predeclare
candidate mappings for codes 51, 57, and 65 using evidence independent of the
Phase 1D outcome, such as an official SNANA survey registry, release
production metadata, or an author-supplied `SURVEY.DEF`; then test whether
the mapping uniquely resolves all rows. Only after that bridge is validated
should any survey-specific contrast or influence audit be attempted.
