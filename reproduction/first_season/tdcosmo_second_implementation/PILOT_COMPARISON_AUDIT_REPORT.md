# TDCOSMO Blind Sentinel Post-Blind Comparison Audit

## Classification

`PASS_BLIND_SENTINEL_ALTERNATE_IMPLEMENTATION_EXACT_MATCH_WITH_SCOPE`

## Integrity

- Blind result ZIP SHA256: `cf5d11faff636b265bfbb87bb8aa79be8eab85f1e70105c49770b800225314cf`
- Blind result ZIP CRC: PASS
- Internal result checksums: 9/9 PASS
- Frozen alternate implementation SHA256: `6360c803c584cc29e939445001fa6508cd875d16b4cdba5caba8be8b031368f7`
- Standard error log: empty
- Input source-hash gate: 3/3 PASS

## Blind-execution artifact audit

The delivered source code:

- locates `h0` from decoded HDF5 parameter names rather than a fixed column;
- implements the pre-registered equal-weight Type-7 linear quantile rule;
- contains no historical HTS68 numerical values, Table 6 values, or identifier crosswalk;
- reads the source manifest and all three HDF5 inputs generically;
- records code, environment, command, stdout, stderr, and internal checksums.

The artifacts support compliance with the blind contract. They cannot prove
the absence of unrecorded human or model exposure outside the package, so the
appropriate description remains a project-internal alternate implementation,
not an external independent replication.

## Structural comparison

- Three input SHA256 values: exact match with the historical source freeze.
- Sample shapes: exact match.
- Parameter counts and ordering: exact match.
- `h0` column index: independently recovered as column 0 in all three files.
- HDF5 ModelID and dataset attributes: exact match.
- Structural comparison result: 3/3 PASS.

The blind audit independently recovered the important release distinction:

- `LambdaCDM2b.h5` = `TDCOSMO + DES-SN5YR + SLACS`
- `LambdaCDM2d.h5` = `TDCOSMO + DES-SN5YR + SLACS + SL2S`

This confirms the file-level basis for the previously recorded identifier
collision. The paper-row mapping itself is established only in the post-blind
comparison using the frozen crosswalk.

## Numerical comparison

Nine pre-registered quantities were compared:

- 3 files × q16, q50, q84
- exact binary64-value equality: 9/9
- pre-registered tolerance pass: 9/9
- maximum absolute delta: `0`

Sentinel values:

| Release file | q16 | q50 | q84 |
|---|---:|---:|---:|
| ULambdaCDM1.h5 | 69.306259656847942 | 73.736005669349581 | 78.446226252864676 |
| LambdaCDM2b.h5 | 70.202457358380812 | 73.760039551163942 | 76.941943800948039 |
| LambdaCDM2d.h5 | 70.898960337066512 | 73.920671303436080 | 77.297041539226498 |

## Scientific boundary

This result establishes that a separately written implementation reproduces
the frozen sentinel HDF5 structure and equal-weight H0 quantiles exactly.

It does **not** establish:

- external independent replication;
- original sampler or likelihood reconstruction;
- MCMC convergence;
- correctness of the released posterior-generation process;
- causal attribution to SLACS, SL2S, mass-sheet effects, or another systematic;
- a corrected H0 value;
- resolution of the Hubble tension.

## Next gate

The pre-registered sentinel gate is passed. The next permissible step is an
unchanged-code extension to the remaining Table 6 flat-LambdaCDM chains.

To preserve the evidential value:

1. freeze the current source-code hash `6360c803c584cc29e939445001fa6508cd875d16b4cdba5caba8be8b031368f7`;
2. do not modify the quantile implementation or tolerance;
3. supply the ten remaining Table 6 HDF5 files;
4. retain `LambdaCDM2b.h5` as an identifier-collision control;
5. run the same code on the 13-file set (12 paper rows plus one collision control);
6. compare with Table 6 only after the expanded result ZIP is frozen.
