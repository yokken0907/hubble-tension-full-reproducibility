# Gate A decision

## Decision

```text
GATE_A_DECISION = PASS
GWTC4_INPUT_IDENTITY = PASS
GWTC5_INPUT_IDENTITY = PASS
CUSTOM_VS_NUMPY = 6 / 6 PASS
ROUNDED_HEADLINE_COMPONENTS = 6 / 6 PASS
STOP_AFTER_GATE_A = YES
NO_AUTOMATIC_EXPANSION = YES
```

The first identity preflight produced `HOLD` before percentile calculation because V1 `SOURCE_FREEZE.tsv` omitted the final hexadecimal character from the GWTC-4 SHA256. CORR1 repaired that transcription against the unchanged source byte and three independent V1 references. The pre-result posterior, percentile, interpolation, rounding, and headline-comparison rules were not changed.

## Raw results

| Release | \(q_{15.865}\) | \(q_{50}\) | \(q_{84.135}\) | Lower error | Upper error | Mean 68.27% uncertainty |
|---|---:|---:|---:|---:|---:|---:|
| GWTC-4 | 67.109687714421568 | 76.637257552567235 | 89.679444938001240 | 9.5275698381456664 | 13.042187385434005 | 11.284878611789836 |
| GWTC-5 | 63.875918946212742 | 71.017005223697197 | 80.002495921711073 | 7.1410862774844546 | 8.9854906980138765 | 8.0632884877491655 |

## Headline comparison

| Release | Reproduced after independent 1-decimal rounding | Official headline | Decision |
|---|---|---|---|
| GWTC-4 | \(76.6^{+13.0}_{-9.5}\) | \(76.6^{+13.0}_{-9.5}\) | PASS |
| GWTC-5 | \(71.0^{+9.0}_{-7.1}\) | \(71.0^{+9.0}_{-7.1}\) | PASS |

The custom type-7 results and `numpy.percentile(..., method="linear")` were identical at the recorded floating-point precision for all six percentile values; every absolute difference was `0`, below the fixed `1e-10` tolerance.

## One-time diagnostic

Using the unrounded headline posterior intervals only:

```text
GWTC4_MEAN_UNCERTAINTY = 11.284878611789836
GWTC5_MEAN_UNCERTAINTY = 8.0632884877491655
RELATIVE_REDUCTION = 28.547849160512239 %
```

This is a diagnostic property of the frozen headline posterior pair. It is not used for Gate A, differs from 25.7% by 2.84784916051224 percentage points, and is not a reproduction of the published metric.

## Gate B separation

```text
METRIC_CODE_PATH = PASS
METRIC_ARITHMETIC_TRACE = PASS
METRIC_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE
GATE_B_DECISION = HOLD_METRIC_PROVENANCE_NOT_UNIQUE
```

Gate A PASS does not alter Gate B because the exact old-side posterior bytes behind `gw_dark_O4a` remain unavailable.

## Scope and stop

No likelihood, sampler, MCMC, event-level analysis, release-difference causal attribution, or other-probe integration was performed. The branch stops after Gate A.
