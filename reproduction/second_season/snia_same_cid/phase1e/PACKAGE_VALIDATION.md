# Package validation

The package is accepted only after all of the following pass:

- prospective contract hash and frozen-input verification;
- 24/24 source-lock records;
- accepted corrected Phase 1D ZIP/sidecar/closure verification and a
  non-retroactive supersession record;
- byte preservation of the original Phase 1E freeze and equality of the 31-row
  target-driving ledger over the specified legacy columns;
- exact seven-directory crosswalk-universe verification with broader-tree and
  external-archive uniqueness booleans fixed to `false`;
- compatible-public-input-candidate status semantics with all direct-ancestry,
  fit-output, bias-correction-run, executed-run, and statistical-independence
  booleans fixed to `false`;
- second-implementation internal cross-check, explicitly not an external
  independent replication or expert endorsement;
- 36 unit and regression tests;
- 15/15 protected outputs reproduced byte-for-byte in isolation;
- preservation of the 74, 62, 12, 3/3, 31/31, code-specific, 847, and zero
  parse-failure scientific counts;
- strict scientific, dependency, interpretation, and documentation closure:
  52/52 gates PASS;
- complete manifest and SHA-256 inventory;
- two deterministic ZIP builds with byte identity;
- ZIP CRC, single-root, sidecar, and no-upstream-redistribution checks;
- a final verification from a newly extracted archive.
