# HTS68 CORR2 patch validation report

Validation date: 2026-07-25  
Scientific computation performed: `NO`

## Patch construction

The CORR1 patch was first applied to the original HTS68 script. The remaining defects were corrected in the completed script, and a new unified diff was generated directly from the original HTS68 script to the CORR2 completed script.

## Mechanical validation

| Check | Result |
|---|---|
| New diff dry-run against original script | PASS |
| New diff application | PASS |
| Patched output byte-equal to completed CORR2 script | PASS |
| Python syntax compilation | PASS |
| 28 expected chain hashes retained | PASS; unchanged from audited CORR1 |
| Reference TSV SHA256 retained | PASS: `1cd322aa9e1131bd6a81702e1b81d3afb49f0388b59825983573e05d260d00ed` |

## Ordered-gate tests

### Test A — unresolved template

Inputs used unresolved G0 and paper-version sentinels, a nonexistent repository, and a nonexistent paper PDF.

Result:

- exit code `2`;
- `HTS68_G0_CONTRACT_COMPLETENESS_GATE.json` written with `HOLD`;
- repository and paper absence did not produce a pre-G0 exception;
- no HDF5 output was generated.

This confirms G0 stops execution before scientific source access.

### Test B — mechanically valid temporary G0, invalid scientific source

A temporary noncanonical test copy was given a resolved test paper version, internally matching normalized script hash, contract hash, approval hash, reference hash, and G0 manifest hash. The repository and paper paths remained intentionally invalid.

Result:

- G0 status `PASS`, zero G0 issues;
- G1 source identity status `HOLD`;
- exit code `2` before HDF5 access.

This confirms gate ordering `G0 → G1 → HDF5`.

## Classification logic validation

The final classification is calculated from:

`G0 PASS && G1 PASS && G2 PASS && G3 PASS`

Management classification is conditional:

- formal PASS → `PASS_WITH_SCOPE`;
- formal HOLD → `HOLD`.

Future PASS classification:

`PASS_TDCOSMO2025_FROZEN_PUBLIC_CHAIN_CONTRACT_AND_DESCRIPTIVE_NESTED_POSTERIOR_SHIFT_MAPPING_WITH_SCOPE`

The historical original-HTS68 CORR1 classification is preserved separately and is not reused as the future-run success label.

## G0 preparation utility test

The historical correction package included `tools/prepare_hts68_g0_freeze.py`, which was tested with noncanonical temporary governance inputs; the utility is not redistributed in the present selective public repository.

Result:

- governance preparation status `PASS_G0_FREEZE_PREPARATION`;
- generated frozen script passed Python syntax compilation;
- generated manifest hash and normalized script hash were mutually consistent;
- generated script passed G0 with zero issues;
- intentionally invalid scientific sources were then stopped at G1 with exit code `2`.
