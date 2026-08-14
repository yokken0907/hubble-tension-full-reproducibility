# Source-freeze correction summary

## Decision

```text
CORR1_STATUS = PASS
CORRECTION_CLASS = DOCUMENTATION_CORRECTION_ONLY
SOURCE_BYTES_CHANGED = NO
SCIENTIFIC_DECISION_CHANGED = NO
V1_OVERWRITTEN = NO
```

The original V1 package remains unchanged:

```text
GWTC45_H0_METRIC_PROVENANCE_SOURCE_FREEZE_V1.zip
SHA256 = a4b71e446e68877954188a2c1837d0f0082e26276a690baaa43fce7681af70f9
```

The corrected package is:

```text
GWTC45_H0_METRIC_PROVENANCE_SOURCE_FREEZE_V1_CORR1.zip
SHA256 = 4dbede18c55ab9d27ef1ddc3333a4195c52c11b0ddc67d4bec1254206d118706
```

## Corrections

1. Added `AUDIT/SUPPORT_FILE_REGISTER.tsv` with complete release, official record ID, filename, role, byte size, official MD5, local MD5, local SHA256, and `used_in_gate` fields for:
   - `SOURCES/GWTC4/H0_spectral_combined.json`
   - `SOURCES/GWTC4/load_result.py`
   - `SOURCES/GWTC5/H0_spectral_combined_gw170817.json`
   - `SOURCES/GWTC5/H0_summary_plot.ipynb`
2. Classified all four as `SUPPORT_FILE_NOT_USED_IN_GATE` with `used_in_gate=NO`.
3. Replaced generic official-checksum descriptions in six existing `AUDIT/SOURCE_FREEZE.tsv` rows with their concrete Zenodo distribution MD5 values.
4. Restored the missing final `8` in the GWTC-4 headline posterior SHA256 recorded in `AUDIT/SOURCE_FREEZE.tsv`.

The correct GWTC-4 SHA256 is:

```text
b4b5e271d94f0ac828c840a46d72bd5e9433d706a47f352abfcdd3fbc2014fc8
```

This value is independently present in the V1 internal manifest, V1 headline identity report, original next-stage contract, and a fresh direct hash of the frozen input. The first Gate A preflight stopped on this ledger mismatch before computing a percentile. Its log is preserved as `RUN_LOG_PRE_CORRECTION_HOLD.txt`.

## Integrity

```text
CORR1_FILES = 37
CORR1_INTERNAL_SHA256 = 36 / 36 PASS
CORR1_ZIP_CRC = PASS
SOURCE_TREE_BYTE_COMPARISON_V1_TO_CORR1 = IDENTICAL
INTERNAL_PRIOR_BYTE_COMPARISON_V1_TO_CORR1 = IDENTICAL
POSTERIOR_QUANTILE_REPRODUCTION_IN_SOURCE_FREEZE = NOT_EXECUTED
```

Gate A is executed only in this separate results package. Gate B remains unchanged.
