# Phase 0 report: SN Ia Hubble-flow compression sufficiency

Authoritative status: **PASS_EXACT_SUFFICIENCY_FOR_FROZEN_LINEAR_MODEL**

Boundary marker: `FROZEN_MODEL_ONLY_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

## Result

The scalar intercept and variance are an exact sufficient statistic for every parameter-dependent contribution of this 277-object block to the frozen H0DN linear model.

The independent Cholesky reconstruction gives
\(a_B=0.716383421095462\) and
\(\sigma(a_B)=0.001892641639181\) from
277 Pantheon+ Hubble-flow rows. The untouched upstream values are
\(a_B=0.716383421095462\) and
\(\sigma(a_B)=0.001892641639181\).

The maximum residual on the 11-point, pre-specified full-versus-scalar
chi-square grid is `3.552714e-13`. Replacing the one scalar H0DN link by
all 277 correlated equations changes no fitted parameter by more than
`7.815970e-14` and no
parameter-covariance element by more than
`1.149254e-17`.
The largest tested difference across 16 seeded permutations is
`3.907985e-12`.

The untouched baseline remains
\(H_0=73.498753643607\pm0.808800025338\)
km/s/Mpc. The expanded calculation is an equivalent representation, not a new
or corrected H0 estimate.

## What the scalar compression omits

The expanded fit has a chi-square larger by
`206.760636437324`, equal within
`2.842171e-14` to the parameter-independent
Hubble-flow minimum chi-square
`206.760636437324`. The covariance rank and adjusted
degrees of freedom each increase by
`276`.

Therefore the scalar is sufficient for the network parameters under the frozen
one-intercept model, but it is not sufficient for residual diagnostics,
goodness-of-fit assessment, or testing richer redshift-, survey-, flow-, or
population-dependent models.

## Scope boundary

No covariance was zeroed, tuned, rescaled, or fitted. No constraint was
dropped. This audit does not validate the physical adequacy of the frozen
model, infer a Hubble-tension significance, produce a corrected H0, or show
that the Hubble tension is resolved. It is an independent computational audit,
not H0DN collaboration validation or peer review.

The frozen equations, tolerances, status rules, and non-claims are in
`PHASE0_CONTRACT.md`.
