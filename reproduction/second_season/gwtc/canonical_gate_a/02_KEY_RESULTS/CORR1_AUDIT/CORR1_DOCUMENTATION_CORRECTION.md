# CORR1 documentation correction

## Classification

```text
CORRECTION_CLASS = DOCUMENTATION_CORRECTION_ONLY
SOURCE_BYTES_CHANGED = NO
SCIENTIFIC_DECISION_CHANGED = NO
V1_HISTORY_OVERWRITTEN = NO
POSTERIOR_QUANTILE_REPRODUCTION_IN_SOURCE_FREEZE = NOT_EXECUTED
```

This CORR1 package preserves the original V1 package as a separate artifact. It makes only the following documentation corrections:

1. Registers four already-present support files in `AUDIT/SUPPORT_FILE_REGISTER.tsv`.
2. Records their release, official record ID, filename, role, byte size, official MD5, local MD5, local SHA256, and `used_in_gate=NO`.
3. Replaces generic checksum descriptions in six existing `AUDIT/SOURCE_FREEZE.tsv` rows with the concrete official distribution MD5 values already present in the frozen Zenodo record metadata.
4. Restores one missing trailing hexadecimal character in the GWTC-4 SHA256 transcription in `AUDIT/SOURCE_FREEZE.tsv`. The corrected value matches the frozen source byte, V1 manifest, `AUDIT/HEADLINE_POSTERIOR_IDENTITY.md`, and the original `AUDIT/NEXT_STAGE_CONTRACT.md`.

The four newly registered files are classified as `SUPPORT_FILE_NOT_USED_IN_GATE`. No source file, paper, notebook, posterior sample, prior audit file, or scientific gate status was modified.

The missing-character defect was exposed by the first Gate A identity preflight, which stopped before any percentile calculation. After the ledger was corrected against three independent in-package references and a fresh direct SHA256 calculation, Gate A was restarted under the same scientific algorithm and comparison contract. The pre-correction HOLD log is preserved in the Gate A results package.

## Parent identity

```text
PARENT_PACKAGE = GWTC45_H0_METRIC_PROVENANCE_SOURCE_FREEZE_V1.zip
PARENT_OUTER_SHA256 = a4b71e446e68877954188a2c1837d0f0082e26276a690baaa43fce7681af70f9
```

## Gate separation

Gate A is executed only in the separate results package. This CORR1 source-freeze package retains the historical statement:

```text
POSTERIOR_QUANTILE_REPRODUCTION = NOT_EXECUTED
```

Gate B remains:

```text
METRIC_CODE_PATH = PASS
METRIC_ARITHMETIC_TRACE = PASS
METRIC_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE
```
