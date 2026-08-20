# Post-hoc diagnostic contract for the row-scaling failure

Status: **frozen before the diagnostics below were generated**  
Freeze date: 2026-07-29 (UTC)  
Diagnostic version: 0.1.0-posthoc.1

## Trigger already observed

The equivalent diagonal row-standardization test frozen internally before its
output was examined retained covariance rank 183 and normal-matrix rank 64 but
changed the fitted value by approximately `-0.05245 km/s/Mpc`, exceeding the
frozen `1e-6` invariance threshold. No other influence result is used to select
the diagnostics below.

This document does not alter the original audit contract or reclassify that
failure. It fixes a bounded investigation of its mathematical source.

## Diagnostics fixed before execution

1. Verify exactly that the tested representation is
   `(A, y, C) -> (D A, D y, D C D)` with
   `D = diag(C)^(-1/2)` and all entries of `D` finite and nonzero.
2. Compute the congruence defect between:
   - the Moore-Penrose weight in the transformed representation, mapped back as
     `D @ pinv(D C D) @ D`; and
   - `pinv(C)`.
3. For both the public solution and the row-standardized Moore-Penrose
   solution, compute the covariance-nullspace support residual using
   `P0 = I - C @ pinv(C)` and `||P0 (y-Ax)||`.
4. Test exact feasibility of the degenerate-Gaussian support constraint
   `U0.T @ (y-Ax) = 0`, where `U0` spans the covariance nullspace at the
   public cutoff. Report ranks and the least-squares feasibility residual.
   Feasibility passes only when the residual is no larger than
   `1e-10 * max(1, ||U0.T @ y||)`.
5. If and only if the support constraint is feasible, solve the
   equality-constrained GLS problem and check its invariance. Otherwise record
   `HOLD_INCONSISTENT_SUPPORT`; do not force a constrained estimate.
6. Run a frozen fractional diagonal-regularization path
   `C_lambda = C + lambda * diag(diag(C))` for
   `lambda = 1e-2, 1e-3, ..., 1e-12`. Use direct inverses. Repeat after the
   exactly transformed representation, transforming the same regularizer as
   `D @ diag(diag(C)) @ D`, and require agreement within `1e-8 km/s/Mpc`.
7. Run the Moore-Penrose solver after deterministic scalings
   `D_p = diag(C)^(-p/2)` for
   `p = -2, -1, -0.5, 0, 0.5, 1, 2`. This is an exploratory map of the
   convention dependence, not a set of alternative scientific models.
8. Record whether the original IDL implementation also uses a
   Moore-Penrose inverse and its stated threshold rule.

## Interpretation rule

If the support constraint is inconsistent, the singular covariance does not
define a nonzero-likelihood degenerate Gaussian for any model parameter vector
at the stated numerical precision. In that case, Moore-Penrose results and
regularized limits are computational conventions unless an explicit generative
model or regularization metric is supplied. No diagnostic solution will be
called a corrected H0 value.
