# HTS64 execution contract

## Stage
`HTS64_WITHIN_BLOCK_REPARAMETERIZATION_INVARIANCE_AUDIT`

## Question
Which HTS63 conclusions survive invertible coordinate changes inside the fixed HTS62 blocks?

## Fixed blocks
- BARYON_TILT = (omega_b, n_s)
- TAU_AMPLITUDE = (tau, logA)

## Predeclared transformations
- all 49 combinations of within-block rotations at 0, 15, 30, 45, 60, 75 and 90 degrees
  in conditionally standardized coordinates
- physical amplitude reparameterization `logA_minus_2tau = logA - 2*tau`

## Operations
- recompute exact Shapley and Owen allocations in every transformed basis
- require exact invariance of total conditional Mahalanobis distance
- require exact invariance of fixed-block Shapley totals
- record the range of top-coordinate shares and effective-variable counts
- record turnover of the dominant transformed coordinate
- repeat under source/target leave-one-chain-out and 30%/50% burn-in

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- total-distance and fixed-block invariance error <= 1e-8
- transformed correlation minimum eigenvalue > 1e-6
- transformed condition number <= 500
- minimum permutation marginal contribution >= -1e-8
- allocation closure <= 1e-8
- maximum LOO conditional-distance drift <= 0.25
- maximum LOO top-share-range drift <= 0.15
- maximum LOO effective-count-range drift <= 0.5
- maximum LOO physical-amplitude top-share drift <= 0.15
- identical burn-in limits
- independent raw-chain reconstruction PASS

## Boundary
A change of variable allocation under an invertible within-block transformation is not a
scientific failure. It establishes that only the block total, not the individual coordinate
allocation, is invariant under the tested reparameterizations.
