# HTS65 execution contract

## Stage
`HTS65_EXHAUSTIVE_COALITION_PARTITION_SENSITIVITY_AUDIT`

## Question
How strongly do coordinate-level Owen allocations depend on the coalition partition itself,
after HTS64 established within-block basis sensitivity?

## Fixed inputs
- omega_b, tau, n_s and logA
- the HTS59 conditional four-dimensional residual game
- all five HTS51 endpoints and the frozen directed release graph
- released weights, exact chains, 30% primary and 50% sensitivity burn-in

## Exhaustive partition set
All 15 set partitions of four variables are enumerated exactly:
- one 4-variable coalition
- all 1+3 and 2+2 partitions
- all 1+1+2 partitions
- four singleton coalitions

The HTS62 partition `(omega_b,n_s)|(tau,logA)` is marked as canonical but is not allowed to
suppress alternative robustness probes.

## Operations
- exact Owen allocation for every partition
- exact respecting-order enumeration
- variable share ranges across all partitions
- dominant-variable turnover
- effective-variable-count range
- exact block-sum reconciliation for every partition
- source/target LOO and 30%/50% burn-in

## Gates
- minimum per-chain Kish effective rows >= 100
- maximum chain weight share <= 0.35
- exactly 15 partitions
- conditional-correlation minimum eigenvalue > 1e-6
- condition number <= 500
- minimum respecting-order marginal contribution >= -1e-8
- Owen closure and block reconciliation <= 1e-8
- maximum LOO conditional-distance drift <= 0.25
- maximum LOO variable-share-range drift <= 0.15
- maximum LOO effective-count-range drift <= 0.5
- maximum LOO coalition-shift drift <= 0.15
- maximum LOO canonical top-share drift <= 0.15
- identical burn-in limits
- independent raw-chain reconstruction PASS

## Boundary
Alternative partitions are mathematical robustness probes, not equally plausible physical
sector definitions. Partition sensitivity limits attribution; it does not select a preferred
alternative partition.
