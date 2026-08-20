# Third-party source policy

Third-party source products are identified by authoritative URL/record, commit or release, byte size, and SHA-256 where available. They are intentionally not copied into this repository. Fetching them does not change their original license.

# Third-party notices and redistribution boundary

This repository does not contain third-party raw data, posterior JSON files, HDF5 chains, H0DN/Pantheon+ source tables or covariance files, or derived NPZ test vectors containing those numerical arrays. Rights and redistribution terms for those source products remain with their respective authors, collaborations, archives, and repositories.

The package instead supplies public URLs or record identifiers, fixed commits, expected filenames, byte sizes, and cryptographic hashes. Readers retrieve source products from the official records and verify them locally before executing the bundled project code.

The bundled `publication_evidence/provenance/PHASE1B_ROW_MAP.tsv` is a project-created index/identifier crosswalk required for the same-name verification. It does not contain photometry, posterior samples, covariance values, or Hubble-diagram measurements.

Bundled historical tables and JSON summaries are project-created audit outputs. Bundled scripts are project-created implementations. Their inclusion does not change the licenses or citation requirements of the external source products they inspect.

The four complete version-locked archival package binaries are identified by filename and SHA-256 but are not embedded inside the GitHub tree. Claim-relevant records created within this study and selected from those packages are included under `evidence/canonical_ledgers/`; the directory name is retained as a machine-readable traceability path. This does not enlarge or imply redistribution rights for any third-party source product.
