# Reproducibility and verification

## Clean-extraction verification

From the extracted package root, run:

```bash
python scripts/run_internal_validations.py --verify-recorded
python scripts/verify_package.py
```

The first command recomputes every new H0DN and SN mathematical validation
from the included test vectors without modifying the package. The second
checks the complete manifest, SHA-256 list, frozen-contract digest, JSON and
ledger closure, test-vector provenance, and the recorded numerical result.

## Test-vector boundary

`h0dn_network_gls.npz` contains the `A`, `y`, and `C` matrices captured from the
untouched H0DN workflow at commit
`cc0a4b9f36e65470d514f254a3c5cffa463fbd94`. Matrix construction is not a new
independent implementation. The delivered SVD, eigendecomposition,
support-space, Decimal, and synthetic calculations are project-internal
independent linear-algebra checks.

`sn_intercept_block.npz` is rebuilt by an independent parser from the two
locked public H0DN Pantheon+ input files and the frozen one-intercept equations.

The source-rebuild helper is included as
`scripts/rebuild_test_vectors_from_h0dn.py`. It requires a local checkout at
the exact H0DN commit and writes new test vectors; it is not run by the
read-only package verifier.

## External independence boundary

No script in this package converts the work into external independent
replication. A genuinely external replication requires a different researcher
or organization, independently implemented numerical/statistical review, and
an independently preserved source/environment record.
