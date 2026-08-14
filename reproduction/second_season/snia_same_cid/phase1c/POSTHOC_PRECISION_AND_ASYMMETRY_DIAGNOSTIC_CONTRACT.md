# Post-hoc precision and mapped-asymmetry diagnostic contract

Contract identifier:
`H0DN-SNIA-PHASE1C-POSTHOC-PRECISION-ASYMMETRY-20260730-01`

Status:
`FROZEN_BEFORE_POSTHOC_PRECISION_AND_ASYMMETRY_EXECUTION`

Freeze timestamp: `2026-07-30T06:34:00Z`

## Scope and chronology

This is an internal, result-blind analysis freeze created in response to bounded
review. It is not an external preregistration. The Phase 1C main results,
formal status, and ordered classification had already been observed when this
contract was written, so the amendment ledger records
`new_results_observed=YES`. The new high-precision-magnitude and selected
submatrix-asymmetry values had not been loaded, calculated, or viewed before
this file was frozen and hashed.

The active Contract 02 analysis remains the sole main analysis. This
supplement cannot replace or revise its three ordered results, its formal
status, or `LOW_FLAG_PERSISTS_THROUGH_STATONLY`.

## Locked inputs

- H0DN commit:
  `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`.
- Pantheon+SH0ES DataRelease commit:
  `c447f0fea703fcd0fff57de5000947b5ca81286b`.
- H0DN printed table:
  `data/sn1a_hf_pp.dat`, SHA-256
  `6b3dd6591cfaade2a6bf4bdb632fafc504f1449b9c07db4176a14e8e2366258f`.
- Official high-precision table:
  `Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat`, field
  `m_b_corr`, SHA-256
  `1cb0fc379ef066afdc2ffd1857681cc478024570d8a3eba284fb645775198cf8`.
- Official STAT+SYS covariance, SHA-256
  `abf806d966485e64afdb359c87bffc0ecc00d05eff0a31ced66f247385df0fdc`.
- Official STATONLY covariance, SHA-256
  `9f177129a332735d3637affd20054080d5260815f3ca0809120c05b2c902297f`.
- Phase 1B compact 277-row mapping:
  `provenance/PHASE1B_ROW_MAP.tsv`, SHA-256
  `a3cd37e836d39f623dfedcea6c3c8a0ac0c0f80ae5647bd163610fdbd1bd9d69`.
- Phase 1A canonical archive:
  `h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip`, SHA-256
  `38bb6e55c66ec3442e465cfe4367c1b75e5ecb369933df6de71b75c6182e8333`.

No row is rematched. The Phase 1B mapping order is used exactly. No upstream
bytes are redistributed.

## Fixed contrast construction

Both magnitude vectors use the same 277 mapped rows, the same exact-name
groups, and the same deterministic Helmert contrast matrix \(A\) from Contract
02. The required structure remains 30 multirow exact-name groups, 69 rows in
those groups, and 39 contrast degrees of freedom. The implementation must build
\(A\) once and use that same in-memory matrix for both vectors. It records a
SHA-256 digest of the little-endian float64 matrix bytes.

The printed vector uses H0DN `m_b`. The alternate vector replaces only those
277 magnitude values by mapped official `m_b_corr`. All cosmographic terms,
`q0=-0.55`, `j0=1`, `vp_2mpp`, the 240 km/s rowwise velocity variance, and all
covariance constructions remain unchanged.

For each vector, calculate

\[
q=(A\alpha)^\mathsf{T}(ACA^\mathsf{T})^{-1}(A\alpha),
\qquad
p=P(\chi^2_{39}\le q),
\qquad
q/39.
\]

The three covariance baselines are fixed in this order:

1. `PHASE1A_FULL`;
2. `STAT_SYS_NO_ROWWISE_VELOCITY`;
3. `STAT_ONLY`.

For each baseline report printed and high-precision \(q\), \(p\), and \(q/39\),
with `delta_chi2 = high_precision - printed` and
`delta_lower_tail_probability = high_precision - printed`. Also report the
maximum absolute and Euclidean-norm differences between the two 39-component
contrast vectors. No threshold, pass/fail criterion, or preferred vector is
attached to those differences.

Required outputs:

- `results/printed_vs_high_precision_contrast_diagnostic.json`;
- `results/printed_vs_high_precision_contrast_diagnostic.tsv`.

## Fixed selected-submatrix asymmetry diagnostic

Before symmetrization, select the raw 277-by-277 STAT+SYS and STATONLY
submatrices by the frozen Phase 1B mapping. For each raw selected submatrix,
inspect only off-diagonal unordered pairs \(i<j\) and report:

- exact asymmetric unordered-pair count;
- exact asymmetric directed-element count;
- count above absolute tolerance `0.0`;
- maximum \(|C_{ij}-C_{ji}|\);
- the lexicographically first maximum pair, including selected indices,
  H0DN rows, official rows, `CID`, and `IDSURVEY` for both endpoints.

The frozen comparison and action tolerance is exactly `0.0`: any finite,
nonzero off-diagonal transpose difference triggers the three representation
calculations below. This exact rule is appropriate because the source commits
and source bytes are fixed. All values must also be finite.

If a selected submatrix has zero exact asymmetry, state that any asymmetry in
the full 1701-by-1701 source matrix lies outside the selected mapped
submatrix. If it has nonzero exact asymmetry, form:

1. `SYMMETRIC_AVERAGE`: \((C+C^\mathsf{T})/2\);
2. `UPPER_TRIANGLE_MIRRORED`: preserve the diagonal and upper triangle;
3. `LOWER_TRIANGLE_MIRRORED`: preserve the diagonal and lower triangle.

For every triggered source covariance, calculate \(q\), \(p\), and \(q/39\)
under all three Phase 1C baselines to which that source contributes:
STAT+SYS supplies the measurement covariance for `PHASE1A_FULL` and
`STAT_SYS_NO_ROWWISE_VELOCITY`; STATONLY supplies `STAT_ONLY`. The Phase 1A
rowwise velocity diagonal is unchanged. Non-applicable baseline/source cells
are omitted. Each projected covariance must be finite and Cholesky-positive
definite before its quadratic form is reported.

Required outputs:

- `results/mapped_submatrix_asymmetry_diagnostic.json`;
- `results/mapped_submatrix_asymmetry_sensitivity.tsv`.

## Tolerances, invariants, and probability questions

- Main-result reproduction tolerance: absolute \(q\) difference `2e-8`.
- Contrast orthogonality and annihilation tolerance: `2e-14`.
- Projected covariance minimum eigenvalue: strictly greater than `1e-14`.
- Cholesky/eigendecomposition \(q\) agreement: absolute difference `2e-9`.
- Probability implementation agreement: absolute difference `2e-14`.
- JSON must reject NaN and Infinity; TSV is UTF-8 and finite.
- The mapping row sequence, group membership, Helmert basis, formal status,
  ordered classification, and main result files must be unchanged by the
  post-hoc runner.

Two probabilities concerning the known Phase 1A value answer different
reference questions and must remain in separate named fields:

- Phase 1A conditional Beta probability: `9.3683622e-05`;
- Phase 1C marginal \(\chi^2_{39}\) lower-tail probability:
  `3.6795246e-06`.

The strong-low descriptive label uses `p < 0.001`. The ordered sensitivity
flag uses `p < 0.01`. All three main baselines meet both thresholds, but the
thresholds are not interchangeable.

## Nonclaims and promotion rule

These diagnostics are post-hoc sensitivity checks only. They do not:

- alter the Contract 02 result vector;
- promote `m_b_corr` to the main Phase 1C input;
- identify a covariance error or justify a covariance rescale;
- show that statistical uncertainties are overestimated;
- identify an instrumental, astrophysical, catalog, or software cause;
- produce corrected intercepts, \(M_B\), \(H_0\), or a Hubble-tension result;
- authorize an object or survey ranking;
- initiate Phase 1D.

The only allowed conclusion is a transparent numerical description of how
these two bounded representation choices affect the fixed 39-dimensional
contrast diagnostic.
