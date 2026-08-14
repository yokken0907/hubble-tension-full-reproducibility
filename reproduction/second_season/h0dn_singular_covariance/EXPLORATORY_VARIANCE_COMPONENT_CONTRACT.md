# Exploratory Cepheid interaction-variance contract

Version: 0.1.0  
Frozen before numerical execution of this model.

## Status and motivation

This is an explicitly post-hoc, exploratory extension. It was motivated by the
internally frozen row-standardization failure and the subsequent exact
decomposition showing that all 72 covariance-nullspace degrees of freedom are
the two-way interaction subspace of the complete 37 host × 3 anchor R22
HST-Cepheid table.

It is not part of the primary audit, does not alter the public H0DN baseline,
and cannot be described as a corrected Hubble-constant result.

## Frozen source and data selection

- Upstream source: the commit and every tracked file frozen in
  `provenance/SOURCE_LOCK.tsv`.
- Baseline matrices: the untouched public `config.ini` execution.
- Variance-component rows: all and only the 111 host-equation rows satisfying
  `method == "ceph_hst"` and `source == "R22"`.
- The selected rows must form a complete, duplicate-free 37 host × 3 anchor
  table.
- No host, anchor, cell, or other equation may be removed, clipped, reweighted,
  or selected using its residual.

## Generative covariance model

For the public design matrix \(A\), data vector \(y\), and covariance \(C_0\),
fit

\[
y \sim \mathcal N(Ax,\; C(\tau)), \qquad
C(\tau) = C_0 + \tau^2 R,
\]

where \(R\) is diagonal with value one on the 111 frozen Cepheid rows and zero
elsewhere. The parameter \(\tau\), in magnitudes, represents additional
independent cell-level host–anchor interaction dispersion. This is one
deliberately simple generative repair; it is not asserted to be the unique or
physical explanation of the interaction residuals.

## Frozen estimators

### Primary

Estimate \(\tau\) by minimizing the profiled REML deviance, up to constants
independent of \(\tau\):

\[
D_{\mathrm{REML}}(\tau) =
\log |C(\tau)| +
\log |A^\mathsf{T} C(\tau)^{-1} A| +
r^\mathsf{T} C(\tau)^{-1} r.
\]

The associated \(H_0\) and uncertainty are the conditional GLS values at the
REML optimum; they do not include uncertainty in \(\tau\).

### Secondary checks

1. Minimize the profiled ML deviance
   \(\log |C(\tau)| + r^\mathsf{T}C(\tau)^{-1}r\).
2. Compute the covariance-nullspace moment estimate
   \[
   \tau_{\mathrm{null}} =
   \sqrt{\|P_{\mathrm{null}}y\|_2^2 / 72}.
   \]
3. Report the GLS result at the nullspace-moment value.

The ML and moment results are diagnostics, not competing preferred estimates.

## Numerical procedure fixed in advance

- Search in \(\log \tau\) over \(10^{-5} \leq \tau \leq 0.3\) mag.
- Use bounded scalar minimization with absolute tolerance \(10^{-12}\) in
  \(\log\tau\).
- At every finite-\(\tau\) evaluation, solve the full-rank covariance and normal
  systems with Cholesky factorization; do not use a pseudoinverse.
- Require the covariance and normal matrices to be positive definite.
- Form approximate profile intervals where the deviance rises by 1.0 and
  3.841459 on either side of the optimum. Mark a side as unbounded if no
  crossing occurs inside the frozen search interval.
- Evaluate a fixed log-spaced profile grid from \(10^{-5}\) to \(0.3\) mag with
  161 points, augmented by the fitted and moment values.

## Invariance and consistency checks

1. Repeat each fitted estimator after exact diagonal row standardization,
   transforming \(A\), \(y\), \(C_0\), and \(R\) by the same congruence.
2. Require absolute agreement below:
   - \(10^{-8}\) mag for fitted \(\tau\);
   - \(10^{-8}\) km s\(^{-1}\) Mpc\(^{-1}\) for \(H_0\);
   - \(10^{-8}\) for conditional \(\sigma(H_0)\);
   - \(10^{-7}\) for profile-deviance differences after subtracting their
     representation-dependent constant offset.
3. Require \(C(\tau)\) to have rank 255 at both fitted optima under the public
   \(10^{-10}\) absolute rank cutoff.
4. Require the selected-cell count, host count, anchor count, and interaction
   degrees of freedom to be 111, 37, 3, and 72.

Failure of a check is retained and reported; the model or tolerances will not
be silently changed.

## Interpretation boundary

This model asks whether one explicit, representation-invariant variance
component can absorb the exact-support inconsistency and how the conditional
network fit responds. A nonzero fitted \(\tau\) does not identify an
astrophysical cause, show that any named host or anchor is erroneous, validate
the independent-cell assumption, or resolve the Hubble tension. No value from
this extension may be labeled a corrected \(H_0\).
