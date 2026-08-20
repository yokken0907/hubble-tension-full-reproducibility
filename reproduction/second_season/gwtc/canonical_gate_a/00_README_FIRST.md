# GWTC-4.0 -> GWTC-5.0 standard-siren posterior traceability

## Placement

```text
2nd season/
└── 01_GWTC45_STANDARD_SIREN_POSTERIOR_TRACEABILITY/
```

## Current branch state

```text
BRANCH_STATUS = COMPLETE_WITH_SCOPE
SOURCE_FREEZE_CURRENT = V1_CORR1
GATE_A_HEADLINE_QUANTILE_REPRODUCTION = PASS
GATE_B_PUBLISHED_25P7_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE
AUTOMATIC_EXPANSION = NO
```

## What was reproduced

The official GWTC-4 and GWTC-5 headline H0 posterior products were fixed from
the official release records. A separately written deterministic type-7
percentile implementation reproduced, after one-decimal rounding:

- GWTC-4: 76.6 +13.0 / -9.5
- GWTC-5: 71.0 +9.0 / -7.1

## What remains unresolved

The official GWTC-5 notebook contains an arithmetic path that displays a 25.7%
uncertainty reduction. However, the old-side `gw_dark_O4a` summary is not bound
to a uniquely frozen posterior byte sequence in the available official
records. The exact referenced old-side registry and inputs remain unavailable.

Therefore:

```text
METRIC_CODE_PATH = PASS
METRIC_ARITHMETIC_TRACE = PASS
METRIC_POSTERIOR_PAIR_PROVENANCE = HOLD_NOT_UNIQUE
```

Gate A PASS does not release Gate B HOLD.

## Package organization

- `01_CURRENT_STATE/`: final branch classification, scope, and reopen conditions.
- `02_KEY_RESULTS/`: decisive Gate A/CORR1 records extracted for direct reading.
- `03_ARCHIVE_PACKAGES/`: original V1, CORR1, Gate A, and instruction artifacts.
- `04_REGISTERS/`: lineage, evidence, and machine-readable current state.
- `05_INDEPENDENT_VALIDATION/`: master-build verification and independent
  quantile recomputation.

The original packages remain intact. This master does not rewrite their
historical contents.
