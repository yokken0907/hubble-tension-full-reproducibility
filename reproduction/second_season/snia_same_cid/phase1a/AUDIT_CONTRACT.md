# Frozen contract: H0DN SN Ia residual-deficit localization audit

Contract identifier: `H0DN-SNIA-RESIDUAL-PHASE1A-20260730-01`

Freeze date: 2026-07-30 (Asia/Tokyo)

## Question

Under the frozen public H0 Distance Network (H0DN) one-intercept,
fixed-covariance model, is the already observed low SN Ia Hubble-flow
residual chi-square disproportionately localized in exact duplicate-name
contrast modes, or is the deficit distributed across the duplicate-name and
between-name subspaces in proportion to their dimensions?

This is a fixed-model localization and numerical-traceability audit. It is not
a search for a corrected covariance, a corrected Hubble constant, an
astrophysical systematic, or a resolution of the Hubble tension.

## Chronology and prior knowledge

Before this contract was written, Phase 0 had already established:

- 277 table rows and 238 unique exact name strings;
- 39 duplicate-name degrees of freedom;
- the frozen one-intercept result
  \(a_B=0.7163834210954622\) with
  \(\sigma(a_B)=0.0018926416391806472\);
- the minimum residual value
  \(\chi^2=206.7606364373241\) for 276 degrees of freedom.

Consequently, the global low-tail probability is not a prospectively
discovered result in this audit. The prospectively frozen result is the
two-subspace partition and its single conditional localization test. No
within/between partition value was evaluated before this contract was frozen.

## Frozen public source

- Upstream repository: `https://github.com/StefCas789/H0DN.git`
- Commit: `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- Hubble-flow table: `data/sn1a_hf_pp.dat`
- Magnitude covariance: `data/sn1a_covar_pp.dat`
- Source register: `provenance/SOURCE_LOCK.tsv`
- Expected tracked paths: 69
- Expected table SHA-256:
  `6b3dd6591cfaade2a6bf4bdb632fafc504f1449b9c07db4176a14e8e2366258f`
- Expected covariance SHA-256:
  `db2b84f18bf8319b0c6d7da46d574e58dce08de913e38e911ea6e0f8aa8a8aa6`

The upstream bytes are not redistributed.

## Frozen data transformation

The audit independently parses the two public input files. It reproduces the
frozen H0DN choices:

- velocity column `vp_2mpp`;
- \(q_0=-0.55\);
- \(j_0=1\);
- velocity dispersion \(240\ {\rm km\,s^{-1}}\);
- no Hubble-flow redshift cut.

For row \(i\), the alpha-unit datum is

\[
d_i=0.2\left[
5\log_{10}\left(
\frac{1+z_{{\rm hel},i}}{1+z_{{\rm corr},i}}\,
c z_{{\rm corr},i}\,
k(z_{{\rm corr},i})
\right)-m_{B,i}\right],
\]

using the frozen relativistic velocity/redshift conversion and cosmographic
series. The alpha covariance is

\[
C_\alpha=C_m/25+
\operatorname{diag}\left[
\left(\log_{10}(v_{\rm corr}+240)-\log_{10}v_{\rm corr}\right)^2
\right].
\]

No covariance element is zeroed, rescaled, fitted, regularized, or removed.

## Identifier-defined grouping

Rows are grouped only by byte-for-byte equality of the name field in
`sn1a_hf_pp.dat`. Case, punctuation, and spelling are not normalized. No
external object resolver or manual merge is permitted.

Let \(Z\) be the 277-by-238 incidence matrix whose columns follow first
appearance of each exact name string. Every row contains exactly one unit
entry. Let \(X_0=\mathbf 1\) and \(X_1=Z\).

The labels “duplicate-name” and “between-name” describe this exact public
identifier partition. They do not independently prove physical object
identity or survey provenance.

## Primary implementation

1. Compute a lower Cholesky factor \(C_\alpha=LL^\mathsf T\).
2. Whiten \(d\), \(X_0\), and \(X_1\) with triangular solves by \(L\).
3. Obtain orthonormal bases for the two nested design spaces with
   rank-revealing QR.
4. Compute

\[
\chi^2_{\rm total}
=\|(I-P_0)L^{-1}d\|^2,
\]

\[
\chi^2_{\rm duplicate}
=\|(I-P_1)L^{-1}d\|^2,
\]

\[
\chi^2_{\rm between}
=\chi^2_{\rm total}-\chi^2_{\rm duplicate}.
\]

The expected degrees of freedom are respectively 276, 39, and 237.

## Independent reference implementation

The reference calculation does not reuse the QR projections. It uses
Cholesky solves for \(C_\alpha^{-1}d\) and
\(C_\alpha^{-1}X\), solves the two GLS normal systems, and evaluates each
quadratic residual directly. Agreement with the primary implementation is a
required numerical gate.

## Frozen statistical interpretation

Only under the literal fixed, known, Gaussian covariance model:

\[
\chi^2_{\rm duplicate}\sim\chi^2_{39},\qquad
\chi^2_{\rm between}\sim\chi^2_{237},
\]

and the two quantities are independent. Conditional on their sum,

\[
R=\frac{\chi^2_{\rm duplicate}}{\chi^2_{\rm total}}
\sim {\rm Beta}(39/2,237/2).
\]

The single primary localization test is two-sided with
\(\alpha_{\rm localization}=0.01\):

- lower Beta tail \(\le 0.005\):
  `LOW_CHI2_LOCALIZED_TO_DUPLICATE_NAME_CONTRASTS`;
- upper Beta tail \(\le 0.005\):
  `LOW_CHI2_LOCALIZED_TO_BETWEEN_NAME_MODES`;
- otherwise:
  `LOW_CHI2_PROPORTIONAL_ACROSS_NAME_PARTITIONS`.

If the already known global lower-tail probability is greater than 0.01, the
classification is instead `NO_STRONG_GLOBAL_LOW_CHI2_UNDER_FROZEN_MODEL`.

Marginal lower-tail probabilities for the 39- and 237-degree components are
reported as descriptive secondary quantities. They are not additional primary
tests and are not used to relabel the primary conditional result.

## Analytic-distribution implementation check

A fixed-seed Monte Carlo check uses 20,000 standard-normal vectors in the
whitened 277-dimensional space, seed `20260730`. This tests only the
implementation of the frozen analytic null:

- the mean duplicate component must be within five Monte Carlo standard
  errors of 39;
- the mean between component must be within five Monte Carlo standard errors
  of 237;
- the mean ratio must be within five Monte Carlo standard errors of
  \(39/276\).

This simulation cannot validate that the published covariance is complete,
known without uncertainty, or physically correct.

## Gates and tolerances

| Gate | Frozen requirement |
| --- | --- |
| Source | commit and all 69 registered paths, sizes, and SHA-256 values match |
| Input schema | 277 rows, 238 exact names, 39 duplicate rows, 277-by-277 finite symmetric covariance |
| Covariance | Cholesky succeeds and minimum eigenvalue exceeds \(10^{-12}\) |
| Group design | every row sum is one; ranks are 1 and 238 |
| Known baseline | \(a_B\), its error, total chi-square, and degrees of freedom reproduce Phase 0 within \(5\times10^{-12}\) |
| Partition closure | total equals duplicate plus between within \(2\times10^{-9}\) |
| Degrees of freedom | exactly 276 = 39 + 237 |
| Reference solver | all three chi-squares agree within \(2\times10^{-8}\) |
| Permutations | 32 fixed-seed simultaneous row/column permutations agree within \(2\times10^{-8}\) |
| Monte Carlo | all three fixed five-standard-error mean checks pass |
| Package | tests, result schema, reports, manifest, hashes, and delivery identity pass |

Tolerance changes after results are observed are prohibited.

## Status rules

Required numerical and provenance gates must pass before scientific
classification.

- `HOLD_SOURCE_MISMATCH`
- `HOLD_INPUT_OR_DESIGN_MISMATCH`
- `HOLD_BASELINE_REPRODUCTION_MISMATCH`
- `HOLD_NUMERICAL_CROSSCHECK_FAILURE`
- `HOLD_VERIFICATION_FAILURE`
- `AUDIT_COMPLETE_NO_STRONG_GLOBAL_LOW_CHI2_UNDER_FROZEN_MODEL`
- `AUDIT_COMPLETE_LOW_CHI2_LOCALIZED_TO_DUPLICATE_NAME_CONTRASTS`
- `AUDIT_COMPLETE_LOW_CHI2_LOCALIZED_TO_BETWEEN_NAME_MODES`
- `AUDIT_COMPLETE_LOW_CHI2_PROPORTIONAL_ACROSS_NAME_PARTITIONS`

A HOLD stops scientific interpretation. Failed checks remain visible and are
not removed, weakened, or silently rerun under a changed contract.

## Frozen exclusions and non-claims

- No row, duplicate name, outlier, or covariance component is removed.
- No redshift, velocity, host, survey, sky, residual-sign, or object-level
  scan is performed.
- No individual object is ranked or named as anomalous.
- No covariance rescaling or intrinsic-scatter parameter is estimated.
- No physical cause is assigned to a low chi-square.
- No corrected \(a_B\), \(M_B\), or \(H_0\) is inferred.
- No Hubble-tension significance is recalculated.
- A result applies only to the frozen one-intercept, fixed-known-covariance
  model and exact-name partition.
- The audit is independent work, not H0DN or Pantheon+ collaboration
  validation or peer review.

## Stop and follow-up rule

Phase 1A stops after the partition classification and package verification.

- A duplicate-name localization may justify a separately contracted audit of
  duplicate-row construction and covariance provenance.
- A between-name localization may justify a separately contracted,
  source-gated residual projection.
- A proportional result may justify a separately contracted audit of
  covariance calibration or covariance-estimation uncertainty.

None of those follow-ups is executed here.

## Amendment policy

Any change after contract freeze requires a numbered row in
`provenance/CONTRACT_AMENDMENTS.tsv`, stating whether partition results had
already been observed and whether interpretation changes. An undisclosed
amendment forces `HOLD_VERIFICATION_FAILURE`.
