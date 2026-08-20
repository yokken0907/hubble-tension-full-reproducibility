# Exploratory Cepheid interaction-variance model

This report is governed by
`EXPLORATORY_VARIANCE_COMPONENT_CONTRACT.md`. The model and numerical
checks were frozen before these values were calculated.

## Main exploratory result

The fitted additional independent host–anchor cell dispersion is
`tau = 0.02224362 mag` by REML.
The profile-deviance-rise-1 interval is
`[0.02051154, 0.02423377] mag`.
At that fitted value, the conditional network result is
`H0 = 73.49432597 +/- 0.81186706`
km/s/Mpc.

For comparison, the untouched public Moore–Penrose baseline is
`H0 = 73.49875364 +/- 0.80880003`
km/s/Mpc. The exploratory conditional shift is
`-0.00442767 km/s/Mpc`.
This comparison does not make the exploratory result a corrected
estimate.

## Cross-checks

- ML gives `tau = 0.02219946 mag`.
- The covariance-nullspace moment gives `tau = 0.02224429 mag` and, at that fixed value, `H0 = 73.49432571 +/- 0.81186724 km/s/Mpc`.
- Exact row standardization changes the REML optimum by `2.497e-09 mag`, `H0` by `9.628e-10`, and its conditional uncertainty by `6.803e-10`.
- The covariance rank is `255` at the REML optimum, so this explicit model removes the 72 zero modes.
- The fixed full profile-grid invariance check has status **FAIL**; its largest absolute centered-deviance discrepancy is `1.106e+01`.
  This maximum occurs at `tau = 1.0e-05 mag`, where the profile deviance is more than `3.563e+08` above its minimum. Over the fitted 95% REML profile interval, the largest discrepancy is only `2.103e-11`.

Overall contract-check status: **PASS_WITH_FLAGGED_PROFILE_NUMERICS**.

## Scientific boundary

The fitted nonzero dispersion shows that one explicit full-rank
generative extension can absorb the exact-support inconsistency without
the Moore–Penrose representation ambiguity. It does not determine
whether the interaction is caused by rounding, bookkeeping, correlated
calibration, or astrophysics; it also does not validate the independent
cell-scatter assumption. No host or anchor was removed, and the result
does not resolve the Hubble tension.
