# Reproducibility

## Frozen upstream source

Use the Pantheon+SH0ES DataRelease at commit:

`c447f0fea703fcd0fff57de5000947b5ca81286b`

The checkout origin must normalize to
`https://github.com/PantheonPlusSH0ES/DataRelease`. The photometry tree and 24
key blobs are verified before computation.

## Accepted corrected Phase 1D dependency

Complete dependency closure also requires the accepted corrected Phase 1D ZIP
and its matching SHA-256 sidecar. The expected ZIP SHA-256 is
`6792886b8f1a8ac6397e6305931bfc750fdf1f1211c5e92b1f07ea1e7f0609bd`.
The package verifies that the ZIP and sidecar agree, that the corrected Phase
1D closure is `ACCEPT_COMPLETE_WITH_SCOPE`, and that the 31 target-driving
rows are unchanged over the specified legacy columns.

The original Phase 1E contract, freeze record, decision configuration,
pre-execution exposure record, and original Phase 1D compact inputs remain
byte-unchanged. The corrected dependency is recorded separately as a
post-result supersession and is not presented as prospectively frozen.

## Run order

```bash
python3 scripts/run_audit.py --pantheonplus /path/to/DataRelease
python3 scripts/independent_verify.py --pantheonplus /path/to/DataRelease
python3 -m unittest discover -s tests -v
python3 scripts/clean_reproduce.py --pantheonplus /path/to/DataRelease
python3 scripts/verify_results.py \
  --pantheonplus /path/to/DataRelease \
  --phase1d-corrected-zip /path/to/h0dn-snia-same-cid-measurement-lineage-audit_v0.1.0.zip \
  --phase1d-corrected-sidecar /path/to/h0dn-snia-same-cid-measurement-lineage-audit_v0.1.0.zip.sha256
```

The project uses only the Python standard library. Git is required because
source bytes and object identifiers are read from the frozen commit rather
than trusted from a mutable working tree.

## Expected high-level outcome

- 1701 official catalog rows
- 30 excluded multi-row CIDs
- 847 active photometry files; 0 parse failures
- 74 target-excluded eligible rows; 62 unambiguous anchors
- 3/3 supported public-internal crosswalks
- 31/31 target rows with one frozen-crosswalk-compatible public input candidate
- second-implementation internal cross-check 24/24
- unit and regression tests 36/36
- clean reproduction 15/15 protected files byte-identical
- accepted corrected Phase 1D dependency and target-driving ledger checks PASS

Upstream photometry and catalog files are not included in this package.
