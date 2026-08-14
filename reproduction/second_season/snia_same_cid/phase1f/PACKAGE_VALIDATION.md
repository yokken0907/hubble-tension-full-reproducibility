# Package validation protocol

The release archive is accepted only when all of the following gates pass:

1. the strict scientific verifier reports `ACCEPT_COMPLETE_WITH_SCOPE` with
   every check passing;
2. `MANIFEST.tsv` and `SHA256SUMS.txt` exactly describe the delivered tree;
3. two independent deterministic archive builds are byte-identical;
4. both ZIP CRC tests pass and every member has the fixed timestamp;
5. the external `.zip.sha256` sidecar matches the delivered archive;
6. the archive has one expected root, no duplicate or unsafe member path, no
   symbolic link, and no redistributed raw upstream file;
7. after extraction to a clean temporary directory, manifest verification and
   the strict 117-gate scientific verifier both pass against the fixed external
   source repository.

The delivery-time result is recorded outside the archive as
`delivery_verification.json`. Keeping that record external avoids a
self-referential archive checksum.
