# GWTC-4 / GWTC-5 \(H_0\) metric provenance source freeze V1 CORR1

```text
CORR1_STATUS = DOCUMENTATION_CORRECTION_ONLY
SOURCE_BYTES_CHANGED = NO
SCIENTIFIC_DECISION_CHANGED = NO
POSTERIOR_QUANTILE_REPRODUCTION_IN_SOURCE_FREEZE = NOT_EXECUTED
```

Read `AUDIT/CORR1_DOCUMENTATION_CORRECTION.md` first, then the original `README_FIRST.md`.

CORR1 adds a complete register for four support files that were already present in V1, replaces generic official-checksum labels with concrete distribution MD5 values where available, and restores one missing trailing checksum character in `AUDIT/SOURCE_FREEZE.tsv`. The original V1 artifact is not overwritten.

Gate A execution results are not part of this source-freeze package; they are carried in the separate results-for-review package. Gate B remains `HOLD_NOT_UNIQUE`.
