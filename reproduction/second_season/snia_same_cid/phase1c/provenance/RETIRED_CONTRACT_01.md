# Frozen contract: H0DN SN Ia contrast-covariance calibration audit

Contract identifier: `H0DN-SNIA-CONTRAST-COVARIANCE-PHASE1C-20260730-01`

Freeze date: 2026-07-30 (UTC)

## Question

For the 39 exact-name, cross-survey contrast modes isolated in Phase 1A and
mapped to the public Pantheon+SH0ES release in Phase 1B, how sensitive is the
observed low dispersion to three predeclared covariance baselines:

1. the frozen H0DN magnitude covariance plus H0DN's rowwise 240 km/s velocity
   term;
2. the published STAT+SYS magnitude covariance without that rowwise velocity
   term; and
3. the published STATONLY magnitude covariance?

This is a bounded covariance-calibration diagnostic. It is not a covariance
correction, a fit of a preferred covariance model, an object-level anomaly
search, or a recalculation of the Hubble tension.

## Chronology and prior knowledge

The following results were known before this contract was written:

- Phase 1A found 30 multi-row exact-name groups containing 69 rows and 39
  contrast degrees of freedom.
- Under the frozen H0DN one-intercept covariance, Phase 1A obtained
  `chi2 = 11.209315063602752` for those 39 modes and a conditional
  localization probability of `9.368362232281232e-05`.
- Phase 1B mapped all 277 H0DN rows one-to-one to public Pantheon+SH0ES rows.
  Of these, 275 were catalog-only unique and two required the predeclared
  covariance-diagonal ambiguity rule.
- Phase 1B found that every multi-row exact-name group is cross-survey and
  that all 76,729 elements of the mapped official STAT+SYS submatrix equal
  the H0DN magnitude covariance as parsed float64 values.

Therefore, the Phase 1A low value and the Phase 1B mapping are not new
discoveries in Phase 1C. The new quantities are the STAT+SYS-without-rowwise-
velocity and STATONLY contrast results, the component diagnostics, and their
predeclared sensitivity classification. No STATONLY or component result was
evaluated before this contract was frozen.

## Frozen sources

Two separately distributed public repositories are required:

- H0DN: `https://github.com/StefCas789/H0DN.git`, commit
  `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- Pantheon+SH0ES DataRelease:
  `https://github.com/PantheonPlusSH0ES/DataRelease.git`, commit
  `c447f0fea703fcd0fff57de5000947b5ca81286b`

The file-level lock is `provenance/SOURCE_LOCK.tsv`. Upstream bytes are not
redistributed.

The compact 277-row mapping in `provenance/PHASE1B_ROW_MAP.tsv` is a frozen
dependency derived from the corrected Phase 1B result. Its archive and
artifact hashes are recorded in
`provenance/UPSTREAM_AUDIT_DEPENDENCIES.json`. Phase 1C verifies this mapping
against both frozen source tables before using it.

## Frozen data vector

The Phase 1A alpha-unit data vector is reproduced from the H0DN table using:

- velocity column `vp_2mpp`;
- \(q_0=-0.55\);
- \(j_0=1\);
- speed of light from `scipy.constants`;
- no Hubble-flow redshift cut.

For row \(i\),

\[
x_i=0.2\left[
5\log_{10}\left(
\frac{1+z_{{\rm hel},i}}{1+z_{{\rm corr},i}}\,
c z_{{\rm corr},i}\,
k(z_{{\rm corr},i})
\right)-m_{B,i}\right].
\]

No intercept is needed in an exact-name contrast because every contrast sums
to zero.

## Frozen contrast basis

Rows are grouped only by byte-for-byte equality of the H0DN `name` field.
Groups follow first appearance in the H0DN table; rows within a group retain
H0DN order. For a group of size \(n\), the audit uses the \(n-1\) normalized
Helmert rows

\[
h_j=(\underbrace{1,\ldots,1}_{j},-j,0,\ldots,0)/
\sqrt{j(j+1)},\qquad j=1,\ldots,n-1.
\]

Embedding these rows in the 277-row space gives a 39-by-277 matrix \(A\).
Required identities are \(AA^\mathsf T=I_{39}\) and \(AZ=0\), where \(Z\)
is the exact-name incidence matrix.

The observed contrast vector is \(d=Ax\).

## Frozen covariance baselines

Let \(C_H\) be the 277-by-277 H0DN magnitude covariance. Let \(C_{SS}\) and
\(C_S\) be the mapped official STAT+SYS and STATONLY magnitude covariances.
Let

\[
v_i=\left[\log_{10}(v_{{\rm corr},i}+240)-
\log_{10}(v_{{\rm corr},i})\right]^2.
\]

The three ordered baselines are:

\[
S_0=A[C_H/25+\operatorname{diag}(v)]A^\mathsf T,
\]

\[
S_1=A(C_{SS}/25)A^\mathsf T,
\]

\[
S_2=A(C_S/25)A^\mathsf T.
\]

`PHASE1A_FULL` (\(S_0\)) is the known reproduction baseline.
`STAT_SYS_NO_ROWWISE_VELOCITY` (\(S_1\)) removes only the H0DN rowwise
velocity term from the contrast covariance. `STAT_ONLY` (\(S_2\)) then
replaces STAT+SYS by the official STATONLY matrix. These are nested
sensitivity baselines, not candidate corrections.

Two diagonal-only matrices, formed from the mapped STAT+SYS and STATONLY
diagonals before projection, are reported as structural diagnostics only.
They do not enter the primary sensitivity classification.

The audit records exact symmetry diagnostics before any transformation.
H0DN must be exactly symmetric. For official matrices, the maximum absolute
transpose difference must not exceed `1e-12`; the numerical calculation then
uses the explicitly recorded average \((C+C^\mathsf T)/2\). The mapped
STAT+SYS submatrix must equal \(C_H\) element by element before averaging.
No covariance entry is otherwise edited, clipped, regularized, fitted, or
rescaled.

## Quadratic form and reference probabilities

For each baseline,

\[
q=d^\mathsf T S^{-1}d
\]

is evaluated with a lower Cholesky factor and triangular solve. Cholesky
failure is a HOLD; a pseudoinverse is prohibited. The primary reference
probability is the lower tail

\[
p_{\rm low}=P(\chi^2_{39}\le q).
\]

Under the literal zero-mean Gaussian model with fixed known covariance:

- `p_low < 0.001`:
  `STRONG_LOW_DISPERSION_RELATIVE_TO_BASELINE`;
- `0.001 <= p_low < 0.01`:
  `LOW_DISPERSION_RELATIVE_TO_BASELINE`;
- `p_low >= 0.01`:
  `NO_LOW_DISPERSION_FLAG_RELATIVE_TO_BASELINE`.

Because component omission changes the assumed model, these probabilities
are reference diagnostics and are not multiplicity-adjusted hypothesis tests.

For each baseline the audit also reports the descriptive scalar
\(\hat s=q/39\) and the exact 95% chi-square interval

\[
\left[q/\chi^2_{39,0.975},\ q/\chi^2_{39,0.025}\right].
\]

This does not authorize covariance rescaling.

## Frozen ordered sensitivity classification

The ordered classification uses only whether each of \(S_0,S_1,S_2\) has
`p_low < 0.01`:

1. If \(S_0\) is not flagged:
   `NO_PHASE1A_BASELINE_LOW_FLAG`.
2. If \(S_0\) is flagged and \(S_1,S_2\) are not:
   `LOW_FLAG_REMOVED_WITHOUT_ROWWISE_VELOCITY_TERM`.
3. If \(S_0,S_1\) are flagged and \(S_2\) is not:
   `LOW_FLAG_PERSISTS_WITHOUT_ROWWISE_VELOCITY_BUT_NOT_WITH_STATONLY`.
4. If all three are flagged:
   `LOW_FLAG_PERSISTS_THROUGH_STATONLY`.
5. Every other flag pattern:
   `NONMONOTONIC_COMPONENT_SENSITIVITY`.

The words “removed” and “persists” describe only threshold behavior under
the ordered baselines. They do not identify a physical cause.

## Component diagnostics

The audit reports, without changing the classification:

- projected rowwise-velocity component \(S_0-S_1\);
- projected systematic component \(S_1-S_2\);
- minimum/maximum eigenvalues and trace for each component;
- generalized eigenvalues, trace ratios, and log-determinant ratios for
  \(S_0\) versus \(S_1\), and \(S_1\) versus \(S_2\);
- diagonal-only quadratic forms;
- the maximum within-group difference in the cosmographic model term.

A component need not be declared physically separable merely because its
matrix difference is positive semidefinite.

## Independent numerical verification

Required independent checks are:

- reproduce the known Phase 1A 39-mode value;
- evaluate every quadratic form again by symmetric eigendecomposition rather
  than Cholesky;
- rebuild the 39-dimensional contrast subspace from the null space of
  \(Z^\mathsf T\), rather than the Helmert construction;
- apply 32 fixed-seed random orthogonal changes of contrast coordinates;
- compare `scipy.stats.chi2.cdf` with
  `scipy.special.gammainc(39/2, q/2)`;
- re-run from a clean copy and require byte-identical scientific result
  artifacts.

## Gates and tolerances

| Gate | Frozen requirement |
| --- | --- |
| Sources | both commits and all 9 locked files match size, SHA-256, and Git blob |
| Mapping dependency | 277 ordered, unique source and target rows; source-table identifiers and survey codes agree |
| Group structure | 30 groups, 69 rows, 39 modes; every multi-row group has more than one survey code |
| Contrast basis | shape 39-by-277; rank 39; orthogonality and group-annihilation errors at most `2e-14` |
| Covariance schemas | dimensions 277 and 1701; finite; official transpose error at most `1e-12` |
| STAT+SYS lineage | all 76,729 mapped elements exactly equal H0DN |
| Positive definiteness | all five projected analysis covariances pass Cholesky and have minimum eigenvalue greater than `1e-14` |
| Known baseline | Phase 1A contrast chi-square agrees within `2e-8` |
| Reference solver | every primary/reference quadratic-form difference at most `2e-9` |
| Alternative basis | every quadratic-form difference at most `2e-8` |
| Orthogonal invariance | all 32 trials agree within `2e-9` |
| Probability implementation | absolute CDF difference at most `2e-14` |
| Package | tests, schemas, reports, manifest, hashes, clean reproduction, and delivery identity pass |

Tolerance changes after new Phase 1C results are observed are prohibited.

## Status rules

Required provenance and numerical gates must pass before interpretation:

- `HOLD_CONTRACT_MISMATCH`
- `HOLD_SOURCE_MISMATCH`
- `HOLD_DEPENDENCY_MAPPING_MISMATCH`
- `HOLD_INPUT_OR_GROUP_MISMATCH`
- `HOLD_COVARIANCE_LINEAGE_MISMATCH`
- `HOLD_NUMERICAL_CROSSCHECK_FAILURE`
- `HOLD_VERIFICATION_FAILURE`
- `AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC`

A HOLD leaves the failure visible and suppresses the scientific
classification.

## Frozen exclusions and non-claims

- No row, object, survey, covariance component, or off-diagonal element is
  removed from the published source files.
- No object, group, survey pair, sky region, or redshift bin is ranked or
  scanned.
- No post-result threshold, subgroup, covariance blend, or regularization is
  selected.
- No preferred covariance scale is inferred.
- No cause is assigned to a threshold transition.
- No corrected \(a_B\), \(M_B\), \(H_0\), or tension significance is
  calculated.
- No claim is made that the official covariance is complete, known without
  uncertainty, or physically validated.
- This is independent work, not H0DN or Pantheon+ collaboration validation
  or peer review.

## Stop rule

Phase 1C stops after the aggregate 39-mode component-sensitivity
classification and package verification. Any object-, survey-, or
redshift-resolved follow-up requires a new frozen contract.

