# H0DN SN Ia contrast-covariance calibration audit

Version 0.1.0

This repository reproduces a bounded Phase 1C audit of the 39 cross-survey,
same-identifier SN Ia contrast modes isolated in earlier H0DN audits. It asks
whether their previously observed low dispersion survives two predeclared
covariance simplifications:

1. removing H0DN's rowwise 240 km/s velocity-dispersion term; and
2. replacing the public Pantheon+SH0ES STAT+SYS covariance by STATONLY.

The result is:

`LOW_FLAG_PERSISTS_THROUGH_STATONLY`

All three ordered baselines remain below the frozen one-sided lower-tail
threshold:

| Baseline | chi-square / 39 df | lower-tail reference probability |
| --- | ---: | ---: |
| Phase 1A full | 11.2093150636 | 3.6795e-06 |
| STAT+SYS, no rowwise velocity term | 14.7342359506 | 1.4711e-04 |
| STATONLY | 16.2334475086 | 4.8568e-04 |

The strong-low descriptive label uses `p < 0.001`, while the ordered
sensitivity flag uses `p < 0.01`. These thresholds are distinct; all three
main baselines meet both.

Two probabilities attached to the known Phase 1A value answer different
questions. Phase 1A reported the conditional Beta probability
`9.3683622e-05`. Phase 1C reports the marginal
\(\chi^2_{39}\) lower-tail probability `3.6795246e-06`. Their difference is
not an inconsistency.

Removing the rowwise velocity variance leaves the low-dispersion flag in
place. Removing the public systematic covariance component also leaves the
flag in place. These are observations under the specified baselines, not
causal explanations. They do **not** license a covariance rescale or identify
a physical or pipeline cause.

## Frozen post-hoc diagnostics

Bounded review requested two supplemental checks. Their internal result-blind
contract was hashed before the new values were loaded or calculated:
`POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.md`, SHA-256
`050272af008385d0f4d5e247d1a81a432411115f972bc6a52562a580d8f3d5b4`.

Replacing only the printed H0DN `m_b` values by the mapped official
high-precision `m_b_corr` values gives:

| Baseline | printed q | high-precision q | high − printed |
| --- | ---: | ---: | ---: |
| Phase 1A full | 11.209315063602716 | 11.181959816277521 | -0.027355247325195 |
| STAT+SYS, no rowwise velocity term | 14.734235950587198 | 14.694714732492480 | -0.039521218094718 |
| STATONLY | 16.233447508593247 | 16.192911494208520 | -0.040536014384728 |

The maximum and Euclidean-norm changes in the fixed 39-component contrast
vector are `9.899494936649322e-05` and `2.879814808859486e-04`.
Both raw mapped 277-by-277 submatrices are exactly symmetric. The 778 directed
asymmetric elements in each full 1701-by-1701 public covariance therefore lie
outside the selected mapping. These post-hoc results do not replace the main
vector, status, probabilities, or classification.

## Audit boundary

Formal status:
`AUDIT_COMPLETE_CONTRAST_COVARIANCE_CALIBRATION_DIAGNOSTIC`

Correction closure:
`ACCEPT_COMPLETE_WITH_SCOPE`

Boundary marker:
`CALIBRATION_DIAGNOSTIC_ONLY_NO_COVARIANCE_RESCALE_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

The audit performs no object or survey ranking, no row removal, no covariance
fit, no corrected intercept or Hubble constant, and no Hubble-tension
recalculation.

## Inputs

Upstream data are not redistributed. The run requires:

- H0DN commit `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`;
- Pantheon+SH0ES DataRelease commit
  `c447f0fea703fcd0fff57de5000947b5ca81286b`.

All 13 consumed implementation and data files are locked by commit, Git blob,
byte count, and
SHA-256 in `provenance/SOURCE_LOCK.tsv`.

The 277-row source-to-source mapping is the compact frozen dependency
`provenance/PHASE1B_ROW_MAP.tsv`. It is verified against both source tables
before use.

The canonical Phase 1A and Phase 1B ZIPs are external, non-redistributed
inputs. Their names, SHA-256 values, sidecars, and CRCs are verified before
the main audit. The Phase 1A archive SHA-256 is
`38bb6e55c66ec3442e465cfe4367c1b75e5ecb369933df6de71b75c6182e8333`.

## Quick reproduction

With Python 3.12, NumPy 2.3.5, SciPy 1.17.0, and Git:

```bash
python -m pip install -r requirements-lock.txt

python scripts/source_tools.py --acquire-root ../frozen-sources

python scripts/run_audit.py \
  --h0dn ../frozen-sources/H0DN \
  --pantheonplus ../frozen-sources/PantheonPlusSH0ES_DataRelease \
  --phase1a-archive ../h0dn-snia-residual-deficit-localization-audit_v0.1.0.zip \
  --phase1b-archive ../h0dn-snia-multirow-provenance-audit_v0.1.0.zip

python scripts/run_posthoc_precision_asymmetry.py \
  --h0dn ../frozen-sources/H0DN \
  --pantheonplus ../frozen-sources/PantheonPlusSH0ES_DataRelease

python scripts/independent_verify.py \
  --h0dn ../frozen-sources/H0DN \
  --pantheonplus ../frozen-sources/PantheonPlusSH0ES_DataRelease

python -m unittest discover -s tests -v
```

See `REPRODUCIBILITY.md` for clean-copy and packaging checks.

## Contract chronology

Contract 01 stopped at a pre-execution schema gate before any new quadratic
form was computed: both official covariance files have a maximum absolute
transpose difference of about `3e-8`, larger than the initial `1e-12` bound.
The retired contract and freeze are preserved. Contract 02 disclosed that
HOLD, retained the predeclared averaging transformation
`(C + C.T) / 2`, set the schema bound to `5e-8`, and froze again before
component outcomes were evaluated.

The bounded correction does not rewrite Contract 01, Contract 02, or their
freeze records. It preserves the original `SOURCE_LOCK.tsv` bytes as a frozen
prefix, preserves the original upstream-dependency JSON as
`UPSTREAM_AUDIT_DEPENDENCIES_CONTRACT02_FROZEN.json`, records all additions in
`CONTRACT_AMENDMENTS.tsv`, and keeps the supplemental calculation under its
own hashed post-hoc contract.

This history is recorded in:

- `provenance/PREEXECUTION_SCHEMA_HOLD.json`;
- `provenance/RETIRED_CONTRACT_01.md`;
- `provenance/RETIRED_CONTRACT_FREEZE_01.json`;
- `provenance/RETIRED_DECISION_CONFIG_01.json`.

## Repository guide

- `AUDIT_CONTRACT.md` — active frozen question, rules, gates, and non-claims
- `POSTHOC_PRECISION_AND_ASYMMETRY_DIAGNOSTIC_CONTRACT.md` — frozen
  supplemental precision/asymmetry rules
- `provenance/` — source locks, Phase 1B mapping, freeze, and chronology
- `scripts/run_audit.py` — primary Cholesky/Helmert calculation
- `scripts/run_posthoc_precision_asymmetry.py` — separate post-hoc runner
- `scripts/independent_verify.py` — separate parser, null-space basis, and
  eigendecomposition
- `tests/` — 33 unit and adversarial tests
- `results/` — machine-readable outputs and verification records
- `REPORT.md`, `REPORT_JA.md` — bounded interpretation in English and Japanese

## License and attribution

The audit code and documentation are released under the MIT License.
Upstream data retain their own terms and are not included. Cite this software
together with the H0DN and Pantheon+ source publications and the two frozen
commits.
