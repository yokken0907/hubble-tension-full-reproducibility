# HTS67 execution contract

## Stage
`HTS67_SYMMETRIC_POOLED_METRIC_DIRECTIONALITY_ROBUSTNESS_AUDIT`

## Question
Do the HTS59–66 conditional four-dimensional distance and fixed-block bookkeeping remain stable when the directed source-posterior covariance metric is replaced by a predeclared symmetric endpoint-pair metric?

## Frozen endpoints and coordinates
The same five released endpoints and the same six-dimensional vector used by HTS59–65:

1. tangent_DESI_sigma
2. normal_DESI_sigma
3. omega_b
4. tau
5. n_s
6. logA

The frozen conditional blocks remain:

- `BARYON_TILT = (omega_b, n_s)`
- `TAU_AMPLITUDE = (tau, logA)`

No new physical parameter, likelihood component, eigenmode, coalition search or cosmological model is introduced.

## Exact canonical inputs
- exact `HTS62_RESULTS_FOR_REVIEW.zip`, outer SHA256 `f51b60503ae20361c9fbcdff4d50b2bac74266b0a270545cb71fe60b582c7a18`
- exact `HTS66_CORR_RESULTS_FOR_REVIEW.zip`, outer SHA256 `92556d7b755f4c7ff2bab1f4ab8cc568a384720cf860164c66810544cf89f54a`
- the retained HTS63 raw-chain cache for the five endpoint contracts

## Predeclared symmetric metrics
### Primary
`ARITHMETIC_COVARIANCE_POOL`

\[
C_{\rm sym}=\frac{C_A+C_B}{2}
\]

### Sensitivity
`PRECISION_MEAN_POOL`

\[
C_{\rm sym}=\left[\frac{C_A^{-1}+C_B^{-1}}{2}\right]^{-1}
\]

Both are invariant under endpoint exchange. Neither is selected after seeing the result.

## Operations
- verify exact HTS62 and HTS66_CORR result archives
- verify the five release endpoint signatures and chain inventories
- calculate symmetric 6D, tangent-normal and conditional 4D Mahalanobis distances
- require exact Schur-complement closure
- repeat the HTS62 two-block sequential and Shapley bookkeeping under each symmetric metric
- compare symmetric classifications with the frozen HTS62 forward/reverse baseline
- source/target leave-one-chain-out, 30%/50% burn-in and metric-pooling sensitivity
- independent raw-chain reconstruction

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- minimum full correlation eigenvalue >= 1e-8
- minimum conditional eigenvalue >= 1e-6
- maximum full condition number <= 1e8
- maximum conditional condition number <= 500
- decomposition and Shapley closure <= 1e-8
- endpoint-swap invariance error <= 1e-10
- LOO: conditional-distance drift <= 0.25, block-share drift <= 0.15, order-sensitivity drift <= 0.15, canonical-correlation drift <= 0.10
- same burn-in limits
- between the two symmetric pooling conventions: block-share difference <= 0.15, order-sensitivity difference <= 0.15, and at least 6/7 primary classifications agree
- independent raw-chain audit PASS

## Outcome logic
- numerical, support, closure, symmetry or stability failure: HOLD
- strong dependence on the symmetric pooling convention: HOLD
- stable symmetric result preserving directed-consensus edges: PASS and close the metric-directionality question with scope
- stable symmetric result that changes a directed-consensus block pattern: PASS with an explicit directionality limitation, then close the question with narrower claims

## Boundary
This is descriptive posterior covariance geometry for correlated released endpoints. It is not independent tension significance, a likelihood-ratio test, profile likelihood, Bayes factor, causal likelihood contribution, uniquely physical block attribution or new cosmological physics.


## Portable exact-archive gate note

The current public replay uses a path-sanitized portable replica whose substantive scientific members are byte-identical to the historical archive. The historical outer SHA-256 and the portable gate SHA-256 are cross-recorded in `../../PORTABLE_EXACT_ARCHIVE_MAPPING.tsv`. This checksum update is a non-scientific portability edit.
