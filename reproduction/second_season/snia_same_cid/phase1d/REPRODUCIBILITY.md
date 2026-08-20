# Reproducibility

## Requirements

- Git with partial-clone support
- CPython 3.12 (the audit uses only the standard library)
- Network access for first-time acquisition and lazy retrieval of frozen Git
  blobs

No Python package installation is required.

## 1. Verify the delivered package

From the unpacked repository root:

```bash
python scripts/finalize_package.py --check
```

This verifies `MANIFEST.tsv`, `SHA256SUMS.txt`, and the completed scientific
closure before any source acquisition.

## 2. Acquire the exact upstream commits

```bash
python scripts/source_tools.py acquire --destination frozen_sources
```

This creates two filtered bare Git repositories:

- `frozen_sources/H0DN.git`
- `frozen_sources/PantheonPlusSH0ES-DataRelease.git`

The helper sets each `HEAD` to the frozen commit and immediately verifies
repository URL, commit, photometry-tree object, locked blobs, byte counts, and
SHA-256 digests. Existing destinations are never deleted or overwritten.

To verify separately acquired repositories:

```bash
python scripts/source_tools.py verify \
  --h0dn /path/to/H0DN \
  --pantheonplus /path/to/DataRelease
```

## 3. Recreate the main results

```bash
python scripts/run_audit.py \
  --h0dn frozen_sources/H0DN.git \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git

python scripts/independent_verify.py \
  --h0dn frozen_sources/H0DN.git \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
```

The first command verifies the frozen contract and sources before emitting
the main result ledgers. The second command reparses sources and recomputes
the population, file candidates, groups, observation-line intersections,
configuration anchors, asset tracking, and classification through a separate
implementation path. It is a within-project second-implementation cross-check,
not an independent external replication.

The main run also validates
`provenance/SURVEY_CROSSWALK_EVIDENCE.tsv` against the official IDSURVEY
legend, frozen decision configuration, `PPLUS.yml` RAW_DIR anchors, and the
main candidate ledger. Its excerpt hashes use the canonical JSON construction
named in the `evidence_excerpt_spec` column.

## 4. Recreate the bounded post-hoc diagnostic

```bash
python scripts/run_posthoc_cid_only_crosswalk.py \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git

python scripts/verify_posthoc_cid_only_crosswalk.py \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
```

The diagnostic checks the hash of its own post-result contract and protects
five main result files before searching by CID alone. A separate implementation
recreates both diagnostic ledgers and confirms that the main files did not
change. This is not an external replication, peer review, or expert endorsement.

## 5. Run tests and isolated reproduction

```bash
python -m unittest discover -s tests -v

python scripts/clean_reproduce.py \
  --h0dn frozen_sources/H0DN.git \
  --pantheonplus frozen_sources/PantheonPlusSH0ES-DataRelease.git
```

`clean_reproduce.py` copies the package without prior results or manifests
into a temporary directory, runs all four analysis/verifier entry points,
and requires 19 regenerated result files to equal the delivered files
byte-for-byte.

To recreate the delivered test log:

```bash
python -m unittest discover -s tests -v 2>&1 | tee results/unit_tests.log
```

## 6. Run strict read-only closure

```bash
python scripts/verify_results.py
```

The command must finish with `status: PASS` and
`closure: ACCEPT_COMPLETE_WITH_SCOPE`. The default verifier is read-only: it
hashes the delivered tree before and after evaluation and does not rewrite a
manifested file.

When intentionally recording a new final verification result before manifests
are frozen, run:

```bash
python scripts/record_verification.py
```

## 7. Rebuild a deterministic archive

After re-running results, regenerate manifests because result bytes are part
of the package:

```bash
python scripts/record_verification.py
python scripts/finalize_package.py --write-manifests
python scripts/verify_results.py
python scripts/finalize_package.py --check
python scripts/finalize_package.py \
  --archive ../h0dn-snia-same-cid-measurement-lineage-audit_v0.1.0.zip
```

ZIP members are sorted, timestamps are fixed, Unix modes are normalized, and
DEFLATE settings are fixed. Repeating the final command from the same
manifested tree must produce the same SHA-256 and byte stream.

## Failure semantics

Operational source, contract, population, parser, pipeline, or verifier
failures stop with a nonzero exit status. A row without a unique
frozen-crosswalk-compatible input candidate is not an operational failure; it
is preserved in `row_lineage.tsv`. The legacy status does not establish absence
of public photometry, and no row establishes direct final-measurement ancestry.
The post-hoc diagnostic is non-promoting by contract and cannot change main
classification.
