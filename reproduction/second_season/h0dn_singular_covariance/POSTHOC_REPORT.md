# Post-hoc diagnosis of the row-scaling failure

This report is governed by `POSTHOC_DIAGNOSTIC_CONTRACT.md` and is
explicitly separate from the primary audit generated under the project-internal frozen contract.

## Result

The failed row-standardization check is reproduced and is not caused by
a rank change. The transformed covariance retains the same 183-dimensional
range, but the Moore–Penrose precision mapped back to the original
coordinates differs from the original precision by relative Frobenius norm
`0.000380468374`.
This is the expected algebraic non-invariance of the Moore–Penrose inverse
under a general non-orthogonal congruence transformation of a singular
matrix.

The public-fit residual has covariance-nullspace projection norm
`0.188749083`;
the row-standardized Moore–Penrose fit has
`0.188749083`.
The exact degenerate-Gaussian support system is classified
**HOLD_INCONSISTENT_SUPPORT**, with least-squares feasibility residual
`0.188749083`
against the frozen tolerance
`1e-10`.

Therefore the singular covariance, taken literally, does not supply a
nonzero-likelihood support for any parameter vector at the stated
precision. The public Moore–Penrose result remains exactly reproducible,
but it is one computational convention for discarding inconsistent
nullspace information; it is not a representation-invariant consequence
of a fully specified degenerate Gaussian model.

## Exact location of the inconsistent support

The exhaustive public-metadata selection forms a complete
`37 host × 3 anchor`
R22 HST-Cepheid table. Its two-way additive interaction equals the
covariance-nullspace projection with maximum absolute closure error
`1.0658141e-13`.
The interaction RMS is
`0.0179152701 mag`,
its L2 norm is
`0.188749083 mag`, and
the largest absolute cell is
`0.0948468468 mag`
(N3147,
N4258).

This establishes where the exact-support inconsistency occurs but does
not establish why those public distance values differ from the additive
covariance support.

## Bounded diagnostic maps

Across the frozen scaling powers, numeric Moore–Penrose solutions span
`H0 = 71.76693328` to `73.52647030 km/s/Mpc`.
Restricting to scalings that preserve the public covariance rank gives
`73.41815460` to `73.52647030 km/s/Mpc`.
The wider range includes two cases where the fixed absolute cutoff also
changes rank.
These are not alternative scientific estimates.

The fractional diagonal-regularization path was repeated in both
representations using the exactly transformed regularizer. The largest
numerically successful cross-representation H0 discrepancy was
`8.64017852e-05 km/s/Mpc`.
Rows at extremely small regularization can become floating-point
ill-conditioned and are retained with their status.
For the well-resolved part of the path, the limit approaches the
row-standardized Moore–Penrose convention while chi-square diverges as
the added independent variance tends to zero, consistent with the
nonzero support residual.

## Consequence

A publication-grade next step is to replace the singular, rounded
covariance-only encoding by an explicit latent-error or expanded-parameter
generative model. That model would state the duplicated measurements and
shared anchor/MAS/HMS terms directly, avoid an inconsistent nullspace, and
make any regularization or rounding uncertainty explicit. This audit does
not choose such a model and does not report a corrected H0.

A separately contracted exploratory implementation of one such model is
reported in `EXPLORATORY_REPORT.md`. It does not alter this diagnosis or
retroactively become part of the internally frozen primary audit.
