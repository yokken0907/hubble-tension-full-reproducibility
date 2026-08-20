# H0DN SN Ia residual-deficit localization audit

Formal status:

`AUDIT_COMPLETE_LOW_CHI2_LOCALIZED_TO_DUPLICATE_NAME_CONTRASTS`

Boundary:

`FROZEN_MODEL_ONLY_NO_COVARIANCE_CORRECTION_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

## Result

This independent audit partitions the already known low residual chi-square of
the frozen public H0 Distance Network (H0DN) Pantheon+ Hubble-flow block into
two exact, nested generalized-least-squares subspaces defined only by equality
of the public name strings.

The 277 rows form 238 exact-name groups. Of those, 30 are multi-row groups
containing 69 rows in total; equivalently, the partition has 39
duplicate-name contrast degrees of freedom (and 39 excess rows beyond the
first row in each exact-name group).

| Component | Chi-square | Degrees of freedom | Fixed-model lower-tail probability |
| --- | ---: | ---: | ---: |
| Total residual | 206.760636437324 | 276 | 0.000667628456 |
| Duplicate-name contrasts | 11.209315063603 | 39 | 0.000003679525 |
| Between-name modes | 195.551321373699 | 237 | 0.022934426681 |

The duplicate-name component supplies 5.4214% of the observed total
chi-square, compared with 14.1304% of the residual dimensions. The
project-internal conditional Beta localization test, hash-frozen before its
output was examined, gives:

- lower-tail probability: `9.368362232281232e-05`;
- two-sided probability: `1.8736724464562464e-04`.

The pre-specified classification is therefore localization to duplicate-name
contrast modes.

This does not establish that duplicate rows are erroneous, that the covariance
is overestimated, or that any named supernova is anomalous. It identifies
where the fixed-model residual deficit is concentrated.

## Scope and chronology

Phase 0 had already observed the total chi-square, 277 rows, 238 exact-name
groups, 30 multi-row exact-name groups containing 69 rows, and 39
duplicate-name contrast degrees of freedom. Those facts and the global
chi-square probability are not new results of the Phase 1A conditional test.

Before the within/between partition was evaluated, `AUDIT_CONTRACT.md` fixed:

- the exact-name incidence design;
- the 39/237-degree partition;
- one conditional Beta localization test;
- its 1% two-sided threshold;
- all numerical tolerances and stop conditions;
- the prohibition on object ranking, residual scans, covariance adjustment,
  and corrected-H0 inference.

The contract and decision configuration are hash-frozen in
`provenance/CONTRACT_FREEZE.json`.
This is a project-internal pre-result freeze, not an external registry or
third-party timestamp. The post-result terminology clarification is disclosed
as `AMEND-001` in `provenance/CONTRACT_AMENDMENTS.tsv`; the frozen contract,
decision configuration, and freeze record remain unchanged.

## Reproduction

Required:

- Python 3.12;
- NumPy and SciPy versions listed in `requirements-lock.txt`;
- Git;
- the public H0DN repository at commit
  `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`.

From the project root:

```bash
python scripts/source_tools.py \
  --destination ../H0DN_FROZEN \
  --manifest provenance/SOURCE_LOCK.tsv

python -m unittest discover -s tests -v

python scripts/run_audit.py --upstream ../H0DN_FROZEN

python scripts/run_clean_reproduction.py \
  --workdir ../H0DN_SNIA_PHASE1A_CLEAN \
  --upstream ../H0DN_FROZEN

python scripts/verify_results.py --record-results
python scripts/finalize_package.py --write-manifests
python scripts/verify_results.py
```

The upstream H0DN bytes are not included in this package. All 69 tracked paths
are verified by commit, size, Git object identifier, and SHA-256.

The default verifier is read-only: it prints a live result and changes no
delivered file. `--record-results` is used only during package closure and
updates exactly `results/unit_tests.log` and
`results/final_verification_summary.json`; manifests must then be regenerated.
`--output-dir /path/outside/the/project` writes the live log and summary
outside the package.

## Reading order

1. `AUDIT_CONTRACT.md`
2. `REPORT_JA.md` or `REPORT.md`
3. `results/audit_summary.json`
4. `REPRODUCIBILITY.md`
5. `AI_ASSISTANCE_DISCLOSURE.md`

This is independent work by Keiji Yoshimura. It is not an official H0DN or
Pantheon+ collaboration product or peer review.
