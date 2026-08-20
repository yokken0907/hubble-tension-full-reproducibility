# Phase 1C report: aggregate contrast-covariance calibration

## Result

All required provenance, lineage, input, and numerical gates passed. The
formal status is
`AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC`.
After the bounded correction and closure audit, the disposition is
`ACCEPT_COMPLETE_WITH_SCOPE`.

The predeclared sensitivity classification is:

`LOW_FLAG_PERSISTS_THROUGH_STATONLY`

For the 39 contrast degrees of freedom:

| Ordered baseline | chi-square | lower-tail probability | q / df |
| --- | ---: | ---: | ---: |
| Phase 1A full | 11.209315063602716 | 3.6795246e-06 | 0.2874183 |
| STAT+SYS without rowwise velocity | 14.734235950587198 | 1.4711329e-04 | 0.3778009 |
| STATONLY | 16.233447508593247 | 4.8568326e-04 | 0.4162422 |

Every probability is below the frozen `0.001` strong-low-dispersion
threshold. These are reference probabilities under literal fixed-known
Gaussian covariance baselines, not multiplicity-adjusted discovery claims.
The descriptive strong-low label uses `p < 0.001`; the ordered sensitivity
flag uses the distinct threshold `p < 0.01`. All three rows meet both.

The Phase 1A conditional Beta probability `9.3683622e-05` and the Phase 1C
marginal \(\chi^2_{39}\) lower-tail probability `3.6795246e-06` are not two
implementations of one probability. They answer different reference
questions, so their numerical difference is not an inconsistency.

## What changed across the covariance baselines

Removing the rowwise velocity term raises the quadratic form from 11.21 to
14.73. In the projected 39-dimensional space, the full Phase 1A covariance
has generalized eigenvalues 1.044 to 1.550 relative to the STAT+SYS-only
baseline, with geometric mean 1.326.

Replacing STAT+SYS by STATONLY raises the quadratic form further to 16.23.
The STAT+SYS covariance has generalized eigenvalues 1.0003 to 1.9015 relative
to STATONLY, with geometric mean 1.0969.

Thus both omitted components influence the numerical value, but neither
transition removes the aggregate lower-tail flag.

The diagonal-only structural checks give chi-squares 9.1554 (STAT+SYS) and
9.9372 (STATONLY). For this observed vector, restoring the published
off-diagonal structure raises rather than removes the quadratic form. These
two diagonal checks are descriptive and do not enter the classification.

The cosmographic model term is exactly common within every multi-row group in
the frozen table: its maximum contrast is zero. The 39-mode signal is
therefore carried entirely by the within-identifier magnitude differences.

## Frozen post-hoc precision and asymmetry diagnostics

Bounded review requested two supplemental checks after the main result was
known. The new calculations were frozen in an internal result-blind contract,
SHA-256
`050272af008385d0f4d5e247d1a81a432411115f972bc6a52562a580d8f3d5b4`,
before their values were loaded or calculated. This is not an external
preregistration and does not amend the main analysis.

Using the same Phase 1B mapping, groups, 39-row Helmert basis, and covariance
baselines, replacing only printed H0DN `m_b` by official high-precision
`m_b_corr` gives:

| Baseline | printed q | high-precision q | delta q |
| --- | ---: | ---: | ---: |
| Phase 1A full | 11.209315063602716 | 11.181959816277521 | -0.027355247325195 |
| STAT+SYS without rowwise velocity | 14.734235950587198 | 14.694714732492480 | -0.039521218094718 |
| STATONLY | 16.233447508593247 | 16.192911494208520 | -0.040536014384728 |

The corresponding high-precision lower-tail probabilities are
`3.5535125e-06`, `1.4219325e-04`, and `4.7133432e-04`. The maximum absolute
and Euclidean-norm contrast changes are `9.899494936649322e-05` and
`2.879814808859486e-04`.

The raw selected 277-by-277 STAT+SYS and STATONLY submatrices both have zero
asymmetric off-diagonal pairs. Each full 1701-by-1701 source matrix has 778
directed asymmetric elements and maximum transpose difference
`3.0000000000038676e-08`; all of those elements lie outside the selected
mapping. The frozen upper-triangle, lower-triangle, and symmetric-average
sensitivity branch was therefore correctly not triggered for the actual
selected data. Its algebra is covered by an asymmetric matrix fixture.

## Interpretation

The bounded conclusion is negative but useful:

- after the H0DN rowwise 240 km/s variance term is removed, the
  low-dispersion flag remains;
- after the published systematic covariance component is removed, the
  low-dispersion flag remains;
- it remains present even against the official STATONLY covariance.

This narrows the next scientific question toward measurement construction and
dependency: whether cross-survey rows sharing a CID are statistically as
independent as the contrast model treats them, whether their uncertainty
fields have a shared derivation, or whether selection and compression induce
additional concordance.

The audit does not distinguish among those possibilities. In particular,
`q/df < 1` is not by itself evidence that every quoted uncertainty should be
multiplied by `sqrt(q/df)`. The reported scale intervals are diagnostics of a
hypothetical scalar family, not a recommended correction.

## Verification

- 13/13 source-lock files passed across two fixed commits, including four
  H0DN implementation files.
- Canonical Phase 1A and Phase 1B ZIPs passed filename, SHA-256, sidecar, and
  CRC checks.
- The Phase 1B compact mapping passed for 277/277 rows with unique targets.
- All 30 multi-row groups are cross-survey; they contain 69 rows and 39
  contrast degrees of freedom.
- The mapped official STAT+SYS submatrix matches H0DN in 76,729/76,729
  float64 elements.
- All five projected covariance matrices are positive definite.
- The known Phase 1A value reproduced within `3.6e-14`.
- Cholesky and eigendecomposition calculations agree within `1.5e-14`.
- A separately constructed null-space basis agrees within `1.5e-13`.
- All 32 orthogonal-coordinate trials passed.
- The independent verifier passed all five baselines and the classification.
- All 33 unit and adversarial tests passed.
- A clean-copy run reproduced all 22 main and post-hoc artifacts byte for
  byte.
- Running `verify_results.py` is read-only with respect to every manifested
  target.

## Schema chronology

Contract 01 stopped before new scientific calculations because the official
covariance files are not exactly symmetric as printed. Their maximum
transpose difference is `3.0000000000038676e-08`. Contract 02 preserved the
failed contract, disclosed the observed schema diagnostic, retained the
already specified `(C+C.T)/2` transformation, and froze a `5e-8` admissibility
bound before any Phase 1C quadratic form was calculated.

The correction preserves the Contract 02 source lock as an exact frozen
2,255-byte prefix and preserves the original upstream-dependency JSON as a
byte-identical snapshot. Additions are disclosed in the amendment ledger and
the separate hashed post-hoc contract.

## Non-claims

This result does not:

- identify an anomalous object, survey, or survey pair;
- support a global reinterpretation of the quoted statistical uncertainties;
- authorize a covariance rescale or row collapse;
- produce a corrected \(a_B\), \(M_B\), or \(H_0\);
- change the numerical Hubble-tension significance;
- assign an instrumental, astrophysical, or software cause.
