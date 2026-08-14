# HTS62 execution contract

## Stage
`HTS62_FIXED_BLOCK_SHAPLEY_AND_ORDER_SENSITIVITY_AUDIT`

## Question
How is the HTS59 conditional four-dimensional posterior distance distributed between the fixed coordinate blocks BARYON_TILT=(omega_b,n_s) and TAU_AMPLITUDE=(tau,logA), once cross-block correlation and block-entry order are made explicit?

## Operations
- condition the four direct variables on the frozen tangent-normal plane exactly as in HTS59
- calculate marginal and conditional block Mahalanobis increments in both orders
- average the two orders with a two-player Shapley decomposition
- record cross-block interaction/order sensitivity and block canonical correlations
- repeat forward/reverse, source/target LOO, and 30%/50% burn-in

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- minimum conditional-correlation eigenvalue > 1e-6
- maximum conditional-correlation condition number <= 500
- maximum Shapley closure error <= 1e-8
- LOO: conditional-distance drift <= 0.25, block-share drift <= 0.15, order-sensitivity drift <= 0.15, canonical-correlation drift <= 0.10
- same burn-in limits
- independent raw-chain reconstruction PASS

## Boundary
Shapley values are symmetric bookkeeping of posterior Mahalanobis distance between fixed coordinate blocks. They are not causal data attribution, physical energy sectors, independent significance, or a new cosmological model.
