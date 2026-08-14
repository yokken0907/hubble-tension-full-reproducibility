# H0DN SN Ia cross-series public-input dependency audit

Version 0.1.0 (Phase 1F)

## Outcome

The audit completed with the formal status
`AUDIT_COMPLETE_PUBLIC_INPUT_DEPENDENCY_CLASSIFIED`.

Within the frozen set of 69 public-input candidates in 30 same-CID groups,
all 48 within-group file pairs were evaluated. No pair contained a byte-exact
published `OBS:` row; four pairs contained exactly one mutual-unique,
rounding-compatible four-value photometric payload; and no pair contained two
or more such matches. These four records are evidence of published numerical
payload compatibility/agreement only, not proof of payload reuse or of a shared
physical exposure.

| Audit component | Result |
|---|---:|
| Candidate rows / same-CID groups / within-group pairs | 69 / 30 / 48 |
| Parsed published observations | 6,744 |
| Byte-exact positive pairs | 0 / 48 |
| Single-payload positive pairs | 4 / 48 |
| Repeated-payload positive pairs | 0 / 48 |
| Row-by-used-filter records mapped to public KCOR text and transmission assets | 434 / 434 |
| Active public configuration series passing all frozen anchors | 7 / 7 |
| Executed-run-to-final-catalog lineage established | No |

The release therefore supports a bounded public-input and configuration
dependency classification. It does not establish that these candidate light
curves generated particular final `m_b_corr` rows, that any two rows share a
physical exposure, or that the rows are statistically independent.

The frozen machine-readable layer token `PUBLISHED_PHOTOMETRIC_PAYLOAD_REUSE`
is retained for reproducibility as legacy nomenclature. Its preferred
reader-facing interpretation is **published photometric payload compatibility**;
the token does not establish reuse.

## Post-hoc diagnostic

After the main result was fixed, a separately frozen descriptive cross-CID
collision screen evaluated 1,523 file pairs and 14,670,999 observation-pair
opportunities in the directory-pair strata represented by the main analysis.
It found 24 positive file pairs, each with one mutual-unique compatible
payload. The groups are nonexchangeable, so this is not a p-value or a formal
null model. It reinforces the need not to promote an isolated payload match to
physical-exposure identity.

## Scientific boundary

This package does not re-fit light curves, reconstruct an executed FITRES or
bias-correction run, rank surveys or objects, modify a covariance matrix,
delete or combine rows, calculate a corrected H0, or address tension
significance or new physics. Corrected Phase 1D and Phase 1E remain unchanged;
Phase 1F is supplementary and non-retroactive.

## Package map

- `AUDIT_CONTRACT.md` — frozen main rules and non-claims.
- `POSTHOC_PAYLOAD_COLLISION_NEGATIVE_CONTROL_CONTRACT.md` — diagnostic rules,
  explicitly frozen after the main result.
- `REPORT.md` and `REPORT_JA.md` — scientific reports.
- `provenance/` — source, tree, contract, and upstream dependency locks.
- `results/` — machine-readable classifications and verification records.
- `scripts/` — audit, second implementation, tests, clean reproduction, and
  delivery validation.
- `MANIFEST.tsv` and `SHA256SUMS.txt` — delivered-tree integrity records.

The raw Pantheon+SH0ES photometry, calibration assets, pipeline configuration,
distance catalog, and covariance products are not redistributed.

## Verify an extracted package

Prepare the Pantheon+SH0ES DataRelease repository at commit
`c447f0fea703fcd0fff57de5000947b5ca81286b`, then run:

```bash
PPLUS_REPO=/absolute/path/to/DataRelease
python3 scripts/verify_results.py --pantheonplus "$PPLUS_REPO"
python3 scripts/finalize_package.py --check
```

See `REPRODUCIBILITY.md` for a full clean rerun. Python 3.11 or newer is
required; the scientific code uses only the standard library and Git.
