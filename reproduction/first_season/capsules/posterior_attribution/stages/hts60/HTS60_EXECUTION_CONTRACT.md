# HTS60 execution contract

## Stage
`HTS60_CONDITIONAL_4D_EIGENMODE_LOCALIZATION_AUDIT`

## Question
After conditioning omega_b, tau, n_s and logA on the frozen tangent-normal coordinates,
is the HTS59 residual distance concentrated in one or a few correlated posterior modes?

## Fixed inputs
- five HTS51 contract-labelled release endpoints
- exact released six/eight numbered chains and weights
- 30% primary and 50% sensitivity burn-in
- the HTS59 six-variable basis and release graph
- cache root `${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

## Operations
- form the source-posterior conditional correlation matrix of omega_b, tau, n_s and logA
- eigendecompose it with deterministic eigenvector signs
- decompose conditional Mahalanobis distance squared exactly into eigenmode contributions
- report top-one and top-two contribution fractions and effective contributing-mode count
- report direct-variable loadings only as linear diagnostics
- repeat under source and target leave-one-chain-out and burn-in sensitivity

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- minimum conditional-correlation eigenvalue > 1e-6
- maximum conditional-mode condition number <= 500
- maximum decomposition closure error <= 1e-8
- maximum LOO conditional-distance drift <= 0.25
- maximum LOO top-one fraction drift <= 0.15
- maximum LOO effective-mode-count drift <= 0.5
- corresponding burn-in limits: 0.25, 0.15 and 0.5
- independent raw-chain reconstruction PASS

## Boundary
The modes are source-posterior linear combinations of conditionally standardized direct
variables. They are not new physical parameters, independent constraints, or causal data
component contributions.
