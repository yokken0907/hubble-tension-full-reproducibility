# Pre-result contract

This contract was fixed before reading the Gate A output values.

## Scope

```text
GATE = A_HEADLINE_POSTERIOR_QUANTILE_REPRODUCTION
NEW_LIKELIHOOD = NO
SAMPLER_OR_MCMC = NO
EVENT_LEVEL_ANALYSIS = NO
OTHER_PROBE_INTEGRATION = NO
RANDOM_OR_RESAMPLING = NO
GATE_B_REOPENING = NO
```

## Frozen inputs

| Release | Official record | File | Expected SHA256 | JSON key | Expected samples |
|---|---:|---|---|---|---:|
| GWTC-4 | 16919645 | `INPUTS/GWTC4/H0_dark_combined.json` | `b4b5e271d94f0ac828c840a46d72bd5e9433d706a47f352abfcdd3fbc2014fc8` | `posterior` | 3500 |
| GWTC-5 | 20378418 | `INPUTS/GWTC5/H0_dark_combined_gw170817.json` | `00aaee9573ae940ac156c1b4af441e075a462a4c54152ac20d03511b877ce0d5` | `posterior` | 3500 |

An input identity, JSON structure, or sample-count mismatch produces `HOLD`. No substitute file or reconstructed input may be used.

The first identity preflight stopped before percentile calculation because the V1 `SOURCE_FREEZE.tsv` transcription omitted the final `8` from the GWTC-4 SHA256. CORR1 restores that character using the source byte, V1 manifest, V1 identity report, and original next-stage contract. The algorithm, posterior, percentile, interpolation, rounding, and headline comparisons below were not changed.

## Fixed calculation

For each posterior:

1. Sort the samples in ascending order.
2. Compute \(q_{15.865}\), \(q_{50}\), and \(q_{84.135}\) with Hyndman-Fan type 7 linear interpolation.
3. Compute `lower_error = q50 - q15.865`.
4. Compute `upper_error = q84.135 - q50`.
5. Preserve the raw values.
6. Round the median, lower error, and upper error independently to one decimal place.

The primary implementation is the deterministic custom implementation in `SCRIPT/gate_a_quantile_reproduction.py`. `numpy.percentile(..., method="linear")` is secondary only.

```text
IMPLEMENTATION_CROSSCHECK_TOLERANCE = 1e-10
```

## Fixed official comparisons

```text
GWTC-4 = 76.6 +13.0 / -9.5
GWTC-5 = 71.0 +9.0 / -7.1
```

## Gate A decision

- `PASS`: both input identities pass; every custom-vs-NumPy comparison is within tolerance; all six independently rounded headline components match.
- `FAIL`: the fixed source and algorithm produce any implementation or headline mismatch. The posterior, percentile, interpolation, or rounding rule must not be changed afterward.
- `HOLD`: the input checksum, JSON structure, or sample identity cannot be interpreted uniquely.

## Diagnostic metric boundary

The raw headline-pair average-uncertainty reduction may be computed once as a diagnostic. It is not used for Gate A and is not a reproduction of the published 25.7%.

Gate B is carried forward unchanged:

```text
METRIC_CODE_PATH = PASS
METRIC_ARITHMETIC_TRACE = PASS
METRIC_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE
```

## Stop

```text
STOP_AFTER_GATE_A = YES
NO_AUTOMATIC_EXPANSION = YES
```
