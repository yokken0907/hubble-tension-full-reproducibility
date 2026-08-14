# Identifier Collision Record

## Frozen finding

- Paper identifier: `ΛCDM2b`
- Paper dataset: `TDCOSMO + DES-SN5YR + SLACS + SL2S`
- Correct release model ID: `LambdaCDM2d`
- Same-named release file: `LambdaCDM2b.h5`
- Same-named release dataset: `TDCOSMO + DES-SN5YR + SLACS`
- Classification: `PAPER_RELEASE_IDENTIFIER_COLLISION`

## Required handling

Use HDF5 dataset attribute; do not select by paper ID alone.

The blind implementation recovered the distinct HDF5 dataset attributes
without receiving the paper-to-release crosswalk. The paper-row mapping itself
is a post-blind provenance conclusion.
