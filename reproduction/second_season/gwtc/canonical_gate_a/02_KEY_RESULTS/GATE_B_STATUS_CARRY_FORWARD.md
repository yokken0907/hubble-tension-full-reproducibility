# Gate B status carried forward

Gate A and Gate B are independent.

```text
METRIC_CODE_PATH = PASS
METRIC_ARITHMETIC_TRACE = PASS
METRIC_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE
GATE_B_DECISION = HOLD_METRIC_PROVENANCE_NOT_UNIQUE
```

The official GWTC-5 notebook contains the arithmetic path that displays 25.7%, but its old-side `gw_dark_O4a` summary is not bound to a uniquely frozen posterior byte sequence. The referenced `O4a_cosmology_results_paths_SR9.json` and the exact old-side inputs are absent from the official frozen records.

Therefore:

- `gw_dark_O4a` is not identified with the GWTC-4 headline posterior.
- A Gate A PASS cannot release the Gate B HOLD.
- The one-time headline-pair diagnostic is not recorded as a 25.7% reproduction.
- No missing registry or posterior input is inferred or reconstructed.

Gate B may be reopened only if the official missing registry, referenced source bytes with checksums, and the comparator mapping become uniquely available.
