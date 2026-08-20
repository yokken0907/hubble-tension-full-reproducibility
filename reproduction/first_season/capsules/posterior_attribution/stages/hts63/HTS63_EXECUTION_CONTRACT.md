# HTS63 execution contract

## Stage
`HTS63_EXACT_VARIABLE_SHAPLEY_AND_OWEN_COALITION_AUDIT`

## Question
Within the HTS62 conditional four-dimensional residual, which fixed coordinates receive
posterior-distance allocation under:
1. unrestricted exact four-player Shapley averaging over all 24 variable orders, and
2. coalition-respecting Owen averaging over the two fixed HTS62 blocks?

## Fixed variables and coalitions
- omega_b
- tau
- n_s
- logA
- BARYON_TILT = (omega_b, n_s)
- TAU_AMPLITUDE = (tau, logA)

## Operations
- exact subset Mahalanobis game for all 16 variable coalitions
- exact unrestricted Shapley values
- exact Owen values over all 8 block-contiguous orders
- all-order marginal contribution ranges
- exact reconciliation of Owen block sums to HTS62 block Shapley values
- forward/reverse, source/target LOO and 30%/50% burn-in

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- conditional-correlation minimum eigenvalue > 1e-6
- conditional-correlation condition number <= 500
- Shapley, Owen and block-reconciliation closure <= 1e-8
- minimum permutation marginal contribution >= -1e-8
- maximum LOO conditional-distance drift <= 0.25
- maximum LOO Shapley/Owen share drift <= 0.15
- maximum LOO effective-variable-count drift <= 0.5
- maximum LOO coalition-shift drift <= 0.15
- corresponding burn-in limits are identical
- independent raw-chain reconstruction PASS

## Boundary
Coordinate allocations depend on the chosen variables and coalition structure. They are
symmetric posterior-distance bookkeeping, not causal effects, physical energy shares,
independent constraints or likelihood-component contributions.
