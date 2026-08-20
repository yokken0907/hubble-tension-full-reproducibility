# HTS61 execution contract

## Stage
`HTS61_CONDITIONAL_EIGENMODE_IDENTIFIABILITY_AND_SUBSPACE_STABILITY_AUDIT`

## Question
Which HTS60 conditional modes are individually identifiable from eigengaps, and which are stable only as near-degenerate subspaces?

## Frozen inputs
- the five HTS51 release endpoints
- exact released six/eight numbered chains and weights
- 30% primary and 50% sensitivity burn-in
- the HTS59/60 six-variable and conditional-four-variable basis
- no new posterior root, model, likelihood or parameter

## Predeclared method
- adjacent relative eigengap threshold: `0.12`
- adjacent modes below this threshold form one identifiability cluster
- individual modes are matched across perturbations by the permutation maximizing total absolute eigenvector overlap
- clustered modes are judged by subspace principal angles, not by individual labels
- coordinate blocks are fixed before execution:
  - `BARYON_TILT = span(omega_b, n_s)`
  - `TAU_AMPLITUDE = span(tau, logA)`
- source and target LOO, burn-in sensitivity and cross-endpoint block alignment are recorded
- edge contributions are reported both for the top individual mode and its full identifiability cluster

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- minimum conditional eigenvalue > 1e-6
- maximum conditional condition number <= 500
- selected coordinate-block mode pairs must form a disjoint partition of all four modes
- maximum LOO singleton-mode angle <= 10 degrees
- maximum LOO near-degenerate-cluster principal angle <= 8 degrees
- maximum LOO coordinate-block subspace angle <= 8 degrees
- corresponding burn-in limits: 10, 8 and 8 degrees
- independent reconstruction PASS

## Boundary
A small eigengap removes the right to assign a unique physical meaning to individual mode labels. A stable subspace is not a newly discovered physical sector.
