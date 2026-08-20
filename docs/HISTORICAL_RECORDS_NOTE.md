# Historical Records Note

The current repository interface uses ordinary scientific language. Some retained historical evidence records preserve earlier project-specific status vocabulary, filenames, and machine-specific execution-path strings because those files are provenance artifacts whose byte identity can matter to historical verification.

These historical strings should be interpreted as records of how an earlier analysis was executed or classified. They are **not** current repository commands, required filesystem paths, or a separate scientific vocabulary that readers must adopt.

In particular:

- machine-specific paths such as former WSL/Windows or home-directory locations are historical execution records only;
- status words embedded in version-locked ledgers retain their historical definitions and are translated into ordinary terms in current public-facing documents;
- missing members named by a historical nested checksum file may reflect deliberate compact-repository exclusions rather than corruption; see `COMPACT_REPOSITORY_OMISSIONS.tsv`.

The repository-level `MANIFEST.tsv` and `SHA256SUMS.txt` are the authoritative integrity records for the current v1.1 tree.
