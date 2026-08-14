# H0DN SN Ia same-CID measurement-lineage audit

Version 0.1.0 · Phase 1D · software provenance audit

This repository asks how far the frozen public Pantheon+SH0ES release can
limit public photometry inputs compatible with a prospectively frozen
CID-plus-IDSURVEY crosswalk for the 69 H0 Distance Network rows belonging to
30 repeated-CID groups, and which shared-processing dependencies are visible
at configuration level.

The completed formal result is:

`PUBLIC_RELEASE_PARTIAL_MEASUREMENT_LINEAGE`

This is a release-sufficiency and provenance classification. It is not a
corrected covariance, a new Hubble-constant estimate, or an explanation of
the Hubble tension.

**Evidence boundary:** Phase 1D does not prove the direct executed-run ancestry
of any final `m_b_corr` row. For 38 rows it establishes only that exactly one
public photometry input candidate satisfied the frozen crosswalk and public
input-selection rules. Accordingly,
`direct_final_measurement_ancestry = NOT_ESTABLISHED`.

## Result at a glance

| Gate or finding | Result |
| --- | ---: |
| Frozen population | 69 rows in 30 same-CID groups |
| Active public photometry files scanned | 847 in 7 source directories |
| Parse failures | 0 |
| Rows with one frozen-crosswalk-compatible input candidate | 38 |
| Rows without a compatible candidate under that crosswalk | 31 |
| Groups whose rows each had distinct unique compatible candidates | 3 of 30 |
| Pairs with compatible candidates for both rows | 10 of 48 |
| Such pairs sharing any byte-identical `OBS:` line | 0 |
| Frozen public configuration anchors verified | 12 of 12 |
| Predeclared referenced assets tracked in the release | 0 of 3 |
| Main second-implementation checks | 15 of 15 PASS |
| Post-hoc second-implementation checks | 9 of 9 PASS |
| Isolated byte-for-byte reproduction | 19 of 19 files PASS |
| Unit/regression tests | See `results/unit_tests.log` |

The three legacy-classified groups are `2009cz`, `2005iq`, and `2005hc`.
Their reader-facing interpretation is that every row had a distinct unique
frozen-crosswalk-compatible input candidate. Distinct files and non-overlapping
text lines do not establish statistical independence, independent calibration,
or independent likelihood terms.

## Crucial interpretation of the 31 unresolved rows

The legacy token `NO_ACTIVE_PUBLIC_PHOTOMETRY_FILE` means that no candidate
matched both the exact CID and the prospectively internally frozen
IDSURVEY-to-directory/header vocabulary. Its explicit interpretation alias is
`NO_FROZEN_CROSSWALK_COMPATIBLE_INPUT_CANDIDATE`. It does not mean that no
public file with that CID exists.

A separately frozen post-hoc diagnostic searched by exact CID alone. All 31
rows had multiple public same-CID candidates (73 row–candidate records in
total). The pattern localizes the remaining problem to a non-unique final
IDSURVEY-to-raw-series crosswalk. It also shows recurring candidates in
`LOSS` for code 51, `KAIT_DS15` for code 57, and CFA4p1-header files for code
65. Because this pattern was observed after the main result, the diagnostic
does not promote candidates, infer an alternate mapping, or change any main
ledger.

The eight-code evidence register is
`provenance/SURVEY_CROSSWALK_EVIDENCE.tsv`. Codes 51, 57, and 65 remain
`UNRESOLVED_BRIDGE` in Phase 1D; post-hoc candidates are never promoted.

The 12 `PPLUS.yml` anchors are
`CONFIGURATION_LEVEL_SHARED_DEPENDENCY_EVIDENCE_ONLY` and do not establish an
executed production path to the final catalog
(`NO_EXECUTED_RUN_TO_FINAL_CATALOG_LINEAGE_PROOF`).

## Start here

- [English report](REPORT.md)
- [Japanese report](REPORT_JA.md)
- [Frozen main contract](AUDIT_CONTRACT.md)
- [Frozen post-hoc diagnostic contract](POSTHOC_CID_ONLY_CROSSWALK_DIAGNOSTIC_CONTRACT.md)
- [Reproduction instructions](REPRODUCIBILITY.md)
- [Validation design](PACKAGE_VALIDATION.md)
- [Result-file guide](results/README.md)
- [Survey-crosswalk evidence register](provenance/SURVEY_CROSSWALK_EVIDENCE.tsv)

## Minimal reproduction

Python 3.12, Git, and the Python standard library are sufficient.

```bash
python scripts/source_tools.py acquire --destination frozen_sources
python scripts/run_audit.py \
  --h0dn frozen_sources/H0DN.git \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
python scripts/independent_verify.py \
  --h0dn frozen_sources/H0DN.git \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
python scripts/run_posthoc_cid_only_crosswalk.py \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
python scripts/verify_posthoc_cid_only_crosswalk.py \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
python -m unittest discover -s tests -v
```

See `REPRODUCIBILITY.md` for clean reproduction and package verification.
No upstream repository or raw photometry bytes are redistributed here.

## Frozen primary sources

- [H0 Distance Network repository](https://github.com/StefCas789/H0DN),
  commit `cc0a4b9f36e65470d514f254a3c5cffa463fbd94`
- [Pantheon+SH0ES DataRelease](https://github.com/PantheonPlusSH0ES/DataRelease),
  commit `c447f0fea703fcd0fff57de5000947b5ca81286b`
- [Pantheon+ light-curve and data-release paper](https://arxiv.org/abs/2112.03863)
- [Pantheon+ cosmology paper](https://arxiv.org/abs/2202.04077)

## License and attribution

The audit code and original documentation are MIT-licensed. Upstream data are
not included and remain governed by their source repositories and
publications. See `THIRD_PARTY_NOTICES.md` and `CITATION.cff`.
