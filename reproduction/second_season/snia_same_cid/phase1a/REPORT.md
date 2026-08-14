# H0DN SN Ia fixed-covariance residual-deficit localization audit

Formal status:

`AUDIT_COMPLETE_LOW_CHI2_LOCALIZED_TO_DUPLICATE_NAME_CONTRASTS`

Boundary marker:

`FROZEN_MODEL_ONLY_NO_COVARIANCE_CORRECTION_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

## Integrated conclusion

The frozen public H0 Distance Network Pantheon+ Hubble-flow residual
chi-square was partitioned into exact duplicate-name contrast modes and
between-name modes:

| Component | Chi-square | Degrees of freedom | Fixed-model lower-tail probability |
| --- | ---: | ---: | ---: |
| Total | 206.760636437324 | 276 | 0.000667628456 |
| Duplicate-name contrasts | 11.209315063603 | 39 | 0.000003679525 |
| Between-name modes | 195.551321373699 | 237 | 0.022934426681 |

The duplicate-name component contributes 5.4214% of the observed total
chi-square while accounting for 14.1304% of the residual dimensions. The
project-internal conditional Beta localization test, hash-frozen before its
output was examined, has lower-tail probability `9.368362232281232e-05` and
two-sided probability
`1.8736724464562464e-04`. Under the pre-specified 1% two-sided rule, the low
chi-square is classified as disproportionately localized to duplicate-name
contrast modes.

## Prospective boundary

Phase 0 had already exposed the total chi-square, 277 rows, 238 exact-name
groups, 30 multi-row exact-name groups containing 69 rows, and 39
duplicate-name contrast degrees of freedom. The global low-tail probability
is therefore not a new result of the Phase 1A conditional test.

Before any within/between partition value was evaluated, the audit froze:

- exact-string grouping without normalization or external resolution;
- the 39- and 237-degree nested GLS partition;
- one conditional Beta localization test;
- a 1% two-sided decision threshold;
- numerical tolerances and stop conditions;
- prohibitions on object ranking, residual scans, covariance modification,
  and corrected-H0 inference.

This was a project-internal pre-result hash freeze, not an external registry
or third-party timestamp. After the results were observed, `AMEND-001`
clarified the reader-facing meaning of 39 without changing any numerical
result, threshold, classification, or scientific boundary. The frozen
contract text and its recorded hash are preserved.

## Construction

The public table contains 208 singleton names, 21 names represented twice, and
9 names represented three times. Thus, 30 multi-row exact-name groups contain
69 rows in total. This produces 238 exact-name groups, 39 excess rows beyond
the first row of each group, and 39 within-name contrast degrees of freedom.

With \(X_0=\mathbf 1\) and the 238-column exact-name incidence matrix \(X_1=Z\),
the fixed covariance was Cholesky-whitened. Nested projections give

\[
\chi^2_{276}
=\chi^2_{{\rm duplicate},39}
+\chi^2_{{\rm between},237}.
\]

Under the literal fixed-known Gaussian covariance model,

\[
R=\chi^2_{\rm duplicate}/\chi^2_{\rm total}
\sim {\rm Beta}(39/2,237/2).
\]

The observed ratio is `0.054213970593`; its null mean is
`39/276 = 0.141304347826`.

## Verification

- 69/69 frozen source paths passed commit, size, Git-object, and SHA-256
  verification.
- The 277-by-277 alpha covariance is full rank and passed Cholesky
  factorization.
- The QR-projection implementation and a separate direct-GLS normal-system
  implementation agree to at worst `2.19e-11` in the three chi-square
  quantities.
- Partition closure is `2.18e-11`.
- All 32 fixed-seed simultaneous row/column permutations passed; the maximum
  difference was `2.33e-10`.
- All three 20,000-draw analytic-null implementation checks passed.
- All 13 unit tests passed.

The Monte Carlo calculation checks code implementation only. It does not
validate the physical completeness or estimation uncertainty of the public
covariance.

## Scientific boundary

The result localizes a fixed-model residual deficit. It does not show that:

- duplicate rows are wrong or independent;
- the public covariance is overestimated;
- any supernova, survey, calibration, or velocity correction is causal;
- rows should be removed, collapsed, or reweighted;
- \(a_B\), \(M_B\), or \(H_0\) should be corrected;
- the significance of the Hubble tension has changed.

Exact public-name equality is not itself a complete physical-identity or
survey-provenance statement. The full covariance already encodes
cross-row correlations.

## Bounded next step

A separately contracted source-provenance audit may map the 30 multi-row
exact-name groups (69 rows) to their public survey, light-curve-fit,
calibration, and covariance-generation records. Phase 1A does not perform that
mapping, identify individual objects, or modify the covariance.

This is independent work by Keiji Yoshimura. It is not an official H0DN or
Pantheon+ collaboration product, endorsement, or peer review.
