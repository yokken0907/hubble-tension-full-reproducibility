# Frozen contract: H0DN SN Ia multi-row provenance audit

Contract identifier: `H0DN-SNIA-MULTIROW-PROVENANCE-PHASE1B-20260730-01`

Freeze timestamp: 2026-07-30T03:18:00Z

## Primary question

Can every row of the frozen 277-row H0 Distance Network (H0DN)
Pantheon+ Hubble-flow table, with particular attention to the already known
69 rows in 30 multi-row exact-name groups, be uniquely traced to a row of the
official frozen Pantheon+SH0ES release and its published `IDSURVEY` value?
Separately, is the frozen H0DN 277-by-277 magnitude covariance exactly the
official Pantheon+SH0ES STAT+SYS covariance submatrix in the traced H0DN row
order?

This is a bounded provenance and numerical-lineage audit. It does not decide
whether repeated rows are statistically independent, correct a covariance,
re-estimate the Hubble constant, or resolve the Hubble tension.

## Chronology and prior knowledge

Before this contract was frozen, Phase 1A had already established:

- 277 H0DN rows and 238 unique byte-for-byte name strings;
- 30 multi-row exact-name groups containing 69 rows;
- 39 duplicate-name contrast degrees of freedom;
- a low residual chi-square localized to the duplicate-name contrast
  subspace under the frozen H0DN model.

The official catalog schema, its published `IDSURVEY` code legend, and a few
illustrative rows had also been inspected while designing this audit. No
complete 277-row mapping, no 30-group survey-classification result, and no
covariance-submatrix comparison was computed or inspected before this
contract and its decision configuration were frozen.

## Frozen public sources

### H0DN

- Repository: `https://github.com/StefCas789/H0DN.git`
- Commit: `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- Table: `data/sn1a_hf_pp.dat`
- Magnitude covariance: `data/sn1a_covar_pp.dat`

### Pantheon+SH0ES release

- Repository: `https://github.com/PantheonPlusSH0ES/DataRelease.git`
- Commit: `c447f0fea703fcd0fff57de5000947b5ca81286b`
- Catalog:
  `Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat`
- STAT+SYS covariance:
  `Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES_STAT+SYS.cov`
- Survey-code and covariance documentation:
  `Pantheon+_Data/4_DISTANCES_AND_COVAR/README`

All required paths, Git blob identifiers, byte counts, and SHA-256 digests are
registered in `provenance/SOURCE_LOCK.tsv`. Upstream bytes are acquired
separately and are not redistributed in this package.

## Frozen row-selection rule

The official candidate pool is restricted to rows for which
`USED_IN_SH0ES_HF` parses numerically as exactly `1`.

The H0DN audit nevertheless maps all 277 rows, not only the 69 rows in
multi-row groups. Full-table mapping is an integrity gate; the multi-row
subset is the descriptive scientific focus.

## Frozen row-matching rule

For each H0DN row, an official row is a candidate only if all of the following
hold:

1. H0DN `name` equals official `CID` byte-for-byte after removing only the
   file-format line terminator and field-separating whitespace. No case fold,
   punctuation edit, alias list, fuzzy match, or manual substitution is
   allowed.
2. `abs(H0DN m_b - official m_b_corr) <= 0.000500000001`.
3. `abs(H0DN err_m_b - official m_b_corr_err_DIAG) <= 0.000005000001`.
4. `abs(H0DN zhel - official zHEL) <= 0.000005000001`.
5. `abs(H0DN zcmb - official zCMB) <= 0.000005000001`.

The tolerances are the printed half-units of the H0DN table's respective
decimal resolutions plus a fixed `1e-12` binary-arithmetic guard. They must
not be widened after outcomes are observed.

- Exactly one candidate: `UNIQUE_MATCH`.
- Zero candidates: `NO_MATCH`, forcing
  `HOLD_CATALOG_MAPPING_INCOMPLETE`.
- More than one candidate: `AMBIGUOUS_MATCH`, forcing
  `HOLD_CATALOG_MAPPING_AMBIGUOUS`.

An official catalog row may be assigned to at most one H0DN row. Reuse forces
`HOLD_CATALOG_MAPPING_AMBIGUOUS`.

## Frozen survey-code vocabulary

The audit copies the integer `IDSURVEY` value from the uniquely matched
official catalog row and resolves its label only through the code legend in
the frozen official README:

| Code | Label |
| ---: | --- |
| 1 | SDSS |
| 4 | SNLS |
| 5 | CSP |
| 10 | DES |
| 15 | PS1MD |
| 18 | CNIa0.02 |
| 50 | LOWZ/JRK07 |
| 51 | LOSS1 |
| 56 | SOUSA |
| 57 | LOSS2 |
| 61 | CFA1 |
| 62 | CFA2 |
| 63 | CFA3S |
| 64 | CFA3K |
| 65 | CFA4p2 |
| 66 | CFA4p3 |
| 100 | HST |
| 101 | SNAP |
| 106 | CANDELS |
| 150 | FOUND |

An unlisted code forces `HOLD_SURVEY_CODE_UNRESOLVED`; it is not silently
relabeled.

For each exact-name group with more than one H0DN row:

- `MULTI_SURVEY_ONLY`: every mapped `IDSURVEY` code occurs once.
- `SAME_SURVEY_REPEATED`: exactly one distinct `IDSURVEY` code occurs.
- `MIXED_SURVEY_MULTIPLICITY`: more than one distinct code occurs and at
  least one code occurs more than once.

These labels describe catalog-row multiplicity only. They do not establish
physical identity, statistical independence, duplication error, or causality.

## Frozen covariance-lineage rule

The official covariance parser must read its declared leading dimension and
then exactly that many squared finite floating-point values. It must produce
a symmetric 1701-by-1701 matrix. The H0DN covariance parser must likewise
produce a finite symmetric 277-by-277 matrix.

Using the unique official row index assigned to each H0DN row, the audit
extracts the official STAT+SYS covariance submatrix in H0DN order. Success
requires elementwise IEEE-754 `float64` equality:

`official_submatrix == H0DN_covariance`

No absolute or relative tolerance, rounding, rescaling, diagonal adjustment,
permutation search, or covariance repair is permitted. The report records the
equality count, mismatch count, first mismatch if any, and maximum absolute
difference.

Any mismatch forces `HOLD_COVARIANCE_LINEAGE_MISMATCH`.

## Independent verification requirements

The delivered verifier must independently reparse the locked inputs and
recompute:

- the 277 row candidate sets and one-to-one mapping;
- the 30 multi-row group memberships and their survey classes;
- the official covariance submatrix and exact-equality diagnostics;
- consistency between all machine-readable ledgers and the summary;
- contract hashes, source hashes, unit tests, package manifest, checksum
  sidecar, and delivery identity.

The verifier is read-only unless explicitly invoked with a result-recording
flag. A clean reproduction runs the complete audit in an isolated copy and
requires byte-identical `audit_summary.json`, `row_mapping.tsv`,
`multirow_group_summary.tsv`, and `covariance_lineage.json`.

## Status precedence

The first applicable HOLD in this order is the formal status:

1. `HOLD_SOURCE_MISMATCH`
2. `HOLD_INPUT_SCHEMA_MISMATCH`
3. `HOLD_CATALOG_MAPPING_INCOMPLETE`
4. `HOLD_CATALOG_MAPPING_AMBIGUOUS`
5. `HOLD_SURVEY_CODE_UNRESOLVED`
6. `HOLD_COVARIANCE_LINEAGE_MISMATCH`
7. `HOLD_VERIFICATION_FAILURE`

Only if every required gate passes is the status:

`AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED`

A HOLD preserves all diagnostics and stops scientific interpretation. Failed
checks must not be hidden, weakened, or rerun under changed rules without a
disclosed amendment.

## Frozen exclusions and non-claims

- No H0DN row is removed, averaged, merged, downweighted, or reweighted.
- No individual supernova is called anomalous.
- No residual, object, or survey is ranked by apparent discrepancy.
- No raw-photometry file, calibration chain, or light-curve reduction path is
  claimed unless separately demonstrated; this audit stops at the frozen
  official final catalog row and its documented survey code.
- No covariance element is modified.
- No corrected `a_B`, `M_B`, `H0`, or tension significance is computed.
- No physical or causal explanation for the Phase 1A result is asserted.
- This independent audit is not validation or peer review by the H0DN or
  Pantheon+SH0ES collaborations.

## Stop rule

Phase 1B stops after provenance mapping, survey-multiplicity description,
exact covariance-lineage comparison, and package verification. Any
row-construction or raw-photometry investigation is a separately contracted
Phase 1C.

## Amendment policy

Any post-freeze change to this contract, the decision configuration, or source
register requires a numbered row in
`provenance/CONTRACT_AMENDMENTS.tsv`. The row must state whether mapping or
covariance results had been observed and whether interpretation changes. An
undisclosed amendment forces `HOLD_VERIFICATION_FAILURE`.
