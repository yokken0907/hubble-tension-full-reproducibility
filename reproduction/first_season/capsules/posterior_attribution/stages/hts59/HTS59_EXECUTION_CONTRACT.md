# HTS59 execution contract

## Stage
`HTS59_TN2D_SUFFICIENCY_AND_CONDITIONAL_4D_RESIDUAL_AUDIT`

## Question
How much of each release-endpoint mean shift is captured by the frozen DESI tangent-normal plane, and how much remains after conditioning in the common direct-parameter sector omega_b, tau, n_s and logA?

## Frozen six-dimensional vector
1. tangent_DESI_sigma
2. normal_DESI_sigma
3. omega_b
4. tau
5. n_s
6. logA

The first two coordinates are the frozen HTS geometry. The remaining four are direct posterior columns. No new physical parameter is introduced.

## Method
- weighted endpoint covariance and correlation matrices
- directed source-metric Mahalanobis distance in 6D
- marginal 2D tangent-normal distance
- conditional 4D residual through the Schur complement
- exact identity audit: D6^2 = D_TN^2 + D_cond^2
- forward and reverse directions
- source-side and target-side leave-one-chain-out
- 30% primary and 50% sensitivity burn-in

## Gates
- minimum chain Kish rows >=100; maximum chain weight share <=0.35
- minimum correlation eigenvalue >=1e-8; condition number <=1e8
- maximum decomposition closure error <=1e-8
- LOO and burn changes in full/conditional distance <=0.35
- LOO and burn conditional-fraction change <=0.20
- LOO and burn log-condition-number change <=0.35
- independent raw-chain audit PASS

## Boundary
This is a covariance decomposition of correlated released posteriors, not independent tension significance, profile likelihood, Bayes factor or causal data attribution.
