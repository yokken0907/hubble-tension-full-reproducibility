# Phase 0 frozen contract: SN Ia Hubble-flow compression sufficiency

Contract identifier: `H0DN-SNIA-COMP-PHASE0-CONTRACT-20260730-01`

Freeze date: 2026-07-30 (Asia/Tokyo)

## Question

For the frozen public H0 Distance Network (H0DN) baseline model, does replacing
the full 277-object Pantheon+ Hubble-flow block by the published scalar
intercept \(a_B\) and its variance preserve all parameter-dependent
generalized-least-squares information passed to the distance network?

This is a computational sufficiency and traceability audit. It is not a test of
whether the frozen cosmographic, peculiar-velocity, light-curve, selection, or
covariance model is physically complete.

## Frozen source and baseline

- Upstream repository: `https://github.com/StefCas789/H0DN.git`
- Commit: `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- Baseline configuration:
  `h0_constrainer/h0_constrainer/configs/config.ini`
- Hubble-flow table: `data/sn1a_hf_pp.dat`
- Magnitude covariance: `data/sn1a_covar_pp.dat`
- Expected Hubble-flow object count: 277
- Velocity field column: `vp_2mpp`
- \(q_0=-0.55\), \(j_0=1\), velocity dispersion \(=240\) km/s
- No Hubble-flow redshift cut in the frozen baseline
- Upstream distance-network covariance policy:
  `scipy.linalg.pinv(atol=1e-10, rtol=0)`

The upstream files are not redistributed. `provenance/SOURCE_LOCK.tsv` freezes
all 69 tracked paths by Git object identifier, byte count, and SHA-256.

## Independent reconstruction

The audit will parse the Hubble-flow table and covariance independently of the
upstream loader. For each object it will reconstruct

\[
d_i = 0.2\left[
5\log_{10}\left(
\frac{1+z_{\rm hel}}{1+z_{\rm HD}}\,
c z_{\rm HD}\,
k(z_{\rm HD})
\right)-m_{B,i}\right],
\]

where the frozen upstream relativistic velocity/redshift conversions and
cosmographic expansion are reproduced literally. The alpha-unit covariance is

\[
C_\alpha = C_m/25 +
\operatorname{diag}\left[
\left(\log_{10}(v_{\rm corr}+240)-\log_{10}v_{\rm corr}\right)^2
\right].
\]

Using a Cholesky solve, not the upstream explicit matrix inverse, the independent
scalar reconstruction is

\[
\widehat a_B =
\frac{\mathbf 1^\mathsf{T}C_\alpha^{-1}d}
     {\mathbf 1^\mathsf{T}C_\alpha^{-1}\mathbf 1},
\qquad
\sigma^2_{a_B} =
\left(\mathbf 1^\mathsf{T}C_\alpha^{-1}\mathbf 1\right)^{-1}.
\]

## Exact compression identity

For the fixed alpha-offset grid

`[-8, -4, -2, -1, -0.5, 0, 0.5, 1, 2, 4, 8]`

in units of the independently reconstructed \(\sigma_{a_B}\), the audit will
test

\[
\chi^2_{\rm full}(a_B)-\chi^2_{\rm full}(\widehat a_B)
=
\frac{(a_B-\widehat a_B)^2}{\sigma^2_{a_B}}.
\]

The grid and tolerance are frozen before execution.

## Expanded-network embedding

The published scalar Hubble-flow link

\[
\log_{10}H_0 - 0.2M_B = \widehat a_B + 5
\]

will be replaced by 277 equations with the same coefficient row,
right-hand sides \(d_i+5\), and covariance \(C_\alpha\). The remaining H0DN
rows and covariance entries will be unchanged.

The audit will compare:

1. untouched upstream baseline;
2. an independently recompressed scalar-link network;
3. the full 277-row expanded network;
4. a blockwise-precision solution of the expanded network; and
5. 16 pre-seeded permutations of the expanded Hubble-flow rows and columns.

For the expanded fit, the total chi-square is expected to exceed the scalar
fit by the parameter-independent Hubble-flow minimum chi-square, and the
covariance rank and degrees of freedom are expected to increase by 276.

## Pre-specified gates and tolerances

All comparisons use absolute tolerances; no result-dependent tolerance changes
are permitted.

| Gate | Pass requirement |
| --- | --- |
| Source lock | commit, all 69 paths, sizes, and SHA-256 values match |
| Input schema | 277 rows, 277×277 finite symmetric covariance, positive diagonal |
| Covariance SPD | Cholesky succeeds; minimum eigenvalue \(>10^{-12}\) |
| Upstream baseline | exact counts/ranks and published rounded quantities within frozen tolerances |
| Alpha reconstruction | \(|\Delta a_B| \le 5\times10^{-14}\), \(|\Delta\sigma| \le 5\times10^{-14}\) |
| Cholesky/inverse cross-check | alpha, sigma, and chi-square differences \(\le 5\times10^{-13}\) |
| Profile identity | maximum absolute residual \(\le 2\times10^{-10}\) |
| Scalar-network replacement | every parameter and parameter-covariance element \(\le 2\times10^{-10}\); \(|\Delta H_0|,|\Delta\sigma_{H_0}|\le 2\times10^{-10}\) |
| Expanded-network equivalence | same parameter/covariance/H0 tolerances as scalar replacement |
| Normal-equation closure | maximum absolute normal-matrix/RHS difference \(\le 2\times10^{-9}\) |
| Chi-square closure | \(|(\chi^2_{\rm expanded}-\chi^2_{\rm scalar})-\chi^2_{\rm HF,min}|\le 2\times10^{-9}\) |
| Rank/dof closure | each increases by exactly 276 |
| Blockwise solver | every parameter/covariance element differs from expanded direct solve by \(\le 2\times10^{-10}\) |
| Permutations | all 16 runs meet parameter/covariance/H0 tolerance \(2\times10^{-9}\) |
| Scientific boundary | reports contain the frozen non-claim language |
| Package closure | tests, schemas, statuses, manifest, hashes, delivery ID, and no upstream bytes all pass |

The upstream rounded-baseline tolerances are: \(5\times10^{-5}\) for \(H_0\),
\(\sigma(H_0)\), and chi-square; \(5\times10^{-4}\) for \(M_B\) and
\(\sigma(M_B)\). Exact expected counts are 255 equations, 64 parameters,
covariance rank 183, and adjusted degrees of freedom 119.

## Status rules

- `PASS_EXACT_SUFFICIENCY_FOR_FROZEN_LINEAR_MODEL`: every gate passes.
- `HOLD_SOURCE_MISMATCH`: frozen source verification fails.
- `HOLD_PUBLIC_INPUT_INCOMPLETE`: required public inputs or schema are missing.
- `HOLD_BASELINE_RECONSTRUCTION_MISMATCH`: untouched upstream or independent
  intercept reconstruction fails.
- `HOLD_COMPRESSION_IDENTITY_FAILURE`: the fixed likelihood-profile identity
  fails.
- `HOLD_NETWORK_EMBEDDING_MISMATCH`: scalar/full network, normal-equation,
  chi-square, rank, blockwise, or permutation closure fails.
- `HOLD_VERIFICATION_FAILURE`: packaging, schema, provenance, or report gates
  fail.

Any HOLD status stops scientific interpretation. Failed checks remain recorded;
they are not silently weakened, removed, or relabeled.

## Frozen exclusions and non-claims

- No covariance term is zeroed, tuned, rescaled, or fitted.
- No rank-dropping constraint removal is performed.
- No redshift-bin, host-bin, survey-bin, or residual-trend search is performed
  in Phase 0.
- No new physical systematic parameter is introduced.
- No corrected \(H_0\), new uncertainty, or Hubble-tension significance is
  inferred.
- Exact sufficiency, if established, applies only to the frozen one-intercept,
  fixed-covariance linear model. It does not imply that one number is sufficient
  for diagnosing model inadequacy or for a richer model.
- Results are an independent computational audit, not H0DN collaboration
  validation, peer review, or evidence that the Hubble tension is resolved.

## Amendment policy

Changes after the contract-freeze commit require a numbered amendment in
`provenance/CONTRACT_AMENDMENTS.tsv`, including the reason, whether any result
had already been observed, and whether the change affects scientific
interpretation. Phase 0 may not pass if an undisclosed amendment exists.

