# GitHub Integration Notes

This package is intentionally assembled as a **candidate repository tree**, not pushed automatically.

Recommended integration choices:

1. **Update the existing `hubble-constant-inference-traceability` repository as a new major/minor release** if continuity with the First-Season public record is preferred. In that case keep old tags immutable and add this integrated reproduction tree as the new current release.
2. **Create a separate integrated-paper repository** if the submitted manuscript is intended to have a clean one-paper/one-repository identity.

Do not overwrite historical release assets. Do not claim a DOI until one is actually assigned. Once a public URL is final, add it to the manuscript Data and Code Availability section and to `CITATION.cff`, then regenerate `MANIFEST.tsv` and `SHA256SUMS.txt`.

The current package deliberately uses `repository-code: TO_BE_ASSIGNED`.
