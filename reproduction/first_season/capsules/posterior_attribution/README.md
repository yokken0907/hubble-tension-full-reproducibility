# E002 - Posterior-attribution archived-workflow replay

This capsule replays the registered N029-N035 posterior-attribution workflow without changing the scientific values or their convention-dependent interpretation.

## Two-layer replay

1. **Layer A - HTS59-HTS65:** the archived scientific implementations are re-executed from 51 hash-fixed selected posterior-export members obtained from official archives. Substantive tables, classifications, and numerical fields are compared with verified historical results. Outer ZIP hashes are not required because timestamps and packaging paths are non-scientific.
2. **Layer B - HTS66 and HTS67:** HTS66 uses verified path-sanitized portable replicas of the historical HTS59-HTS65 intermediate inputs required by its fixed gates. HTS67 uses the verified HTS62 and `HTS66_CORR` inputs plus the same hash-fixed posterior exports. The canonical current acceptance lineage is the Phase2C official empty-cache run; its eight designated substantive HTS67 tables are byte-identical to the preserved historical substantive reference. This is not a claim that the complete result ZIP or path- and packaging-dependent records are byte-identical.

The failed historical `HTS66_RESULTS_FOR_REVIEW.zip` (`HOLD_SOURCE_MATERIALIZATION_OR_CLOSEOUT_EXECUTION_FAILURE`) is not included and must never be used as evidence, expected output, or downstream input.

Third-party posterior chain bytes are not redistributed. `fetch_selected_chains.py` obtains them from the official providers and verifies all 51 selected members against `SELECTED_CHAIN_MANIFEST.tsv`.

## Run

```bash
python run_all.py --fetch-inputs --cache ./_external_cache --work ./_work --output ./_outputs --verify
```

A verified local cache may be reused by omitting `--fetch-inputs`. This is project-internal replay of fixed posterior exports and historical intermediate archives. It does not reconstruct the original likelihoods, samplers, burn-in decisions at posterior generation, convergence assessment, or posterior-generation environment, and it is not external independent validation.

## Reproducibility-repair records

`verify_output.py` accepts `--output-dir`, `--expected`, and `--report`, and reads fresh HTS59–HTS67 outputs directly. `run_all.py --verify` passes the just-generated output directory to this verifier and fails nonzero on any missing, duplicate, non-finite, classification, count, tolerance, or manuscript-display mismatch. Retained records under `fresh_replay_records/` and `verified_replay_records/` are historical audit evidence; neither directory is the current Phase2C acceptance lineage.

The wrapper constructs `selected_hts67/ORIGINAL_FACTORIAL_SELECTED/` and `selected_hts67/FIXED_FULL_SELECTED/` with byte-identical members. HTS59–HTS65 may consume the verified selected cache through a non-scientific materialization override, avoiding repeated expansion of the upstream archives while retaining all 51 member hashes.

## Portable exact intermediate archives

HTS66 input gates use path-sanitized portable replicas of the historical author-generated intermediate ZIPs. For HTS59-HTS65 and the HTS66 correction input, substantive scientific members are byte-identical and historical/portable outer hashes are cross-recorded. The current HTS67 comparison is generated directly from the canonical Phase2C result ZIP and the historical substantive reference. The earlier non-byte-identical comparison is preserved unchanged under `historical_earlier_replay/` and is not current E002 acceptance evidence.
## Official empty-cache acquisition evidence

Phase2C executed this capsule from a newly empty external cache in a network-enabled WSL environment. The FIXED archive matched its registered full-archive SHA-256. The ORIGINAL archive was accessed by HTTP Range rather than fully materialized; all 40 selected ORIGINAL members and all 11 selected FIXED members matched their registered byte sizes and SHA-256 values, and E002 completed successfully.

The expected and observed ORIGINAL ETags differ. The mismatch is recorded under `official_fetch_records/` and is treated as HTTP metadata, not as the scientific input-identity gate. No full ORIGINAL archive SHA-256 is claimed. See `official_fetch_records/OFFICIAL_ARCHIVE_METADATA_INTERPRETATION.md`.

The retained canonical HTS67 result ZIP is
`official_fetch_records/phase2c_network_execution/outputs/HTS67_RESULTS_FOR_REVIEW.zip`
(SHA-256
`8254503a8a18d6ca3cfcc6dfb0104458982e19bd13bf89b9c81d3e8f34a31353`).
`generate_hts67_phase2c_comparison.py` reads that ZIP and regenerates the
8-row current comparison without executing any scientific stage.
