# Phase 1F report: cross-series public-input dependency audit

## Executive result

Phase 1F completed its frozen 69-row, 30-group, 48-pair audit. The public
release supports classification of candidate photometry inputs, their used
filters, public calibration definitions, and active pipeline configuration.
It does not provide the run manifests or hash chain needed to prove that a
particular public candidate generated a particular final catalog row.

Across the 48 same-CID file pairs, the primary comparison found zero pairs
with a byte-exact observation row, four pairs with exactly one mutual-unique
rounding-compatible photometric payload, and zero pairs with repeated
compatible payloads. No accepted match used the same filter token, public
transmission blob, or KCOR filter definition. Only one had an absolute MJD
difference at or below 0.11 day; that timing screen was exposed before the
complete scan and is descriptive only.

The formal scientific classification is:

`PUBLIC_INPUT_DEPENDENCIES_CLASSIFIED_REPEATED_PAYLOAD_PAIRS_0_OF_48_SINGLE_PAYLOAD_PAIRS_4_OF_48_FILTER_RECORDS_MAPPED_434_OF_434_CONFIG_SERIES_PASS_7_OF_7`

## Question and scope

The audit asked what the fixed public Pantheon+SH0ES release can establish
about shared or distinct photometry records, filter/calibration inputs,
light-curve configuration inputs, and downstream aggregation configuration
for the same-CID rows fixed by the preceding phases.

The population came from two accepted corrected upstream deliverables:

- 38 candidates from corrected Phase 1D;
- 31 candidates from corrected Phase 1E;
- 69 candidates total, forming 30 repeated-CID groups and 48 unordered
  within-group pairs.

These candidates are frozen public-input candidates, not proven final
measurement ancestors. Phase 1D and Phase 1E classifications were copied and
hash-locked, then left unchanged.

## Sources and chronology

The public source was fixed to Pantheon+SH0ES DataRelease commit
`c447f0fea703fcd0fff57de5000947b5ca81286b`. Forty-five exact files and 20 Git
trees were locked. The principal photometry, calibration, and SALT2 tree OIDs
were respectively `3facbb99276c7589349d8eceaac218ccd2ad0726`,
`33ffec9491944f172e9a1358de56a281296068f0`, and
`31e12f7dbbb0c4ffc86bf0020bedeca3edbb2613`.

The main contract was internally hash-frozen before the complete 69-file and
48-pair scan. This was not a public preregistration and not a fully blind
analysis: limited examples from SN 2009cz, SN 2007qe, and SN 2009D, including
similar SN 2007qe payload values, were already visible. The post-hoc
cross-CID diagnostic was designed and separately frozen only after the main
result had been observed. Its chronology is therefore explicit and it cannot
retroactively strengthen the prospective status of the main audit.

## Methods

### Candidate and photometry validation

Each candidate path had to be a tracked blob at the fixed commit, active under
its directory `.LIST` and `.IGNORE` files, and consistent with the expected
CID. The parser required one `SNID`, `SURVEY`, `VARLIST`, and `NOBS`, with
`MJD`, `FLT`, `FLUXCAL`, `FLUXCALERR`, `MAG`, and `MAGERR` present. The audit
parsed 6,744 published observation rows across 69 distinct candidate blobs.

No residual, fitted parameter, covariance value, redshift, H0 value, or final
`m_b_corr` value entered candidate selection or pair matching.

### Pair comparison

The strongest test required exact raw bytes after the literal `OBS:` prefix.
The primary tolerant comparison converted each printed decimal to its closed
rounding interval and required overlap in all four quantities `FLUXCAL`,
`FLUXCALERR`, `MAG`, and `MAGERR`. MJD and filter token did not define an edge.
Only graph edges unique at both endpoints were accepted. Pair classes were
zero, exactly one, or at least two accepted matches.

This rule detects compatibility/agreement in published numerical payloads. It
does not establish payload reuse, identify a raw image or physical exposure, or
establish causal covariance or statistical dependence. The frozen
machine-readable layer token `PUBLISHED_PHOTOMETRIC_PAYLOAD_REUSE` is retained
for reproducibility as legacy nomenclature and should be read as published
photometric payload compatibility only.

### Filter, calibration, and configuration mapping

For every raw filter token actually used by a candidate, the audit required
one case-sensitive `FILTER:` definition in the frozen KCOR text input and a
tracked public transmission asset at the implied path. The 434 row-by-filter
records covered all 6,744 observations, used five KCOR input files, and mapped
to 50 distinct public transmission blobs.

Seven active source-series configurations were checked in `PPLUS.yml`,
including the one series with zero Phase 1F candidate rows. All seven passed
the frozen DATAPREP, LCFIT, KCOR alias, common-input, and `REALDATABS20NOM`
aggregation anchors. This is configuration-level evidence. It is not a job
log, run manifest, FITRES provenance chain, or proof of execution identity.

## Primary pair results

| CID | H0DN rows | Filters | Absolute MJD difference (day) | Same public transmission blob | Interpretation |
|---|---:|---|---:|---|---|
| 2004as | 109 / 110 | C / d | 2.86091 | No | One compatible published payload |
| 2005hc | 172 / 173 | f / J | 10.61800 | No | One compatible published payload |
| 2007co | 50 / 52 | F / i | 9.98319 | No | One compatible published payload |
| 2007qe | 5 / 6 | F / g | 0.10000 | No | One compatible published payload; timing descriptor only |

The other 44 pairs had no mutual-unique rounding-compatible payload match.
There were no byte-exact positive pairs and no repeated-payload positive pairs.
None of the four accepted matches had overlapping printed MJD intervals or an
equal filter token. No physical-exposure identity was established.

## Public asset availability

Sixteen referenced configuration assets were classified. Eight had tracked
public basename candidates without execution identity: `ALL.fitopts`, six
header-override files, and `SALT2.INFO` (with ten public model variants). Eight
were not tracked by basename in the fixed release: the seven referenced base
NML files and the downstream `SALT2muH0_data_foranthony.input`. Neither class
establishes that an externally referenced byte sequence was used in an
executed final run.

## Post-hoc cross-CID collision diagnostic

The separately frozen diagnostic considered all cross-CID candidate file
pairs whose unordered source-directory pair occurred in the 48-pair main
universe. It used the same rounding-compatible payload rule and found:

| Quantity | Count |
|---|---:|
| Cross-CID candidate file pairs | 1,523 |
| Observation-pair opportunities | 14,670,999 |
| Positive file pairs | 24 |
| Mutual-unique compatible matches | 24 |
| Directory-pair strata | 11 |

Positive controls occurred in the three directory-pair strata that also
contained the four main positives. Candidate groups and observations are not
exchangeable, and no p-value was computed. This diagnostic is therefore a
descriptive collision screen, not a calibrated null distribution or causal
test. The protected main outputs were byte-identical before and after it.

## Verification

- Source and contract locks: PASS (45 files, 20 trees).
- Unit and fixed-source integration tests: 50/50 PASS.
- Second implementation: 31/31 checks PASS. It was developed within the same
  AI-assisted project and is not external replication.
- Clean-directory reproduction: 20/20 generated outputs byte-identical.

## Interpretation and stopping point

The public release is sufficient to say that the 69 frozen candidates are
distinct files, that their published observation payloads show four isolated
cross-series agreements under the frozen rule, that all used filters map to
public KCOR definitions and transmission assets, and that all seven series
appear in the active shared configuration and aggregation graph.

It is not sufficient to say that any match is the same physical exposure, that
the same-CID rows are independent or dependent, or that a candidate produced a
specific final `m_b_corr` row. Phase 1F therefore stops without a refit, row
operation, covariance change, corrected H0, tension-significance update,
causal explanation, or new-physics claim.
