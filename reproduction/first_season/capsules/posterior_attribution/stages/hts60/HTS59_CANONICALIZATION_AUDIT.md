# HTS59 canonicalization audit

`PASS_TN2D_SUFFICIENCY_AND_CONDITIONAL_4D_RESIDUAL_AUDIT`

Integrity:
- outer ZIP SHA256: `e61ee6b6cca4dadcb32b9bf7c75c869c1a39927d5ca5638e3542f1467f9b3245`
- ZIP CRC: PASS
- internal SHA256 manifest: 27/27 PASS
- independent raw-chain and LOO reconstruction: PASS
- maximum Schur closure error: `9.95e-14`

Primary findings:
- conditional four-dimensional distance-squared fractions range from about 0.185 to 0.965
  across directed edges.
- BASE-to-ACT forward: 0.821; reverse: 0.855.
- BASE-to-PR4 forward: 0.913; reverse: 0.965.
- ACT-to-FULL_FIXED forward is the main exception at 0.185.
- n_s is the largest absolute conditional univariate coordinate for most directions, while
  omega_b dominates ACT-to-FULL_FIXED reverse and tau dominates ORIGINAL-to-FIXED.
- These univariate coordinates are not additive contributions.
