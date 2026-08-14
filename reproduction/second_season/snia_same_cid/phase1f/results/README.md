# Results guide

## Main result

`audit_summary.json` and `EXECUTION_STATUS.json` hold the formal Phase 1F
classification. The public release supports bounded input-dependency and
configuration classification; executed-run-to-final-catalog lineage and
physical-exposure identity remain unestablished.

| File | Role |
|---|---|
| `input_inventory.json` | Frozen population counts and candidate-integrity status |
| `input_candidate_map.tsv` | One record per 69 upstream-selected public-input candidates |
| `row_input_profile.tsv` | Parsed file identity, header, filters, and observation counts |
| `pair_dependency_classification.tsv` | All 48 within-CID pair classes and counts |
| `observation_match_evidence.tsv` | The four accepted isolated payload matches and descriptors |
| `filter_calibration_mapping.tsv` | All 434 row-by-used-filter mappings |
| `series_configuration_lineage.tsv` | Seven-series active configuration anchors |
| `public_asset_availability.tsv` | Sixteen externally referenced asset availability records |
| `shared_dependency_ledger.tsv` | Bounded shared-input/configuration statements |
| `evidence_semantics.json` | Machine-readable evidence levels and non-promotions |

The four records in `observation_match_evidence.tsv` describe published
numerical payload compatibility/agreement only. They do not establish payload
reuse and are not shared-exposure labels. The layer token
`PUBLISHED_PHOTOMETRIC_PAYLOAD_REUSE` in `shared_dependency_ledger.tsv` is
retained as frozen legacy nomenclature; its preferred interpretation is
`PUBLISHED_PHOTOMETRIC_PAYLOAD_COMPATIBILITY`. The 0.11-day timing field is a
non-promoting descriptor chosen after limited example exposure.

## Post-hoc diagnostic

`posthoc_cross_cid_negative_control_pairs.tsv`,
`posthoc_cross_cid_negative_control_by_directory_pair.tsv`, and
`posthoc_cross_cid_negative_control_summary.json` record a diagnostic designed
and frozen after the main result. The nonexchangeable screen found 24 positive
cross-CID file pairs among 1,523 tested pairs and 14,670,999 observation-pair
opportunities. It supplies no p-value and makes no causal inference.

## Verification records

- `contract_verification.json` and `source_verification.json`: frozen inputs.
- `independent_verification.json`: 31-check within-project second
  implementation, not external replication.
- `unit_tests_summary.json` and `unit_tests.log`: 50-test suite.
- `clean_reproduction_summary.json` and `.log`: 20-output clean rerun.
- `final_verification_summary.json`: strict scientific and packaging gates.
- `run_environment.json`: reference execution platform.

No table contains a corrected H0, a covariance update, or a promoted final
measurement ancestry claim.
