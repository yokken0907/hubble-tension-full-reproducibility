# Frozen contract: H0DN SN Ia cross-series input-dependency audit

Contract identifier:
`H0DN-SNIA-CROSS-SERIES-INPUT-DEPENDENCY-PHASE1F-20260809-01`

## Primary question

For the 30 same-CID groups and 69 final-distance rows fixed upstream, what can
the frozen public release establish about shared or distinct:

1. published photometry records;
2. observed filter tokens and public calibration definitions;
3. light-curve-fit configuration inputs; and
4. downstream aggregation configuration?

This is a bounded public-input and configuration-provenance audit. It is not a
light-curve re-fit, a covariance correction, a survey comparison, or an H0
analysis.

## Chronology and result blindness

This audit is not fully blind. Phase 1D and corrected Phase 1E had already
classified 38 and 31 public-input candidates, respectively. Before this
contract was frozen, limited examples from SN 2009cz, SN 2007qe, and SN 2009D
were inspected, and the SN 2007qe examples exposed similar published
photometric payload values across two files. The public `PPLUS.yml` task blocks
and five KCOR input examples were also inspected. These exposures are recorded
in `provenance/PREEXECUTION_EXPOSURE.json`.

The complete 69-file parse, all 48 within-CID pair comparisons, full filter
mapping, and aggregate counts were not run before the internal hash freeze.
This is a project-internal prospective freeze for the remaining complete scan,
not a public preregistration.

## Frozen upstream sources

- Corrected Phase 1D archive SHA-256:
  `6792886b8f1a8ac6397e6305931bfc750fdf1f1211c5e92b1f07ea1e7f0609bd`.
- Corrected Phase 1E archive SHA-256:
  `0c86bd916e5b54f3e97b810b868c793e2fdd564abd94d4f1687fb4f632f73ed3`.
- Pantheon+SH0ES DataRelease commit:
  `c447f0fea703fcd0fff57de5000947b5ca81286b`.
- The compact Phase 1B, corrected Phase 1D, and corrected Phase 1E ledgers
  copied into `provenance/` and byte-hash locked.

Raw upstream photometry, calibration files, catalog bytes, and `PPLUS.yml` are
read from the fixed Git commit and are not redistributed in the package.

## Frozen population and candidate construction

The Phase 1D corrected ledger must contain exactly 69 rows in 30 repeated-CID
groups. Its 38 legacy-unique rows contribute their single
`active_candidate_paths` path. Exactly the 31 Phase 1D legacy-unresolved rows
must match corrected Phase 1E, and each must contribute its single
`candidate_paths` path. Every combined record is labelled
`FROZEN_PUBLIC_INPUT_CANDIDATE_NOT_FINAL_MEASUREMENT_ANCESTRY`.

Any row-set, CID, IDSURVEY, path-count, or upstream-hash mismatch is an
operational HOLD. The 69 candidates are not treated as proven ancestors of the
final `m_b_corr` rows or of an executed FITRES/bias-correction run.

## Frozen photometry parse

Each candidate must be a tracked blob in the fixed commit, active under its
directory `.LIST`/`.IGNORE` rules, and must have one `SNID`, one `SURVEY`, one
`VARLIST`, and a consistent `NOBS`. `VARLIST` must expose `MJD`, `FLT`,
`FLUXCAL`, `FLUXCALERR`, `MAG`, and `MAGERR`. Numeric tokens are parsed as
finite base-10 decimals while preserving the displayed precision.

No residual, fitted parameter, covariance entry, redshift, or H0 value enters
candidate selection or pair matching.

## Frozen within-CID pair universe

All unordered row pairs within each of the 30 same-CID groups are evaluated.
The expected count is 48. No pair may be selected or removed after inspecting
its observations.

### Exact-row evidence

`BYTE_EXACT_OBSERVATION_ROW` requires identical raw bytes after the literal
`OBS:` prefix, including every published field. This is the strongest direct
public-file equality test, but even equality does not prove the physical
exposure history or final-run ancestry.

### Rounding-compatible payload evidence

For a printed decimal token, its rounding interval is the closed interval
centred on the parsed value with half-width one half of its least displayed
decimal place, including scientific notation. Two observations are a
`ROUNDING_COMPATIBLE_PHOTOMETRIC_PAYLOAD_EDGE` only if the intervals overlap
for all four quantities `FLUXCAL`, `FLUXCALERR`, `MAG`, and `MAGERR`.

MJD and filter token do not define this edge because public series may round
epochs differently and recode filters. Candidate edges are accepted as
`MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD_MATCH` only when each observation
has degree one in the pairwise edge graph. Ambiguous edges are reported but
not promoted.

Pair classes are fixed as:

- at least two mutual-unique matches:
  `REPEATED_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD`;
- exactly one: `SINGLE_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD`;
- none: `NO_MUTUAL_UNIQUE_ROUNDING_COMPATIBLE_PAYLOAD`.

These classes describe reuse or agreement of published numerical payloads.
They do not establish shared physical exposure, common raw image, causal
covariance, or statistical dependence.

### Non-promoting near-match screen

An edge enters a secondary screen when both flux quantities have relative
difference at most `1e-4`, `|delta MAG| <= 5e-4`, and
`|delta MAGERR| <= 5e-4`. Relative difference uses
`abs(a-b)/max(abs(a),abs(b),1)`. Its mutual-unique count is reported separately
and never changes the primary pair class.

For accepted primary matches, MJD interval overlap, exact filter-token equality,
and `|delta MJD| <= 0.11 day` are descriptors only. The 0.11-day screen was
chosen after the limited SN 2007qe example was seen and therefore cannot be
used as prospective proof of exposure identity.

## Frozen filter and calibration mapping

Each of the seven source directories is assigned, before the complete scan, to
the active `datawithsys` task and KCOR input explicitly named in
`provenance/DECISION_CONFIG.json`. Every actually used raw `FLT` token is
matched case-sensitively to the token declared by a `FILTER:` line in that KCOR
input. A mapping is complete only when exactly one definition is found.

The referenced transmission basename is checked at the public-release filter
path implied by the KCOR `FILTPATH` basename. The KCOR input `OUTFILE` basename
is checked against a tracked public FITS blob. These are public metadata and
asset-availability checks; no FITS grid is regenerated and no claim is made
that the tracked FITS was produced by the tracked text input.

## Frozen configuration-lineage audit

For every source series, exact active `PPLUS.yml` blocks must document:

- a DATAPREP raw-directory task;
- the assigned `datawithsys` LCFIT task;
- its BASE NML reference;
- its KCOR alias;
- the common `salt2excal`, `fitinplambda`, `header_override_nom`, and
  `ALL.fitopts` references; and
- membership of the corresponding output token in the active
  `REALDATABS20NOM` DATA list.

Evidence from `PPLUS.yml` is `CONFIGURATION_LEVEL`. It is not a run manifest,
job log, FITRES hash chain, or proof that a specific public candidate generated
a specific final row. Exact externally referenced paths are checked for tracked
availability. A differently located public file is only a candidate analogue,
not execution identity.

## Formal completion and stop rules

Operational parsing or source-integrity failure produces HOLD. Otherwise the
audit completes with counts and bounded classifications, including partial or
ambiguous public evidence. Completion does not require a preferred scientific
outcome.

After row profiles, all 48 pair classifications, filter/calibration mapping,
configuration lineage, second implementation, clean reproduction, and
deterministic packaging, the phase stops.

## Frozen exclusions and non-claims

- No public input candidate is promoted to proven final-measurement ancestry.
- No physical exposure identity or statistical independence is inferred from
  file, epoch, filter, or payload comparisons.
- No light curve is re-fit; no SALT2 parameter or bias correction is computed.
- No row is deleted, merged, averaged, reweighted, relabelled, or corrected.
- No survey, object, residual, or influence is ranked.
- No covariance element is changed or recommended for change.
- No corrected `a_B`, `M_B`, H0, or tension significance is computed.
- No causal explanation of the Phase 1A/1C low-dispersion flag is made.
- No new physics or Hubble-tension resolution is claimed.

