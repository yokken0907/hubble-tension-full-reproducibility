# Exhaustive interaction decomposition contract

Status: **frozen before the decomposition outputs below were generated**  
Freeze date: 2026-07-29 (UTC)  
Diagnostic version: 0.1.0-posthoc.2

## Trigger already observed

The first bounded post-hoc diagnostic established that:

- `P0 @ A` is numerically zero at the public covariance cutoff;
- `||P0 @ y||` is approximately 0.18875;
- inspection of the required all-equation projection table showed that the
  nonzero entries occur in the complete R22 HST-Cepheid host-by-anchor block.

These observations are disclosed because they motivated this localization
step.

## Fixed exhaustive decomposition

1. Select rows only by the public metadata fields
   `method=ceph_hst` and `source=R22`.
2. Require a complete rectangular table with 37 unique hosts and the three
   encoded anchors, with exactly one row per host-anchor cell. Stop if this
   structural gate fails.
3. Compute the unweighted two-way additive interaction for every cell:
   `y_ha - host_mean_h - anchor_mean_a + grand_mean`.
4. Compare the 111 interaction values, in original equation order, with the
   corresponding values of `P0 @ y`. The decomposition passes only if the
   maximum absolute difference is below `1e-10`.
5. Output all 111 cells, all 37 host summaries, and all three anchor summaries.
   No host or anchor is excluded based on its result.
6. Report RMS, L2 norm, and maximum absolute interaction. A ranked display may
   name the largest cells only if the complete tables are delivered alongside
   it.

## Interpretation boundary

The interaction is a mismatch between the public data vector and the exact
additive support implied by the public singular covariance. It is not, by
itself, evidence that a named distance measurement is erroneous or that a
specific astrophysical systematic is present.

